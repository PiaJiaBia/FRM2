"""网页管理元数据与原有不可变快照分离；一个调用流程共享原repository事务。"""
from pathlib import Path
from datetime import timezone

from . import codec


def management_timestamp(value):
    """MySQL连接以UTC写入DATETIME；只标注管理时间，不转换样本日期。"""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def initialize_workbench(database):
    """显式追加网页表，不ALTER/DROP原表，兼容历史计算记录。"""
    database.initialize()
    with database.session() as repository:
        with repository.connection.cursor() as cursor:
            for statement in (Path(__file__).parent / 'workbench_schema.sql').read_text(encoding='utf-8').split(';'):
                if statement.strip():
                    cursor.execute(statement)


class WorkbenchRepository:
    def __init__(self, repository):
        self.repository = repository
        self.connection = repository.connection

    def _one(self, sql, args):
        with self.connection.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchone()

    def datasets(self, q='', archived=False, offset=0, limit=20):
        where = ' WHERE COALESCE(u.archived,0)=%s AND COALESCE(u.display_name,d.name) LIKE %s'
        args = (archived, '%' + q + '%')
        join = ' FROM frm_datasets d LEFT JOIN frm_dataset_ui u ON u.dataset_id=d.dataset_id'
        total = self._one('SELECT COUNT(*) AS n' + join + where, args)['n']
        with self.connection.cursor() as cursor:
            cursor.execute('''SELECT d.dataset_id AS id, COALESCE(u.display_name,d.name) AS name,
                d.description,d.row_count,d.column_count,d.created_at,d.metadata_json,
                COALESCE(u.archived,0) AS archived''' + join + where +
                ' ORDER BY d.created_at DESC,d.dataset_id LIMIT %s OFFSET %s', (*args, limit, offset))
            items = cursor.fetchall()
        for item in items:
            item['metadata'] = codec.loads(item.pop('metadata_json'))
            item['archived'] = bool(item['archived'])
            item['created_at'] = management_timestamp(item['created_at'])
        return {'items': items, 'total': total}

    def dataset(self, identity):
        item = self._one('''SELECT d.dataset_id AS id,COALESCE(u.display_name,d.name) AS name,
            d.description,d.row_count,d.column_count,d.created_at,
            COALESCE(u.archived,0) AS archived FROM frm_datasets d
            LEFT JOIN frm_dataset_ui u ON u.dataset_id=d.dataset_id WHERE d.dataset_id=%s''', (identity,))
        if item is None:
            raise KeyError('数据集不存在')
        snapshot = self.repository.load_dataset(identity)
        item['metadata'] = snapshot.metadata
        item['archived'] = bool(item['archived'])
        item['created_at'] = management_timestamp(item['created_at'])
        return item, snapshot.frame

    def update_dataset(self, identity, name=None, archived=None):
        # 锁定原快照行，为首次创建管理元数据的并发更新提供串行化边界。
        if self._one('SELECT dataset_id FROM frm_datasets WHERE dataset_id=%s FOR UPDATE', (identity,)) is None:
            raise KeyError('数据集不存在')
        item, _ = self.dataset(identity)
        with self.connection.cursor() as cursor:
            cursor.execute('''INSERT INTO frm_dataset_ui(dataset_id,display_name,archived) VALUES(%s,%s,%s)
                ON DUPLICATE KEY UPDATE display_name=%s,archived=%s''',
                (identity, name if name is not None else item['name'], archived if archived is not None else item['archived'],
                 name if name is not None else item['name'], archived if archived is not None else item['archived']))
        return self.dataset(identity)[0]

    def records(self, q='', archived=False, offset=0, limit=20):
        join = ' FROM frm_calculations c LEFT JOIN frm_calculation_ui u ON u.run_id=c.run_id'
        where = ' WHERE COALESCE(u.archived,0)=%s AND COALESCE(u.display_name,c.operation) LIKE %s'
        args = (archived, '%' + q + '%')
        total = self._one('SELECT COUNT(*) AS n' + join + where, args)['n']
        with self.connection.cursor() as cursor:
            cursor.execute('''SELECT c.run_id AS id,COALESCE(u.display_name,c.operation) AS name,
                c.dataset_id,c.operation,c.created_at,COALESCE(u.archived,0) AS archived''' + join + where +
                ' ORDER BY c.created_at DESC,c.run_id LIMIT %s OFFSET %s', (*args, limit, offset))
            items = cursor.fetchall()
        for item in items:
            item['archived'] = bool(item['archived'])
            item['created_at'] = management_timestamp(item['created_at'])
        return {'items': items, 'total': total}

    def record(self, identity):
        row = self.repository.load_calculation(identity)
        ui = self._one('SELECT display_name,archived FROM frm_calculation_ui WHERE run_id=%s', (identity,))
        parameters = row['parameters']
        request = parameters.get('request') if isinstance(parameters, dict) else None
        modern = (isinstance(parameters, dict) and parameters.get('format') == 'workbench-v1'
                  and isinstance(request, dict)
                  and isinstance(request.get('dataset_id'), str) and bool(request['dataset_id'].strip())
                  and isinstance(request.get('operation'), str) and bool(request['operation'].strip())
                  and isinstance(request.get('parameters'), dict))
        return {'id': identity, 'name': ui['display_name'] if ui else row['operation'],
                'dataset_id': row['dataset_id'], 'operation': row['operation'], 'created_at': management_timestamp(row['created_at']),
                'archived': bool(ui['archived']) if ui else False, 'source_sha256': row['source_sha256'],
                'legacy': not modern, 'request': parameters['request'] if modern else parameters,
                'result': row['result'] if modern else {
                    'metrics': [], 'tables': [], 'charts': [],
                    'notes': ['旧版计算记录，保留原始结果；不支持直接恢复网页表单。']},
                **({'legacy_result': row['result']} if not modern else {})}

    def save_result(self, job, name):
        # 锁定数据集，在同一事务中查重并写入记录，跨并发请求不会重复保存。
        self._one('SELECT dataset_id FROM frm_datasets WHERE dataset_id=%s FOR UPDATE', (job['dataset_id'],))
        old = self._one('SELECT run_id FROM frm_calculation_ui WHERE job_id=%s', (job['id'],))
        if old:
            return self.record(old['run_id'])
        request = {'dataset_id': job['dataset_id'], 'operation': job['operation'], 'parameters': job['parameters']}
        identity = self.repository.save_calculation(job['dataset_id'], job['operation'],
            {'format': 'workbench-v1', 'request': request, 'dataset_metadata': job['dataset_metadata']},
            job['result'], job['source_sha256'])
        with self.connection.cursor() as cursor:
            cursor.execute('INSERT INTO frm_calculation_ui(run_id,job_id,display_name) VALUES(%s,%s,%s)',
                           (identity, job['id'], name))
        return self.record(identity)

    def update_record(self, identity, name=None, archived=None):
        if self._one('SELECT run_id FROM frm_calculations WHERE run_id=%s FOR UPDATE', (identity,)) is None:
            raise KeyError('计算记录不存在')
        item = self.record(identity)
        with self.connection.cursor() as cursor:
            # 旧记录以run_id作为稳定的管理键，UUID空间与真正job_id分离。
            cursor.execute('''INSERT INTO frm_calculation_ui(run_id,job_id,display_name,archived) VALUES(%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE display_name=%s,archived=%s''',
                (identity, identity, name if name is not None else item['name'],
                 archived if archived is not None else item['archived'],
                 name if name is not None else item['name'], archived if archived is not None else item['archived']))
        return self.record(identity)

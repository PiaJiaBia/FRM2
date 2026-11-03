"""不可变DataFrame快照及计算记录；SQL仅存在于data层，值全部绑定参数。"""
from dataclasses import dataclass
from hashlib import sha256
from uuid import uuid4

import pandas as pd

from . import codec


@dataclass
class DatasetSnapshot:
    dataset_id: str
    name: str
    frame: pd.DataFrame
    metadata: dict
    sha256: str


class Repository:
    def __init__(self, connection):
        self.connection = connection

    def save_dataset(self, name, frame, description='', metadata=None):
        """每次生成新ID，不覆盖同名快照；commit由Database.session统一负责。"""
        if not isinstance(frame, pd.DataFrame):
            raise TypeError('Dataset must be a DataFrame')
        payload = codec.dumps(frame)
        identity = str(uuid4())
        digest = sha256(payload.encode('utf-8')).hexdigest()
        with self.connection.cursor() as cursor:
            cursor.execute('''INSERT INTO frm_datasets
                (dataset_id,name,description,row_count,column_count,sha256,frame_json,metadata_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                (identity,name,description,len(frame),len(frame.columns),digest,payload,codec.dumps(metadata or {})))
        return identity

    def load_dataset(self, dataset_id):
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT dataset_id,name,frame_json,metadata_json,sha256 FROM frm_datasets WHERE dataset_id=%s', (dataset_id,))
            row = cursor.fetchone()
        if row is None:
            raise KeyError(f'Dataset not found: {dataset_id}')
        if sha256(row['frame_json'].encode('utf-8')).hexdigest() != row['sha256']:
            raise ValueError(f'Dataset checksum mismatch: {dataset_id}')
        return DatasetSnapshot(row['dataset_id'],row['name'],codec.loads(row['frame_json']),
                               codec.loads(row['metadata_json']),row['sha256'])

    def list_datasets(self, name=None, limit=100):
        sql = 'SELECT dataset_id,name,description,row_count,column_count,sha256,created_at FROM frm_datasets'
        parameters = []
        if name is not None:
            sql += ' WHERE name=%s'
            parameters.append(name)
        sql += ' ORDER BY created_at DESC,dataset_id LIMIT %s'
        parameters.append(limit)
        with self.connection.cursor() as cursor:
            cursor.execute(sql,parameters)
            return pd.DataFrame(cursor.fetchall(),columns=['dataset_id','name','description','row_count','column_count','sha256','created_at'])

    def save_calculation(self, dataset_id, operation, parameters, result, source_sha256):
        identity = str(uuid4())
        with self.connection.cursor() as cursor:
            cursor.execute('''INSERT INTO frm_calculations
                (run_id,dataset_id,operation,parameters_json,result_json,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s)''',
                (identity,dataset_id,operation,codec.dumps(parameters),codec.dumps(result),source_sha256))
        return identity

    def load_calculation(self, run_id):
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT * FROM frm_calculations WHERE run_id=%s',(run_id,))
            row = cursor.fetchone()
        if row is None:
            raise KeyError(f'Calculation not found: {run_id}')
        row['parameters'] = codec.loads(row.pop('parameters_json'))
        row['result'] = codec.loads(row.pop('result_json'))
        return row

    def list_calculations(self, dataset_id, limit=100):
        with self.connection.cursor() as cursor:
            cursor.execute('''SELECT run_id,dataset_id,operation,source_sha256,created_at
                FROM frm_calculations WHERE dataset_id=%s ORDER BY created_at DESC,run_id LIMIT %s''',(dataset_id,limit))
            return pd.DataFrame(cursor.fetchall(),columns=['run_id','dataset_id','operation','source_sha256','created_at'])

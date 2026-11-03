"""市场风险工作台HTTP接口。所有SQL经data层，所有公式经计算适配层。"""
from contextlib import asynccontextmanager
from copy import deepcopy
import csv
from io import StringIO
import json

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.middleware.cors import CORSMiddleware
import pymysql

from data import Database, MySQLConfig
from data.workbench_repository import WorkbenchRepository
from controller.field_metadata import validate_field_metadata
from .jobs import JobManager
from .models import ExampleBody, JobBody, NameBody, PrepareBody, SavePreviewBody, UpdateBody
from .previews import PreviewStore, read_upload
from .serialization import browser_value, frame_page


def calculations():
    # 延迟加载，API模块可独立导入；只有明确注册的操作才能由网页调用。
    from controller import workbench_calculations
    return workbench_calculations


def metadata_with_fields(original, replacement, columns):
    result = deepcopy(original)
    if replacement is not None:
        # 来源与血缘由服务端维护；调用方只能编辑样本口径。
        result.update({k: deepcopy(v) for k, v in replacement.items() if k not in ('source', 'lineage')})
    validate_field_metadata(columns, result)
    return result


def csv_download(text, filename):
    return Response('\ufeff' + text, media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})


def record_csv(result):
    stream = StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['metric', 'value', 'unit'])
    for metric in result.get('metrics', []):
        writer.writerow([metric.get('name'), metric.get('value'), metric.get('unit', '')])
    for table in result.get('tables', []):
        writer.writerow([])
        writer.writerow([table['name']])
        writer.writerow(table['columns'])
        for row in table['rows']:
            writer.writerow([row.get(column) for column in table['columns']])
    return stream.getvalue()


def create_app(database=None):
    database = database or Database(MySQLConfig.load())
    previews = PreviewStore()
    jobs = JobManager()

    @asynccontextmanager
    async def lifespan(app):
        yield
        jobs.close()

    app = FastAPI(title='FRM 市场风险工作台', version='1.0', lifespan=lifespan)
    app.state.database = database
    app.state.jobs = jobs
    app.add_middleware(CORSMiddleware,
        allow_origin_regex=r'https?://(localhost|127\.0\.0\.1)(:\d+)?',
        allow_methods=['GET', 'POST', 'PATCH'], allow_headers=['Content-Type'])

    @app.middleware('http')
    async def local_origin_only(request: Request, call_next):
        # 本机应用不接受跨站网页发起的写入请求；开发代理不受影响。
        import re
        origin = request.headers.get('origin')
        if origin and not re.fullmatch(r'https?://(localhost|127\.0\.0\.1)(:\d+)?', origin):
            return JSONResponse({'detail': '仅允许本机工作台访问'}, status_code=403)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        first = error.errors()[0]
        field = '.'.join(str(x) for x in first['loc'])
        return JSONResponse({'detail': f'{field}: {first["msg"]}', 'field': field}, status_code=422)

    @app.exception_handler(KeyError)
    async def not_found(request, error):
        return JSONResponse({'detail': str(error).strip("'")}, status_code=404)

    @app.exception_handler(ValueError)
    async def invalid_value(request, error):
        return JSONResponse({'detail': str(error)}, status_code=422)

    @app.exception_handler(pymysql.MySQLError)
    async def database_error(request, error):
        return JSONResponse({'detail': '数据库暂不可用，请检查连接及数据库初始化状态。'}, status_code=503)

    @app.exception_handler(Exception)
    async def unexpected_error(request, error):
        return JSONResponse({'detail': '操作未完成，请检查本机服务日志或输入格式。'}, status_code=500)

    def reply(value):
        return JSONResponse(browser_value(value))

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'database': database.health()['database_name']}

    @app.get('/api/catalog')
    def catalog():
        return reply(calculations().catalog())

    @app.get('/api/examples')
    def examples():
        return reply({'items': calculations().examples()})

    @app.post('/api/previews/example')
    def preview_example(body: ExampleBody):
        frame, metadata = calculations().example_frame(body.example_id)
        return reply(previews.create(frame, metadata))

    @app.post('/api/previews/upload')
    async def preview_upload(file: UploadFile = File(...), sheet: str | None = Form(None)):
        content = await file.read(30 * 1024 * 1024 + 1)
        await file.close()
        if len(content) > 30 * 1024 * 1024:
            raise HTTPException(413, '文件超过30MB，请拆分后导入')
        try:
            frame, metadata, sheets = read_upload(file.filename, content, sheet)
        except (UnicodeError, ImportError) as error:
            raise ValueError('CSV请使用UTF-8编码；Excel请确认已安装对应读取依赖。') from error
        except ValueError:
            raise
        except Exception as error:
            raise ValueError('无法读取该文件，请确认文件格式及工作表内容。') from error
        return reply(previews.create(frame, metadata, sheets=sheets))

    def prepare(frame, metadata, body):
        metadata = metadata_with_fields(metadata, body.metadata, frame.columns)
        result, new_metadata, changes = calculations().prepare_frame(frame, metadata, body.options)
        lineage = deepcopy(metadata.get('lineage', {'steps': []}))
        lineage.setdefault('steps', []).append(deepcopy(body.options))
        new_metadata['lineage'] = lineage
        return previews.create(result, new_metadata, changes=changes)

    @app.post('/api/previews/{identity}/prepare')
    def prepare_preview(identity: str, body: PrepareBody):
        item = previews.get(identity)
        return reply(prepare(item['frame'], item['metadata'], body))

    @app.post('/api/previews/{identity}/save')
    def save_preview(identity: str, body: SavePreviewBody):
        item = previews.get(identity)
        metadata = metadata_with_fields(item['metadata'], body.metadata, item['frame'].columns)
        with database.session() as repository:
            dataset_id = repository.save_dataset(body.name, item['frame'], body.description, metadata)
            result, _ = WorkbenchRepository(repository).dataset(dataset_id)
        return reply(result)

    @app.get('/api/datasets')
    def list_datasets(q: str = '', archived: bool = False, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
        with database.session() as repository:
            result = WorkbenchRepository(repository).datasets(q, archived, offset, limit)
        return reply(result)

    @app.get('/api/datasets/{identity}')
    def dataset(identity: str, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
        with database.session() as repository:
            item, frame = WorkbenchRepository(repository).dataset(identity)
        return reply({**item, **frame_page(frame, offset, limit)})

    @app.post('/api/datasets/{identity}/prepare')
    def prepare_dataset(identity: str, body: PrepareBody):
        with database.session() as repository:
            item, frame = WorkbenchRepository(repository).dataset(identity)
        metadata = deepcopy(item['metadata'])
        metadata['lineage'] = {'parent_dataset_id': identity, 'steps': []}
        return reply(prepare(frame, metadata, body))

    @app.patch('/api/datasets/{identity}')
    def update_dataset(identity: str, body: UpdateBody):
        with database.session() as repository:
            result = WorkbenchRepository(repository).update_dataset(identity, body.name, body.archived)
        return reply(result)

    @app.get('/api/datasets/{identity}/export')
    def export_dataset(identity: str):
        with database.session() as repository:
            _, frame = WorkbenchRepository(repository).dataset(identity)
        return csv_download(frame.to_csv(index=False), f'dataset-{identity}.csv')

    @app.post('/api/jobs')
    def submit_job(body: JobBody):
        if body.operation not in {item['id'] for item in calculations().catalog()['operations']}:
            raise HTTPException(status_code=422, detail='未知网页计算操作')
        with database.session() as repository:
            snapshot = repository.load_dataset(body.dataset_id)
        return reply(jobs.submit(body.dataset_id, snapshot.frame, snapshot.metadata, body.operation, body.parameters))

    @app.get('/api/jobs')
    def list_jobs():
        return reply({'items': jobs.list()})

    @app.get('/api/jobs/{identity}')
    def job(identity: str):
        return reply(jobs.get(identity))

    @app.post('/api/jobs/{identity}/cancel')
    def cancel_job(identity: str):
        return reply(jobs.cancel(identity))

    @app.post('/api/jobs/{identity}/save')
    def save_job(identity: str, body: NameBody):
        job = jobs.get(identity, internal=True)
        if job['status'] != 'completed':
            raise HTTPException(409, '只有已完成的任务可以保存')
        with database.session() as repository:
            result = WorkbenchRepository(repository).save_result(job, body.name)
        jobs.mark_saved(identity, result['id'])
        return reply(result)

    @app.get('/api/records')
    def list_records(q: str = '', archived: bool = False, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
        with database.session() as repository:
            result = WorkbenchRepository(repository).records(q, archived, offset, limit)
        return reply(result)

    @app.get('/api/records/{identity}')
    def record(identity: str):
        with database.session() as repository:
            result = WorkbenchRepository(repository).record(identity)
        return reply(result)

    @app.patch('/api/records/{identity}')
    def update_record(identity: str, body: UpdateBody):
        with database.session() as repository:
            result = WorkbenchRepository(repository).update_record(identity, body.name, body.archived)
        return reply(result)

    @app.get('/api/records/{identity}/export')
    def export_record(identity: str, format: str = Query('json', pattern='^(json|csv)$')):
        with database.session() as repository:
            result = WorkbenchRepository(repository).record(identity)
        if format == 'csv':
            if result['legacy']:
                legacy = result['legacy_result']
                text = legacy.to_csv() if hasattr(legacy, 'to_csv') else 'value\n' + str(legacy)
            else:
                text = record_csv(result['result'])
            return csv_download(text, f'record-{identity}.csv')
        configuration = {k: result[k] for k in ('id', 'name', 'dataset_id', 'request', 'source_sha256', 'legacy')}
        return Response(json.dumps(browser_value(configuration), ensure_ascii=False, indent=2),
                        media_type='application/json', headers={'Content-Disposition': f'attachment; filename="config-{identity}.json"'})

    return app

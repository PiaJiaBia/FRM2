"""有界后台计算：每任务独立子进程，取消真实终止；结果不自动持久化。"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import multiprocessing as mp
from pathlib import Path
from threading import RLock
from uuid import uuid4

from service import source_fingerprint
from .serialization import browser_value


def implementation_fingerprint():
    """同时涵盖纯计算器及网页计算适配，避免只记录底层公式版本。"""
    digest = sha256(source_fingerprint().encode())
    controller = Path(__file__).resolve().parents[1] / 'controller'
    for path in sorted(controller.rglob('*.py')):
        digest.update(path.relative_to(controller).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _calculate(connection, frame, metadata, request):
    try:
        from controller.workbench_calculations import calculate_frame
        result = calculate_frame(frame, metadata, request)
        connection.send({'result': browser_value(result)})
    except (ValueError, KeyError, TypeError) as error:
        connection.send({'error': str(error)})
    except Exception:
        connection.send({'error': '计算失败，请检查输入是否满足模型条件。'})
    finally:
        connection.close()


class JobManager:
    def __init__(self, workers=2):
        self._jobs = {}
        self._lock = RLock()
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='frm-job')
        self._closed = False

    def submit(self, dataset_id, frame, metadata, operation, parameters):
        with self._lock:
            if self._closed:
                raise ValueError('任务服务正在关闭')
            if sum(j['status'] in ('queued', 'running') for j in self._jobs.values()) >= 20:
                raise ValueError('等待任务过多，请先完成或取消已有任务')
            identity = str(uuid4())
            job = {'id': identity, 'dataset_id': dataset_id, 'operation': operation,
                   'parameters': deepcopy(parameters), 'status': 'queued', 'progress': None,
                   'dataset_metadata': deepcopy(metadata), 'source_sha256': implementation_fingerprint(),
                   'created_at': datetime.now(timezone.utc).isoformat()}
            self._jobs[identity] = job
            job['_future'] = self._pool.submit(self._run, identity, frame.copy(deep=True))
            return self.get(identity)

    def _run(self, identity, frame):
        context = mp.get_context('spawn')
        receiver, sender = context.Pipe(duplex=False)
        process = None
        try:
            with self._lock:
                job = self._jobs[identity]
                if job['status'] == 'cancelled':
                    return
                request = {'operation': job['operation'], 'parameters': job['parameters']}
                process = context.Process(target=_calculate, args=(sender, frame, job['dataset_metadata'], request), daemon=True)
                process.start()
                sender.close()
                job['_process'] = process
                job['status'] = 'running'
            message = None
            while True:
                if receiver.poll(0.1):
                    try:
                        message = receiver.recv()
                    except EOFError:
                        pass
                    break
                with self._lock:
                    if self._jobs[identity]['status'] == 'cancelled':
                        return
                if not process.is_alive():
                    break
            with self._lock:
                job = self._jobs[identity]
                if job['status'] == 'cancelled':
                    return
                if message and 'result' in message:
                    job.update(status='completed', result=message['result'], progress=100)
                else:
                    job.update(status='failed', error=(message or {}).get('error', '计算进程意外退出，请重试。'))
        except Exception:
            with self._lock:
                if self._jobs[identity]['status'] != 'cancelled':
                    self._jobs[identity].update(status='failed', error='无法启动计算任务，请检查本机运行环境。')
        finally:
            sender.close()
            receiver.close()
            if process is not None:
                process.join(timeout=1)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)
            with self._lock:
                self._jobs[identity].pop('_process', None)

    def _find(self, identity):
        if identity not in self._jobs:
            raise KeyError('任务不存在或服务已重启')
        return self._jobs[identity]

    def get(self, identity, internal=False):
        with self._lock:
            job = self._find(identity)
            return deepcopy({k: v for k, v in job.items() if not k.startswith('_')
                             and (internal or k not in ('dataset_metadata', 'source_sha256'))})

    def list(self):
        with self._lock:
            return [self.get(identity) for identity in reversed(self._jobs)]

    def cancel(self, identity):
        with self._lock:
            job = self._find(identity)
            if job['status'] in ('queued', 'running'):
                job['status'] = 'cancelled'
                job.pop('result', None)
                future = job.get('_future')
                if future:
                    future.cancel()
                process = job.get('_process')
                if process is not None and process.is_alive():
                    process.terminate()
            return self.get(identity)

    def mark_saved(self, identity, record_id):
        with self._lock:
            self._find(identity)['record_id'] = record_id

    def close(self):
        with self._lock:
            self._closed = True
            for identity in list(self._jobs):
                self.cancel(identity)
        self._pool.shutdown(wait=True, cancel_futures=True)

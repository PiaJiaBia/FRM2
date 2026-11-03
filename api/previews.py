"""上传和派生数据的临时预览；只有用户保存时才生成数据库快照。"""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from threading import RLock
from uuid import uuid4

import pandas as pd

from .serialization import frame_page


class PreviewStore:
    def __init__(self):
        self._items = {}
        self._lock = RLock()

    def create(self, frame, metadata=None, **extra):
        if frame.empty:
            raise ValueError('数据表为空')
        frame = frame.copy(deep=True)
        frame.columns = [str(column) for column in frame.columns]
        if not frame.columns.is_unique:
            raise ValueError('列名必须唯一')
        identity = str(uuid4())
        with self._lock:
            self._items[identity] = {'id': identity, 'frame': frame, 'metadata': deepcopy(metadata or {}), **deepcopy(extra)}
        return self.view(identity)

    def get(self, identity):
        with self._lock:
            if identity not in self._items:
                raise KeyError('预览不存在或服务已重启，请重新导入')
            item = self._items[identity]
            return {**deepcopy({k: v for k, v in item.items() if k != 'frame'}), 'frame': item['frame'].copy(deep=True)}

    def view(self, identity):
        item = self.get(identity)
        frame = item.pop('frame')
        return {**item, **frame_page(frame), 'row_count': len(frame)}


def read_upload(filename, content, sheet=None):
    suffix = Path(filename or '').suffix.lower()
    stream = BytesIO(content)
    if suffix == '.csv':
        frame = pd.read_csv(stream, encoding='utf-8-sig')
        sheets = []
    elif suffix in ('.xlsx', '.xls'):
        with pd.ExcelFile(stream) as book:
            sheets = book.sheet_names
            if sheet is not None and sheet not in sheets:
                raise ValueError('所选工作表不存在')
            frame = pd.read_excel(book, sheet_name=sheet or sheets[0])
    else:
        raise ValueError('请选择CSV、XLSX或XLS文件')
    metadata = {'fields': {str(column): {'kind': 'other', 'unit': 'other', 'sign': 'none'} for column in frame.columns},
                'source': {'filename': Path(filename).name, 'sheet': sheet or (sheets[0] if sheets else None)}}
    return frame, metadata, sheets

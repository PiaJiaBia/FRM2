"""无pickle的带类型JSON：保存DataFrame/Series结构、数值缺失和非有限结果。"""
from datetime import date, datetime
import json
import math

import numpy as np
import pandas as pd


def _dtype(dtype):
    if isinstance(dtype, pd.CategoricalDtype):
        return {'name': 'category', 'categories': _encode(dtype.categories.tolist()), 'ordered': dtype.ordered}
    return {'name': str(dtype)}


def _restore_dtype(spec):
    if spec['name'] == 'category':
        return pd.CategoricalDtype(_decode(spec['categories']), ordered=spec['ordered'])
    return spec['name']


def _encode(value):
    if isinstance(value, pd.DataFrame):
        range_index = None
        if isinstance(value.index, pd.RangeIndex):
            range_index = [value.index.start, value.index.stop, value.index.step]
        return {'type': 'dataframe', 'value': _encode(value.to_dict(orient='tight')),
                'dtypes': [_dtype(dtype) for dtype in value.dtypes], 'range_index': range_index,
                'frequency': value.index.freqstr if isinstance(value.index, pd.DatetimeIndex) else None}
    if isinstance(value, pd.Series):
        return {'type': 'series', 'name': _encode(value.name), 'frame': _encode(value.to_frame(name='value'))}
    if value is pd.NA:
        return {'type': 'missing'}
    if value is pd.NaT:
        return {'type': 'nat'}
    if isinstance(value, np.ndarray):
        return {'type': 'array', 'dtype': str(value.dtype), 'value': _encode(value.tolist())}
    if isinstance(value, (pd.Timestamp, datetime)):
        return {'type': 'timestamp', 'value': value.isoformat()}
    if isinstance(value, pd.Timedelta):
        return {'type': 'timedelta', 'value': value.value}
    if isinstance(value, date):
        return {'type': 'date', 'value': value.isoformat()}
    if isinstance(value, np.generic):
        return _encode(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return {'type': 'float', 'value': 'nan' if math.isnan(value) else ('inf' if value>0 else '-inf')}
    if isinstance(value, dict):
        return {'type': 'mapping', 'value': [[_encode(k), _encode(v)] for k,v in value.items()]}
    if isinstance(value, tuple):
        return {'type': 'tuple', 'value': [_encode(x) for x in value]}
    if isinstance(value, list):
        return [_encode(x) for x in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f'Unsupported persisted value: {type(value).__name__}')


def _decode(value):
    if isinstance(value, list):
        return [_decode(x) for x in value]
    if not isinstance(value, dict):
        return value
    kind = value['type']
    if kind == 'dataframe':
        frame = pd.DataFrame.from_dict(_decode(value['value']), orient='tight')
        for i,spec in enumerate(value['dtypes']):
            frame.isetitem(i, frame.iloc[:,i].astype(_restore_dtype(spec)))
        if value['range_index'] is not None:
            frame.index = pd.RangeIndex(*value['range_index'], name=frame.index.name)
        elif value['frequency']:
            frame.index = pd.DatetimeIndex(frame.index, freq=value['frequency'], name=frame.index.name)
        return frame
    if kind == 'series':
        series = _decode(value['frame']).iloc[:,0]
        series.name = _decode(value['name'])
        return series
    if kind == 'mapping':
        return {_decode(k): _decode(v) for k,v in value['value']}
    if kind == 'tuple':
        return tuple(_decode(x) for x in value['value'])
    if kind == 'array':
        return np.asarray(_decode(value['value']), dtype=value['dtype'])
    if kind == 'timestamp':
        return pd.Timestamp(value['value'])
    if kind == 'timedelta':
        return pd.Timedelta(value['value'], unit='ns')
    if kind == 'date':
        return date.fromisoformat(value['value'])
    if kind == 'missing':
        return pd.NA
    if kind == 'nat':
        return pd.NaT
    if kind == 'float':
        return float(value['value'])
    raise ValueError(f'Unknown serialized type: {kind}')


def dumps(value):
    return json.dumps({'format': 'frm-json-v1', 'payload': _encode(value)},
                      ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def loads(text):
    envelope = json.loads(text)
    if envelope['format'] != 'frm-json-v1':
        raise ValueError('Unsupported FRM JSON format')
    return _decode(envelope['payload'])

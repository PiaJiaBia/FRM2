"""稳定浏览器格式，与data.codec的持久化格式分开。"""
from datetime import date, datetime
import math

import numpy as np
import pandas as pd


def browser_value(value):
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return browser_value(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None if math.isnan(value) else ('Infinity' if value > 0 else '-Infinity')
    if isinstance(value, pd.DataFrame):
        return {'columns': [str(x) for x in value.columns], 'rows': browser_value(value.to_dict(orient='records'))}
    if isinstance(value, pd.Series):
        return browser_value(value.to_dict())
    if isinstance(value, np.ndarray):
        return browser_value(value.tolist())
    if isinstance(value, dict):
        return {str(k): browser_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [browser_value(x) for x in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def frame_page(frame, offset=0, limit=100):
    return {'columns': [str(x) for x in frame.columns],
            'rows': browser_value(frame.iloc[offset:offset + limit].to_dict(orient='records')),
            'total_rows': len(frame)}

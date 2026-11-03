"""调用层的显式准备；原始DataFrame与字段元数据均不原地修改。"""
from copy import deepcopy

import numpy as np
import pandas as pd

from service import load_chapter
from .workbench_catalog import field
from .field_metadata import validate_field_metadata


def numeric_column(df, name, minimum=1, allow_missing=False):
    if name not in df.columns:
        raise ValueError(f'字段 {name!r} 不存在，请选择有效列')
    values = df[name]
    if not pd.api.types.is_numeric_dtype(values.dtype) or pd.api.types.is_bool_dtype(values.dtype):
        raise ValueError(f'字段 {name} 必须是数值列，请先确认导入类型')
    if len(values) < minimum:
        raise ValueError(f'字段 {name} 至少需要 {minimum} 个观测')
    array = values.to_numpy(dtype=float, na_value=np.nan)
    if np.isinf(array).any() or (not allow_missing and np.isnan(array).any()):
        raise ValueError(f'字段 {name} 存在缺失或无穷值；请在数据准备中显式处理后计算')
    return values


def validate_fields(df, metadata):
    validate_field_metadata(df.columns, metadata)


def prepare_frame(df, metadata, options):
    """顺序为重命名→日期解析→排序→删除缺失→显式转换→派生。

    派生自然产生的首行缺失不自动删除；再次调用dropna步骤可显式删除。
    """
    options = options or {}
    unknown = options.keys() - {'rename', 'date_column', 'sort_by', 'dropna_columns', 'conversions', 'derive'}
    if unknown:
        raise ValueError(f'未知准备选项：{sorted(unknown)}')
    frame = df.copy(deep=True)
    meta = deepcopy(metadata or {})
    meta.setdefault('fields', {})
    validate_fields(frame, meta)
    rename = options.get('rename') or {}
    if not isinstance(rename, dict):
        raise ValueError('rename必须是旧列名到新列名的映射')
    frame = frame.rename(columns=rename, errors='raise')
    meta['fields'] = {rename.get(name, name): spec for name, spec in meta['fields'].items()}
    if meta.get('date_column') in rename:
        meta['date_column'] = rename[meta['date_column']]
    validate_fields(frame, meta)
    date = options.get('date_column')
    if date:
        if date not in frame.columns:
            raise ValueError(f'日期字段 {date} 不存在')
        frame[date] = pd.to_datetime(frame[date], errors='raise')
        meta['fields'][date] = field('date', 'date', 'none')
        meta['date_column'] = date
    if options.get('sort_by'):
        frame = frame.sort_values(options['sort_by'], kind='stable')
    if options.get('dropna_columns'):
        frame = frame.dropna(subset=options['dropna_columns'])
    for conversion in options.get('conversions') or []:
        column, kind = conversion.get('column'), conversion.get('kind')
        numeric_column(frame, column, allow_missing=True)
        spec = meta['fields'].get(column)
        if not spec:
            raise ValueError(f'转换前请确认 {column} 的字段口径')
        if kind == 'percent_to_decimal':
            if spec['unit'] != 'percent':
                raise ValueError(f'{column} 不是百分数单位，不能再次除以100')
            frame[column] = frame[column] / 100
            spec['unit'] = 'decimal'
        elif kind == 'loss_to_profit':
            if spec['sign'] != 'loss':
                raise ValueError(f'{column} 不是损失为正的列，不能再次反号')
            frame[column] = -frame[column]
            spec['sign'] = 'profit'
            if spec['kind'] == 'loss':
                spec['kind'] = 'pnl' if spec['unit'] == 'amount' else 'arithmetic_return'
        else:
            raise ValueError(f'未知转换：{kind}')
    chapter = load_chapter(1)
    operations = {name: getattr(chapter, 'cal_' + name)
                  for name in ['pnl', 'pvpnl', 'fvpnl', 'arithmetic_return', 'geometric_return']}
    added = []
    for derivation in options.get('derive') or []:
        operation = derivation.get('operation')
        if operation not in operations:
            raise ValueError(f'未知派生计算：{operation}')
        if operation in frame.columns:
            raise ValueError(f'结果列 {operation} 已存在；请先重命名，避免覆盖已有列')
        parameters = dict(derivation.get('parameters') or {})
        allowed = {'value_column', 'payment_column'}
        if operation in ('pvpnl', 'fvpnl'):
            allowed |= {'rate_column', 'periods_per_year'}
        if parameters.keys() - allowed:
            raise ValueError(f'{operation} 包含未知参数')
        value = parameters.get('value_column', 'book_value')
        payment = parameters.get('payment_column', 'interim_payments')
        numeric_column(frame, value, minimum=2)
        numeric_column(frame, payment, minimum=2)
        if meta['fields'].get(value, {}).get('kind') != 'price' or meta['fields'].get(value, {}).get('unit') != 'amount':
            raise ValueError('价格/账面价值列必须确认 kind=price、unit=amount')
        if meta['fields'].get(payment, {}).get('kind') != 'payment' or meta['fields'].get(payment, {}).get('unit') != 'amount':
            raise ValueError('现金流列必须确认 kind=payment、unit=amount；无现金流时请提供显式零列')
        if operation.endswith('return'):
            if (frame[value] <= 0).any():
                raise ValueError('收益率计算需要正的前期价格/账面价值')
            if operation == 'geometric_return' and ((frame[value] + frame[payment]) <= 0).any():
                raise ValueError('对数收益率需要价格加现金流为正')
        if operation in ('pvpnl', 'fvpnl'):
            rate = parameters.get('rate_column', 'discount_rate')
            numeric_column(frame, rate)
            if meta['fields'].get(rate, {}).get('kind') != 'rate' or meta['fields'].get(rate, {}).get('unit') != 'decimal':
                raise ValueError('贴现率必须确认 kind=rate、unit=decimal')
            periods = parameters.get('periods_per_year', 252)
            if not isinstance(periods, (int, float)) or not np.isfinite(periods) or periods <= 0:
                raise ValueError('年化期数必须为正数')
            if operation == 'pvpnl' and (1 + frame[rate] / periods <= 0).any():
                raise ValueError('折现因子必须为正')
        frame = operations[operation](frame, **parameters)
        meta['fields'][operation] = field(operation if operation.endswith('return') else 'pnl',
                                          'decimal' if operation.endswith('return') else 'amount')
        added.append(operation)
    meta.setdefault('preparation', []).append(deepcopy(options))
    validate_fields(frame, meta)
    return frame, meta, {'before_rows': len(df), 'after_rows': len(frame),
                         'dropped_rows': len(df) - len(frame), 'added_columns': added}

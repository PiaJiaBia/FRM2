"""HTTP保存和计算准备共享的字段口径约定；不属于纯计算器。"""


def validate_field_metadata(columns, metadata):
    if not isinstance(metadata, dict):
        raise ValueError('数据元信息必须为对象')
    columns = list(columns)
    if not all(isinstance(column, str) for column in columns) or len(set(columns)) != len(columns):
        raise ValueError('网页数据列名必须是唯一字符串')
    fields = metadata.get('fields', {})
    if not isinstance(fields, dict):
        raise ValueError('字段元数据 fields 必须为对象')
    for name, spec in fields.items():
        if name not in columns:
            raise ValueError(f'字段元数据包含不存在的列 {name}')
        if not isinstance(spec, dict):
            raise ValueError(f'字段 {name} 的口径必须为对象')
        if spec.get('kind') not in {'date', 'price', 'payment', 'rate', 'arithmetic_return', 'geometric_return', 'pnl', 'loss', 'other'}:
            raise ValueError(f'字段 {name} 需要有效的含义 kind')
        if spec.get('unit') not in {'decimal', 'percent', 'amount', 'date', 'other'}:
            raise ValueError(f'字段 {name} 需要有效的单位 unit')
        if spec.get('sign') not in {'profit', 'loss', 'none'}:
            raise ValueError(f'字段 {name} 需要明确正负号约定 sign')

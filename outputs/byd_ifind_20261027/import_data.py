import csv
import json
import os
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parent
TABLE = 'raw_ifind_stock_close_af_daily'
DATABASE = 'assets_return_forecast'
obj = json.loads((ROOT / 'ifind_raw.json').read_text(encoding='utf-8'), parse_float=Decimal)
assert obj.get('errorcode', 0) == 0
rows, excluded = [], []
for block in obj['tables']:
    assert block['thscode'] == '002594.SZ'
    dates = block['time']
    prices = block['table']['ths_close_price_stock']
    factors = block['table']['ths_af_stock']
    assert len(dates) == len(prices) == len(factors)
    for d, price, factor in zip(dates, prices, factors):
        if d > '2026-10-26':
            excluded.append(d)
            continue
        assert '2021-10-31' <= d
        assert price is not None and factor is not None, f'Missing data: {d}'
        price, factor = Decimal(str(price)), Decimal(str(factor))
        assert price.is_finite() and factor.is_finite() and price > 0 and factor > 0
        rows.append((date.fromisoformat(d), block['thscode'], price, factor))
rows.sort()
assert rows and len({(r[0], r[1]) for r in rows}) == len(rows)

conn = pymysql.connect(host='10.8.100.149', user='luyichen',
                       password=os.environ['TASK_MYSQL_PASSWORD'],
                       database=DATABASE, charset='utf8mb4', connect_timeout=10)
try:
    with conn.cursor() as cur:
        # Plain CREATE intentionally fails if the table already exists.
        cur.execute(f'''CREATE TABLE `{TABLE}` (
            `trade_date` DATE NOT NULL,
            `thscode` VARCHAR(16) NOT NULL,
            `ths_close_price_stock` DECIMAL(24,12) NOT NULL COMMENT 'iFinD close price, parameter 0, CNY',
            `ths_af_stock` DECIMAL(24,12) NOT NULL COMMENT 'iFinD adjustment factor, original field',
            `imported_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (`thscode`, `trade_date`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        COMMENT='iFinD THS_DS; 002594.SZ; requested 2021-10-31 to 2026-10-31; complete closes through 2026-10-26' ''')
        cur.executemany(f'INSERT INTO `{TABLE}` (trade_date, thscode, ths_close_price_stock, ths_af_stock) VALUES (%s,%s,%s,%s)', rows)
    conn.commit()
    with conn.cursor() as cur:
        cur.execute(f'SELECT trade_date, thscode, ths_close_price_stock, ths_af_stock FROM `{TABLE}` ORDER BY trade_date, thscode')
        stored = cur.fetchall()
    assert list(stored) == rows, 'Database readback differs from source'
finally:
    conn.close()

csv_path = ROOT / '002594_SZ_close_af_20211101_20261026.csv'
headers = ['trade_date', 'thscode', 'ths_close_price_stock', 'ths_af_stock']
def decimal_text(v):
    return format(v, 'f').rstrip('0').rstrip('.') if isinstance(v, Decimal) else str(v)
with csv_path.open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows([[decimal_text(v) for v in row] for row in stored])
with csv_path.open(encoding='utf-8-sig', newline='') as f:
    exported = list(csv.DictReader(f))
assert len(exported) == len(rows)
for actual, expected in zip(exported, rows):
    assert (date.fromisoformat(actual['trade_date']), actual['thscode'], Decimal(actual['ths_close_price_stock']), Decimal(actual['ths_af_stock'])) == expected
summary = {
    'database': DATABASE, 'table': TABLE, 'rows': len(rows),
    'first_date': str(rows[0][0]), 'last_date': str(rows[-1][0]),
    'source': "THS_DS('002594.SZ','ths_close_price_stock;ths_af_stock','0;','','2021-10-31','2026-10-31')",
    'excluded_dates': excluded,
    'exclusion_reason': '2026-10-27 not yet closed at retrieval; subsequent dates are future; API filled these dates with previous close',
    'missing_values': 0, 'duplicate_keys': 0,
    'csv': str(csv_path), 'csv_encoding': 'UTF-8 BOM',
    'verified_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
    'notes': 'Raw requested fields only; no adjusted-price or return calculation.'
}
(ROOT / 'import_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))

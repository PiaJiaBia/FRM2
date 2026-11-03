import { Select, Table, Typography } from 'antd';
import type { Field, Metadata } from '../types';

const kinds = [ ['date', '日期'], ['price', '价格/账面价值'], ['payment', '期间现金流'], ['rate', '利率'], ['arithmetic_return', '算术收益率'], ['geometric_return', '对数收益率'], ['pnl', '损益 P&L'], ['loss', '损失'], ['other', '其他'] ];
const units = [['decimal', '小数'], ['percent', '百分数'], ['amount', '金额'], ['date', '日期'], ['other', '其他']];
const signs = [['profit', '盈利为正'], ['loss', '损失为正'], ['none', '不适用']];
const options = (items: string[][]) => items.map(([value, label]) => ({ value, label }));
export function completeMetadata(columns: string[], metadata: Metadata): Metadata {
  return { ...metadata, fields: Object.fromEntries(columns.map(column => [column, metadata.fields?.[column] ?? { kind: 'other', unit: 'other', sign: 'none' }])) };
}

export function FieldEditor({ columns, value, onChange }: { columns: string[]; value: Metadata; onChange: (value: Metadata) => void }) {
  const update = (column: string, property: keyof Field, next: string) => {
    const metadata = completeMetadata(columns, value);
    onChange({ ...metadata, fields: { ...metadata.fields, [column]: { ...metadata.fields![column], [property]: next } } });
  };
  const rows = columns.map(column => ({ column, ...(value.fields?.[column] ?? { kind: 'other', unit: 'other', sign: 'none' }) }));
  return <><Typography.Paragraph type="secondary">确认每列的含义、单位与符号。这里只声明口径；百分数转小数、损失转损益需在“数据准备”中显式执行。</Typography.Paragraph>
    <Table size="small" pagination={false} scroll={{ x: 690 }} rowKey="column" dataSource={rows} columns={[
      { title: '原始字段', dataIndex: 'column', width: 180 },
      { title: '字段含义', render: (_, row) => <Select aria-label={`${row.column} 字段含义`} value={row.kind} options={options(kinds)} style={{ width: 160 }} onChange={next => update(row.column, 'kind', next)} /> },
      { title: '单位', render: (_, row) => <Select aria-label={`${row.column} 单位`} value={row.unit} options={options(units)} style={{ width: 120 }} onChange={next => update(row.column, 'unit', next)} /> },
      { title: '正负号', render: (_, row) => <Select aria-label={`${row.column} 正负号`} value={row.sign} options={options(signs)} style={{ width: 140 }} onChange={next => update(row.column, 'sign', next)} /> },
    ]} />
  </>;
}

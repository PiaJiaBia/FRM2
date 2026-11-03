import { Button, Form, Input, InputNumber, Select, Space, Typography } from 'antd';
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';

export interface PrepareOptions { rename?: Record<string, string>; date_column?: string; sort_by?: string[]; dropna_columns?: string[]; conversions?: { column: string; kind: string }[]; derive?: { operation: string; parameters: Record<string, unknown> }[] }
interface Values { rename?: { from: string; to: string }[]; date_column?: string; sort_by?: string[]; dropna_columns?: string[]; conversions?: { column: string; kind: string }[]; derive?: { operation: string; value_column?: string; payment_column?: string; rate_column?: string; periods_per_year?: number }[] }

export function PrepareForm({ columns, busy, onPrepare }: { columns: string[]; busy: boolean; onPrepare: (options: PrepareOptions) => void }) {
  const [form] = Form.useForm<Values>();
  const colOptions = columns.map(value => ({ value, label: value }));
  const renames = Form.useWatch('rename', form) ?? [];
  const preparedColumns = columns.map(column => renames.find((item: { from?: string; to?: string } | undefined) => item?.from === column)?.to || column);
  const preparedOptions = preparedColumns.map(value => ({ value, label: value }));
  const submit = (values: Values) => {
    const options: PrepareOptions = { date_column: values.date_column, sort_by: values.sort_by, dropna_columns: values.dropna_columns, conversions: values.conversions };
    if (values.rename?.length) options.rename = Object.fromEntries(values.rename.map(item => [item.from, item.to]));
    if (values.derive?.length) options.derive = values.derive.map(({ operation, ...parameters }) => ({ operation, parameters: Object.fromEntries(Object.entries(parameters).filter(([, value]) => value !== undefined && value !== '')) }));
    onPrepare(options);
  };
  return <Form form={form} layout="vertical" onFinish={submit}>
    <Typography.Paragraph type="secondary">仅执行你选择的步骤：重命名 → 日期解析 → 排序 → 删除指定缺失行 → 单位/符号转换 → 派生计算。派生收益率的首行缺失会保留，可在生成预览后再执行一次缺失处理。涉及重命名时，后续步骤使用新列名。</Typography.Paragraph>
    <div className="form-grid"><Form.Item name="date_column" label="日期列（可选）"><Select allowClear options={preparedOptions} /></Form.Item>
      <Form.Item name="sort_by" label="排序字段（按选择顺序）"><Select mode="tags" options={preparedOptions} /></Form.Item>
      <Form.Item name="dropna_columns" label="明确删除这些列含缺失值的行"><Select mode="tags" options={preparedOptions} /></Form.Item></div>
    <Form.List name="rename">{(fields, { add, remove }) => <div className="prepare-section"><Typography.Text strong>字段重命名</Typography.Text>{fields.map(field => <Space key={field.key} align="baseline" wrap>
      <Form.Item name={[field.name, 'from']} rules={[{ required: true, message: '选择原始列' }]}><Select placeholder="原始列" options={colOptions} style={{ width: 180 }} /></Form.Item>
      <Form.Item name={[field.name, 'to']} rules={[{ required: true, message: '填写新名称' }]}><Input placeholder="新列名" /></Form.Item><Button type="text" aria-label="删除重命名" icon={<MinusCircleOutlined />} onClick={() => remove(field.name)} />
    </Space>)}<Button type="dashed" size="small" icon={<PlusOutlined />} onClick={() => add()}>添加重命名</Button></div>}</Form.List>
    <Form.List name="conversions">{(fields, { add, remove }) => <div className="prepare-section"><Typography.Text strong>单位与符号转换</Typography.Text>{fields.map(field => <Space key={field.key} align="baseline" wrap>
      <Form.Item name={[field.name, 'column']} rules={[{ required: true }]}><Select showSearch placeholder="字段" options={preparedOptions} style={{ width: 180 }} /></Form.Item>
      <Form.Item name={[field.name, 'kind']} rules={[{ required: true }]}><Select placeholder="转换方式" style={{ width: 210 }} options={[{ value: 'percent_to_decimal', label: '百分数 → 小数' }, { value: 'loss_to_profit', label: '损失为正 → 盈利为正' }]} /></Form.Item><Button type="text" aria-label="删除转换" icon={<MinusCircleOutlined />} onClick={() => remove(field.name)} />
    </Space>)}<Button type="dashed" size="small" icon={<PlusOutlined />} onClick={() => add()}>添加转换</Button></div>}</Form.List>
    <Form.List name="derive">{(fields, { add, remove }) => <div className="prepare-section"><Typography.Text strong>生成 P&L / 收益率</Typography.Text>{fields.map(field => <div className="derive-row" key={field.key}>
      <Form.Item label="计算方式" name={[field.name, 'operation']} rules={[{ required: true }]}><Select options={[{ value: 'pnl', label: '期间 P&L' }, { value: 'pvpnl', label: '现值 P&L' }, { value: 'fvpnl', label: '终值 P&L' }, { value: 'arithmetic_return', label: '算术收益率' }, { value: 'geometric_return', label: '对数收益率' }]} /></Form.Item>
      <Form.Item label="价格/账面价值列" name={[field.name, 'value_column']} rules={[{ required: true }]}><Select options={preparedOptions} /></Form.Item>
      <Form.Item label="期间现金流列" name={[field.name, 'payment_column']} rules={[{ required: true }]}><Select options={preparedOptions} /></Form.Item>
      <Form.Item label="利率列（PV/FV）" name={[field.name, 'rate_column']}><Select allowClear options={preparedOptions} /></Form.Item>
      <Form.Item label="每年期数（PV/FV）" name={[field.name, 'periods_per_year']}><InputNumber min={1} /></Form.Item>
      <Button type="text" aria-label="删除派生" icon={<MinusCircleOutlined />} onClick={() => remove(field.name)} />
    </div>)}<Button type="dashed" size="small" icon={<PlusOutlined />} onClick={() => add({ operation: 'arithmetic_return', periods_per_year: 252 })}>添加计算</Button></div>}</Form.List>
    <Button type="primary" htmlType="submit" loading={busy}>生成处理预览</Button>
  </Form>;
}

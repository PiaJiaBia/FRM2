import { useEffect, useMemo, useState } from 'react';
import { Alert, App, Button, Card, Collapse, Empty, Form, Input, InputNumber, Modal, Select, Space, Spin, Tabs, Tag, Typography } from 'antd';
import { CalculatorOutlined, DownloadOutlined, SaveOutlined } from '@ant-design/icons';
import { api, downloadBlob, post } from '../api';
import type { CalculationRequest, Catalog, Dataset, Job, Operation, Page, Parameter, SavedRecord } from '../types';
import { ResultView } from '../components/ResultView';

interface Props { catalog?: Catalog; revision: number; selectedDataset?: Dataset; selectedJob?: Job; reopen?: { request: CalculationRequest; key: number }; onJob: (job: Job) => void; onSaved: () => void; onPrepare: (id?: string) => void }

function shown(parameter: Parameter, operation: string, values: Record<string, unknown>) {
  const key = parameter.name;
  if (key === 'arithmetic_column' || key === 'geometric_column') return operation === 'var' && values.model === 'compare';
  if (key === 'target_column') return values.model !== 'compare';
  if (key === 'gamma') return values.weight === 'exponential';
  if (key === 'confidence_level' && operation === 'spectral') return values.weight !== 'exponential';
  if (key === 'n_resamples' || key === 'seed') return operation === 'standard_error' && values.method === 'bootstrap';
  if (key === 'n_slices') return values.method === 'slices' || (operation === 'standard_error' && values.method === 'spectral');
  return true;
}

export default function Calculate({ catalog, revision, selectedDataset, selectedJob, reopen, onJob, onSaved, onPrepare }: Props) {
  const { message } = App.useApp();
  const [chapter, setChapter] = useState(1); const [operationId, setOperationId] = useState('var');
  const [datasets, setDatasets] = useState<Dataset[]>([]); const [dataset, setDataset] = useState<Dataset>();
  const [datasetId, setDatasetId] = useState<string>(); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [saveOpen, setSaveOpen] = useState(false); const [saveName, setSaveName] = useState('');
  const [form] = Form.useForm<Record<string, unknown>>(); const values = Form.useWatch([], form) ?? {};
  const operation = catalog?.operations.find(item => item.id === operationId);
  const activeChapter = catalog?.chapters.find(item => item.number === chapter);
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const all: Dataset[] = []; let offset = 0;
        do { const result = await api<Page<Dataset>>(`/datasets?archived=false&offset=${offset}&limit=100`); all.push(...result.items); offset += result.items.length; if (offset >= result.total || !result.items.length) break; } while (active);
        if (active) setDatasets(all);
      } catch (e) { if (active) setError((e as Error).message); }
    }
    void load(); return () => { active = false; };
  }, [revision]);
  useEffect(() => { if (selectedDataset) { setDatasetId(selectedDataset.id); setChapter(1); } }, [selectedDataset]);
  useEffect(() => {
    if (!datasetId) { setDataset(undefined); return; }
    let active = true;
    api<Dataset>(`/datasets/${datasetId}`).then(value => { if (active) { setDataset(value); setError(''); } }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [datasetId, revision]);
  useEffect(() => { if (operation) { form.resetFields(); form.setFieldsValue(Object.fromEntries(operation.parameters.filter(p => p.default !== undefined).map(p => [p.name, p.default]))); } }, [operation, form]);
  useEffect(() => {
    if (reopen && operation?.id === reopen.request.operation) form.setFieldsValue(reopen.request.parameters);
  }, [reopen, operation, form]);
  useEffect(() => {
    if (reopen) { setDatasetId(reopen.request.dataset_id); setOperationId(reopen.request.operation); setChapter(1); }
  }, [reopen]);
  const columnOptions = useMemo(() => (dataset?.columns ?? []).map(column => {
    const field = dataset?.metadata.fields?.[column];
    return { value: column, label: field ? `${column} · ${field.kind} / ${field.unit}` : column };
  }), [dataset]);
  const optionsFor = (parameter: Parameter) => columnOptions.map(option => {
    const field = dataset?.metadata.fields?.[option.value];
    if (operationId === 'diagnostics') return option;
    const model = parameter.name === 'arithmetic_column' ? 'normal' : parameter.name === 'geometric_column' ? 'lognormal' : values.model;
    const compatible = field && (model === 'historical'
      ? ['arithmetic_return', 'pnl', 'loss'].includes(field.kind) && ['decimal', 'amount'].includes(field.unit) && (field.kind !== 'arithmetic_return' || field.unit === 'decimal') && field.sign !== 'none'
      : field.kind === (model === 'normal' ? 'arithmetic_return' : 'geometric_return') && field.unit === 'decimal' && field.sign === 'profit');
    return { ...option, disabled: !compatible };
  });
  const datasetOptions = [...datasets, ...(dataset && !datasets.some(d => d.id === dataset.id) ? [dataset] : [])].map(item => ({ value: item.id, label: `${item.name}${item.archived ? '（已归档）' : ''} · ${item.row_count} 行` }));
  const submit = async (input: Record<string, unknown>) => {
    if (!datasetId || !operation) { message.warning('请先选择数据集'); return; }
    setBusy(true); setError('');
    try {
      const parameters = Object.fromEntries(operation.parameters.filter(p => shown(p, operationId, input)).filter(p => input[p.name] !== undefined).map(p => [p.name, input[p.name]]));
      const job = await post<Job>('/jobs', { dataset_id: datasetId, operation: operationId, parameters }); onJob(job);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const save = async () => {
    if (!selectedJob) return; setBusy(true);
    try { const record = await post<SavedRecord>(`/jobs/${selectedJob.id}/save`, { name: saveName.trim() }); onJob({ ...selectedJob, record_id: record.id }); setSaveOpen(false); message.success('计算记录已保存'); onSaved(); }
    catch (e) { message.error((e as Error).message); } finally { setBusy(false); }
  };
  const exportConfig = () => {
    if (!selectedJob) return;
    const request: CalculationRequest = { dataset_id: selectedJob.dataset_id, operation: selectedJob.operation, parameters: selectedJob.parameters };
    downloadBlob(new Blob([JSON.stringify(request, null, 2)], { type: 'application/json' }), 'calculation-config.json');
  };
  const ready = activeChapter?.available ?? chapter === 1;
  return <>
    <div className="page-heading"><div><div className="eyebrow">CHAPTER WORKSPACE</div><Typography.Title level={2}>章节计算</Typography.Title><Typography.Text type="secondary">从公式到结果，用同一份样本探索风险。</Typography.Text></div><Select aria-label="章节" value={chapter} style={{ width: 380 }} onChange={setChapter} options={catalog?.chapters.map(item => ({ value: item.number, label: `第 ${item.number} 章 · ${item.title}${!item.available ? ' · 未接入' : ''}` }))} /></div>
    {!ready ? <Card><Empty description={<><Typography.Title level={4}>{activeChapter?.title}</Typography.Title><p>第 {chapter} 章计算器已存在，网页操作尚未接入。</p><Tag>教材 pp. {activeChapter?.pages}</Tag></>} /><div className="center"><Button onClick={() => setChapter(1)}>返回第 1 章工作区</Button></div></Card> : <>
      <div className="chapter-banner"><div><span>CHAPTER 01</span><h3>Estimating Market Risk Measures</h3><p>市场风险度量 · 教材 pp. 2–16</p></div><CalculatorOutlined /></div>
      <Tabs activeKey={operationId} onChange={key => { if (key === 'prepare') onPrepare(datasetId); else setOperationId(key); }} items={[
        { key: 'prepare', label: '数据准备' },
        ...((catalog?.operations ?? []).map(item => ({ key: item.id, label: item.name }))),
      ]} />
      <Card title="配置计算" extra={<Tag color="green">第 1 章</Tag>}>
        <div className="dataset-picker"><Typography.Text strong>样本数据集</Typography.Text><Select aria-label="计算数据集" showSearch optionFilterProp="label" placeholder="选择已保存的数据集" value={datasetId} onChange={setDatasetId} options={datasetOptions} style={{ minWidth: 330, flex: 1 }} /><Button onClick={() => onPrepare(datasetId)}>查看 / 准备数据</Button></div>
        {dataset && <Space className="section-gap" wrap><Tag>{dataset.row_count} 个观测</Tag><Tag>{dataset.column_count} 个字段</Tag><Typography.Text type="secondary">输入 ID：{dataset.id.slice(0, 8)}</Typography.Text></Space>}
        {operation ? <><Typography.Paragraph type="secondary">{operation.description}</Typography.Paragraph>
          <Form form={form} layout="vertical" onFinish={submit}><div className="form-grid">{operation.parameters.filter(p => shown(p, operationId, values)).map(parameter => <Form.Item key={parameter.name} name={parameter.name} label={parameter.label} rules={[{ required: true, message: `请填写${parameter.label}` }]}>
            {parameter.type === 'column' ? <Select showSearch optionFilterProp="label" options={optionsFor(parameter)} placeholder="选择适用字段（含口径）" /> : parameter.type === 'select' ? <Select options={parameter.options} /> : <InputNumber min={parameter.min} max={parameter.max} style={{ width: '100%' }} step={parameter.name.includes('confidence') || parameter.name === 'gamma' ? 0.01 : 1} />}
          </Form.Item>)}</div>
            <Space><Button type="primary" icon={<CalculatorOutlined />} htmlType="submit" disabled={!datasetId} loading={busy}>开始试算</Button><Typography.Text type="secondary">修改参数后手动计算；试算不会自动保存。</Typography.Text></Space>
          </Form>
          <Typography.Paragraph type="secondary" className="section-gap">灰色字段表示其类型、单位或符号不适用于当前模型；请先到数据准备确认口径。前端不会自动转换或删除样本。</Typography.Paragraph>
          <TeachingNote operation={operation} />
        </> : <Spin />}
        {error && <Alert className="section-gap" showIcon type="error" title={error} />}
      </Card>
      <Card className="section-gap" title="本次试算" extra={selectedJob && <Tag>{selectedJob.operation} · {selectedJob.id.slice(0, 8)}</Tag>}>
        {!selectedJob ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="配置模型并开始试算，结果将在这里呈现。" /> : <>
          <Typography.Paragraph type="secondary">结果属于数据集 {selectedJob.dataset_id.slice(0, 8)}；对应参数以本次任务为准，修改上方配置不会改变已完成结果。</Typography.Paragraph>
          {(selectedJob.status === 'queued' || selectedJob.status === 'running') && <Space><Spin /><Typography.Text>{selectedJob.status === 'queued' ? '等待计算' : '正在计算'}，你可以切换页面。</Typography.Text></Space>}
          {selectedJob.status === 'failed' && <Alert showIcon type="error" title="计算失败" description={selectedJob.error} />}
          {selectedJob.status === 'cancelled' && <Alert showIcon type="info" title="任务已取消，未保存计算记录。" />}
          {selectedJob.status === 'completed' && selectedJob.result && <>
            <Space className="table-actions" wrap><Button type="primary" icon={<SaveOutlined />} disabled={!!selectedJob.record_id} onClick={() => { setSaveName(`${catalog?.operations.find(o => o.id === selectedJob.operation)?.name ?? selectedJob.operation} · ${new Date().toLocaleString('zh-CN')}`); setSaveOpen(true); }}>{selectedJob.record_id ? '已保存' : '保存计算记录'}</Button><Button icon={<DownloadOutlined />} onClick={exportConfig}>导出配置 JSON</Button></Space>
            <ResultView result={selectedJob.result} />
          </>}
        </>}
      </Card>
    </>}
    <Modal title="保存计算记录" open={saveOpen} onCancel={() => setSaveOpen(false)} onOk={() => void save()} confirmLoading={busy} okButtonProps={{ disabled: !saveName.trim() }}><Typography.Paragraph type="secondary">保存本次任务的输入版本、模型参数、结果及图表，不改变已有记录。</Typography.Paragraph><Input aria-label="计算记录名称" value={saveName} onChange={e => setSaveName(e.target.value)} maxLength={128} /></Modal>
  </>;
}

function TeachingNote({ operation }: { operation: Operation }) {
  return <Collapse className="section-gap" items={[{ key: 'teaching', label: <Space><span>公式与教材说明</span><Tag>pp. {operation.pages}</Tag></Space>, children: <>
    <pre className="formula">{operation.formula}</pre>
    <Typography.Paragraph>{operation.description}</Typography.Paragraph>
    {Array.isArray(operation.assumptions) ? <ul className="compact-list">{operation.assumptions.map((item, i) => <li key={i}>{item}</li>)}</ul> : <Typography.Paragraph>{operation.assumptions}</Typography.Paragraph>}
    <Typography.Paragraph type="secondary">收益率参数法结果是损失比例。VaR / ES 置信水平与估计误差的区间置信水平为独立参数。</Typography.Paragraph>
  </> }]} />;
}

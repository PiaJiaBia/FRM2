import { useCallback, useEffect, useState } from 'react';
import { App, Alert, Button, Card, Checkbox, Collapse, Drawer, Empty, Input, Modal, Select, Space, Table, Tag, Tabs, Typography, Upload } from 'antd';
import { ArrowRightOutlined, DatabaseOutlined, DownloadOutlined, InboxOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { api, download, patch, post } from '../api';
import type { Dataset, Example, Metadata, Page, Preview } from '../types';
import { DataTable } from '../components/ResultView';
import { completeMetadata, FieldEditor } from '../components/FieldEditor';
import { PrepareForm, type PrepareOptions } from '../components/PrepareForm';

interface Props { onCalculate: (dataset: Dataset) => void; onChanged: () => void; initialDataset?: { id: string; key: number } }
export default function Datasets({ onCalculate, onChanged, initialDataset }: Props) {
  const { message, modal } = App.useApp();
  const [items, setItems] = useState<Dataset[]>([]); const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1); const [query, setQuery] = useState(''); const [archived, setArchived] = useState(false); const [loading, setLoading] = useState(false);
  const [examples, setExamples] = useState<Example[]>([]); const [importOpen, setImportOpen] = useState(false);
  const [selectedExample, setSelectedExample] = useState<string>(); const [file, setFile] = useState<File>();
  const [sheet, setSheet] = useState<string>(); const [preview, setPreview] = useState<Preview>(); const [detail, setDetail] = useState<Dataset>();
  const [metadata, setMetadata] = useState<Metadata>({}); const [name, setName] = useState(''); const [description, setDescription] = useState('');
  const [confirmed, setConfirmed] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [detailPage, setDetailPage] = useState(1);
  const refresh = useCallback(async () => {
    setLoading(true);
    try { const result = await api<Page<Dataset>>(`/datasets?q=${encodeURIComponent(query)}&archived=${archived}&offset=${(page - 1) * 20}&limit=20`); setItems(result.items); setTotal(result.total); }
    catch (e) { message.error((e as Error).message); } finally { setLoading(false); }
  }, [query, archived, page, message]);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { api<{ items: Example[] }>('/examples').then(result => setExamples(result.items)).catch(() => {}); }, []);
  const openDetail = useCallback(async (id: string, nextPage = 1) => {
    setBusy(true); setError('');
    try { const result = await api<Dataset>(`/datasets/${id}?offset=${(nextPage - 1) * 100}&limit=100`); setDetail(result); setMetadata(completeMetadata(result.columns ?? [], result.metadata)); setDetailPage(nextPage); }
    catch (e) { message.error((e as Error).message); } finally { setBusy(false); }
  }, [message]);
  useEffect(() => { if (initialDataset) void openDetail(initialDataset.id); }, [initialDataset, openDetail]);
  const acceptPreview = (result: Preview) => { setPreview(result); setMetadata(completeMetadata(result.columns, result.metadata)); setConfirmed(false); setImportOpen(true); setError(''); };
  const doPreview = async (kind: 'example' | 'upload') => {
    setBusy(true); setError('');
    try {
      if (kind === 'example') { const result = await post<Preview>('/previews/example', { example_id: selectedExample }); acceptPreview(result); setName(examples.find(item => item.id === selectedExample)?.name ?? '教材示例'); }
      else if (file) { const body = new FormData(); body.append('file', file); if (sheet) body.append('sheet', sheet); acceptPreview(await api<Preview>('/previews/upload', { method: 'POST', body })); setName(file.name.replace(/\.[^.]+$/, '')); }
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const prepare = async (options: PrepareOptions, source: 'preview' | 'dataset') => {
    setBusy(true); setError('');
    try {
      const result = await post<Preview>(`/${source === 'preview' ? 'previews' : 'datasets'}/${source === 'preview' ? preview!.id : detail!.id}/prepare`, { options, metadata });
      if (source === 'dataset') { setName(`${detail!.name} · 派生`); setDetail(undefined); }
      acceptPreview(result);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const save = async () => {
    setBusy(true); setError('');
    try {
      const dataset = await post<Dataset>(`/previews/${preview!.id}/save`, { name: name.trim(), description, metadata });
      setImportOpen(false); setPreview(undefined); setFile(undefined); setSheet(undefined); setDescription('');
      message.success('已保存为新数据集'); onChanged(); void refresh(); await openDetail(dataset.id);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const rename = (dataset: Dataset) => { let next = dataset.name; modal.confirm({ title: '重命名数据集', content: <Input defaultValue={next} onChange={e => { next = e.target.value; }} />, onOk: async () => { if (!next.trim()) throw new Error('名称不能为空'); await patch(`/datasets/${dataset.id}`, { name: next.trim() }); await refresh(); onChanged(); } }); };
  const archive = async (dataset: Dataset) => {
    try { await patch(`/datasets/${dataset.id}`, { archived: !dataset.archived }); message.success(dataset.archived ? '已恢复' : '已归档，历史记录仍可引用'); void refresh(); onChanged(); }
    catch (e) { message.error((e as Error).message); }
  };
  return <>
    <div className="page-heading"><div><div className="eyebrow">DATA LIBRARY</div><Typography.Title level={2}>数据集</Typography.Title><Typography.Text type="secondary">保留原始样本，让每一次计算都有清晰的数据来源。</Typography.Text></div><Button type="primary" size="large" icon={<PlusOutlined />} onClick={() => { setImportOpen(true); setError(''); }}>导入 / 教材示例</Button></div>
    <Card><div className="toolbar"><Input.Search placeholder="搜索数据集名称" allowClear onSearch={value => { setQuery(value); setPage(1); }} style={{ width: 320 }} /><Space><Checkbox checked={archived} onChange={e => { setArchived(e.target.checked); setPage(1); }}>已归档</Checkbox><Button icon={<ReloadOutlined />} onClick={() => void refresh()}>刷新</Button></Space></div>
      <Table loading={loading} rowKey="id" dataSource={items} locale={{ emptyText: <Empty description="暂无数据集。先载入教材示例，或上传自己的数据。" /> }} pagination={{ current: page, pageSize: 20, total, showSizeChanger: false, onChange: setPage }} columns={[
        { title: '数据集', dataIndex: 'name', render: (value, row) => <Button type="link" onClick={() => void openDetail(row.id)}><DatabaseOutlined />{value}</Button> },
        { title: '规模', render: (_, row) => `${row.row_count.toLocaleString()} 行 / ${row.column_count} 列` },
        { title: '创建时间', dataIndex: 'created_at', render: value => value ? new Date(value).toLocaleString('zh-CN') : '—' },
        { title: '操作', render: (_, row) => <Space><Button size="small" onClick={() => onCalculate(row)}>用于计算</Button><Button size="small" type="text" onClick={() => rename(row)}>命名</Button><Button size="small" type="text" onClick={() => void archive(row)}>{row.archived ? '恢复' : '归档'}</Button></Space> },
      ]} />
    </Card>
    <Modal title="导入数据与确认口径" width={1100} open={importOpen} footer={null} onCancel={() => setImportOpen(false)} destroyOnHidden={false}>
      <Alert showIcon type="info" title="预览不写入数据库。确认字段与单位后，再保存新数据集。" className="section-gap" />
      <Tabs items={[
        { key: 'example', label: '教材 / 演示示例', children: <><Space wrap><Select aria-label="选择教材示例" placeholder="选择示例" value={selectedExample} onChange={setSelectedExample} style={{ width: 460 }} options={examples.map(item => ({ value: item.id, label: item.name }))} /><Button loading={busy} disabled={!selectedExample} onClick={() => void doPreview('example')}>载入示例</Button></Space><Typography.Paragraph type="secondary">{examples.find(item => item.id === selectedExample)?.description}</Typography.Paragraph></> },
        { key: 'upload', label: '上传 CSV / Excel', children: <Space direction="vertical" style={{ width: '100%' }}><Upload.Dragger accept=".csv,.xlsx,.xls" maxCount={1} fileList={file ? [{ uid: 'upload', name: file.name, status: 'done' }] : []} beforeUpload={next => { setFile(next); setSheet(undefined); setPreview(undefined); return false; }} onRemove={() => { setFile(undefined); setPreview(undefined); }}><p className="ant-upload-drag-icon"><InboxOutlined /></p><p>拖入数据文件，或点击选择</p><p className="ant-upload-hint">CSV、XLSX、XLS；上传后可选择工作表并预览</p></Upload.Dragger><Space>{!!preview?.sheets?.length && <Select aria-label="Excel工作表" placeholder="选择工作表" value={sheet} onChange={setSheet} options={preview.sheets.map(value => ({ value, label: value }))} style={{ width: 240 }} />}<Button disabled={!file} loading={busy} onClick={() => void doPreview('upload')}>上传并预览</Button></Space></Space> },
      ]} />
      {error && <Alert className="section-gap" showIcon type="error" title={error} />}
      {preview && <div className="result-stack"><div className="preview-label"><Tag color="cyan">预览</Tag><strong>{preview.row_count.toLocaleString()} 行 · {preview.columns.length} 列</strong><Typography.Text type="secondary">最多展示前 100 行</Typography.Text></div>
        {preview.changes && <Alert type="success" title={`处理前 ${preview.changes.before_rows} 行 → 处理后 ${preview.changes.after_rows} 行；删除 ${preview.changes.dropped_rows} 行`} description={`新增列：${preview.changes.added_columns.join('、') || '无'}`} />}
        <DataTable columns={preview.columns} rows={preview.rows} />
        <FieldEditor columns={preview.columns} value={metadata} onChange={value => { setMetadata(value); setConfirmed(false); }} />
        <Collapse items={[{ key: 'prepare', label: '数据准备：重命名、排序、转换与收益率计算', children: <PrepareForm key={preview.id} columns={preview.columns} busy={busy} onPrepare={options => void prepare(options, 'preview')} /> }]} />
        <div className="form-grid"><div><Typography.Text>数据集名称</Typography.Text><Input aria-label="数据集名称" value={name} onChange={e => setName(e.target.value)} maxLength={128} /></div><div><Typography.Text>说明（可选）</Typography.Text><Input value={description} onChange={e => setDescription(e.target.value)} /></div></div>
        <Space wrap><Checkbox checked={confirmed} onChange={e => setConfirmed(e.target.checked)}>我已确认字段含义、单位及正负号</Checkbox><Button type="primary" disabled={!confirmed || !name.trim()} loading={busy} onClick={() => void save()}>保存新数据集</Button></Space>
      </div>}
    </Modal>
    <Drawer title={detail?.name ?? '数据集详情'} size="large" width={1080} open={!!detail} onClose={() => setDetail(undefined)} extra={<Space><Button icon={<DownloadOutlined />} onClick={() => detail && void download(`/datasets/${detail.id}/export`, `${detail.name}.csv`).catch(e => message.error(e.message))}>CSV</Button><Button type="primary" icon={<ArrowRightOutlined />} onClick={() => { if (detail) onCalculate(detail); setDetail(undefined); }}>用于计算</Button></Space>}>
      {detail && <div className="result-stack"><Space><Tag>{detail.row_count} 行</Tag><Tag>{detail.column_count} 列</Tag><Typography.Text type="secondary" copyable>{detail.id}</Typography.Text></Space><Typography.Paragraph>{detail.description}</Typography.Paragraph>
        <DataTable columns={detail.columns ?? []} rows={detail.rows ?? []} />
        {detail.row_count > 100 && <Space><Button disabled={detailPage === 1} onClick={() => void openDetail(detail.id, detailPage - 1)}>上一批</Button><span>第 {detailPage} 批，每批 100 行</span><Button disabled={detailPage * 100 >= detail.row_count} onClick={() => void openDetail(detail.id, detailPage + 1)}>下一批</Button></Space>}
        <Collapse items={[{ key: 'metadata', label: '字段口径与数据血缘', children: <><FieldEditor columns={detail.columns ?? []} value={metadata} onChange={setMetadata} /><Typography.Paragraph type="secondary">修改口径仅用于下一次派生，原始快照不变。</Typography.Paragraph><pre className="metadata">{JSON.stringify(detail.metadata, null, 2)}</pre></> }, { key: 'prepare', label: '生成派生数据集', children: <PrepareForm key={detail.id} columns={detail.columns ?? []} busy={busy} onPrepare={options => void prepare(options, 'dataset')} /> }]} />
        {error && <Alert type="error" title={error} showIcon />}
      </div>}
    </Drawer>
  </>;
}

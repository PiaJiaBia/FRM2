import { useCallback, useEffect, useState } from 'react';
import { App, Alert, Button, Card, Checkbox, Drawer, Empty, Input, Space, Table, Tag, Typography } from 'antd';
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import { api, download, patch } from '../api';
import type { CalculationRequest, Catalog, Page, SavedRecord } from '../types';
import { ResultView } from '../components/ResultView';
import { recordRequest } from '../recordRequest';

export default function Records({ revision, catalog, onReopen }: { revision: number; catalog?: Catalog; onReopen: (request: CalculationRequest) => void }) {
  const { message, modal } = App.useApp();
  const [items, setItems] = useState<SavedRecord[]>([]); const [total, setTotal] = useState(0); const [page, setPage] = useState(1);
  const [query, setQuery] = useState(''); const [archived, setArchived] = useState(false); const [loading, setLoading] = useState(false); const [record, setRecord] = useState<SavedRecord>();
  const reopenRequest = recordRequest(record, catalog);
  const refresh = useCallback(async () => {
    setLoading(true);
    try { const value = await api<Page<SavedRecord>>(`/records?q=${encodeURIComponent(query)}&archived=${archived}&offset=${(page - 1) * 20}&limit=20`); setItems(value.items); setTotal(value.total); }
    catch (e) { message.error((e as Error).message); } finally { setLoading(false); }
  }, [query, archived, page, message]);
  useEffect(() => { void refresh(); }, [refresh, revision]);
  const open = async (id: string) => { try { setRecord(await api<SavedRecord>(`/records/${id}`)); } catch (e) { message.error((e as Error).message); } };
  const rename = (row: SavedRecord) => { let name = row.name; modal.confirm({ title: '重命名计算记录', content: <Input defaultValue={name} onChange={e => { name = e.target.value; }} />, onOk: async () => { if (!name.trim()) throw new Error('名称不能为空'); await patch(`/records/${row.id}`, { name: name.trim() }); await refresh(); } }); };
  const archive = async (row: SavedRecord) => { try { await patch(`/records/${row.id}`, { archived: !row.archived }); message.success(row.archived ? '已恢复' : '已归档'); void refresh(); } catch (e) { message.error((e as Error).message); } };
  const exportRecord = (format: 'csv' | 'json') => { if (record) void download(`/records/${record.id}/export?format=${format}`, `${record.name}.${format}`).catch(e => message.error(e.message)); };
  return <>
    <div className="page-heading"><div><div className="eyebrow">ANALYSIS HISTORY</div><Typography.Title level={2}>计算记录</Typography.Title><Typography.Text type="secondary">冻结当时的参数与结果，随时回来继续分析。</Typography.Text></div></div>
    <Card><div className="toolbar"><Input.Search placeholder="搜索计算记录" allowClear onSearch={value => { setQuery(value); setPage(1); }} style={{ width: 320 }} /><Space><Checkbox checked={archived} onChange={e => { setArchived(e.target.checked); setPage(1); }}>已归档</Checkbox><Button icon={<ReloadOutlined />} onClick={() => void refresh()}>刷新</Button></Space></div>
      <Table rowKey="id" loading={loading} dataSource={items} locale={{ emptyText: <Empty description="暂无保存记录。完成试算后，点击“保存计算记录”。" /> }} pagination={{ current: page, pageSize: 20, total, showSizeChanger: false, onChange: setPage }} columns={[
        { title: '分析名称', dataIndex: 'name', render: (name, row) => <Button type="link" onClick={() => void open(row.id)}>{name}</Button> },
        { title: '操作', dataIndex: 'operation', render: value => <Tag>{value}</Tag> },
        { title: '保存时间', dataIndex: 'created_at', render: value => value ? new Date(value).toLocaleString('zh-CN') : '—' },
        { title: '操作', render: (_, row) => <Space><Button size="small" onClick={() => void open(row.id)}>查看</Button><Button size="small" type="text" onClick={() => rename(row)}>命名</Button><Button size="small" type="text" onClick={() => void archive(row)}>{row.archived ? '恢复' : '归档'}</Button></Space> },
      ]} />
    </Card>
    <Drawer open={!!record} onClose={() => setRecord(undefined)} title={record?.name} width={1120} extra={<Space><Button icon={<DownloadOutlined />} onClick={() => exportRecord('csv')}>CSV</Button><Button icon={<DownloadOutlined />} onClick={() => exportRecord('json')}>配置 JSON</Button><Button type="primary" disabled={!reopenRequest} onClick={() => { if (reopenRequest) { onReopen(reopenRequest); setRecord(undefined); } }}>修改参数后另存</Button></Space>}>
      {record && <div className="result-stack"><Alert type="info" title="保存时的结果快照" description="这里展示已保存结果，不自动重新计算。修改参数将创建新的任务和记录。" />{catalog && !reopenRequest && <Alert type="warning" title="此记录仅支持查看和导出" description="记录来自旧格式、操作尚未接入或参数结构不完整。请到章节计算选择数据集与可用模型重新配置。" />}<Typography.Text type="secondary" copyable>输入数据集：{record.dataset_id}</Typography.Text><pre className="metadata">{JSON.stringify(record.request, null, 2)}</pre>{record.result ? <ResultView result={record.result} /> : <Empty description="这条旧记录没有工作台格式的图表结果，可导出查看。" />}</div>}
    </Drawer>
  </>;
}

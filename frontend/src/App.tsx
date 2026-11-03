import { useCallback, useEffect, useState } from 'react';
import { Alert, App as AntApp, Badge, Button, Drawer, Layout, Menu, Progress, Space, Tag, Typography } from 'antd';
import { BookOutlined, CheckCircleOutlined, DatabaseOutlined, ExperimentOutlined, HistoryOutlined, LoadingOutlined, UnorderedListOutlined } from '@ant-design/icons';
import { api, post } from './api';
import type { CalculationRequest, Catalog, Dataset, Job } from './types';
import Calculate from './pages/Calculate';
import Datasets from './pages/Datasets';
import Records from './pages/Records';

type PageName = 'datasets' | 'calculate' | 'records';
const statusText: Record<Job['status'], string> = { queued: '等待中', running: '计算中', completed: '已完成', failed: '失败', cancelled: '已取消' };
const statusColor: Record<Job['status'], string> = { queued: 'default', running: 'processing', completed: 'success', failed: 'error', cancelled: 'default' };
const pageFromHash = (): PageName => ['datasets', 'calculate', 'records'].includes(location.hash.slice(1)) ? location.hash.slice(1) as PageName : 'calculate';

export default function App() {
  const { message } = AntApp.useApp();
  const [page, setPage] = useState<PageName>(pageFromHash);
  const [catalog, setCatalog] = useState<Catalog>(); const [connectionError, setConnectionError] = useState('');
  const [jobs, setJobs] = useState<Job[]>([]); const [selectedJobId, setSelectedJobId] = useState<string>();
  const [tasksOpen, setTasksOpen] = useState(false); const [revision, setRevision] = useState(0);
  const [selectedDataset, setSelectedDataset] = useState<Dataset>(); const [prepareDataset, setPrepareDataset] = useState<{ id: string; key: number }>();
  const [reopen, setReopen] = useState<{ request: CalculationRequest; key: number }>();
  const navigate = (next: PageName) => { setPage(next); location.hash = next; };
  useEffect(() => { const listener = () => setPage(pageFromHash()); window.addEventListener('hashchange', listener); return () => window.removeEventListener('hashchange', listener); }, []);
  const connect = useCallback(async () => {
    try { const result = await api<Catalog>('/catalog'); setCatalog(result); await api('/health'); setConnectionError(''); }
    catch (e) { setConnectionError((e as Error).message); }
  }, []);
  useEffect(() => { void connect(); }, [connect]);
  useEffect(() => {
    let active = true; let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try { const result = await api<{ items: Job[] }>('/jobs'); if (active) setJobs(result.items); }
      catch { /* The connection banner and per-request errors report availability. */ }
      finally { if (active) timer = setTimeout(() => void poll(), 1800); }
    }
    void poll(); return () => { active = false; clearTimeout(timer); };
  }, []);
  const acceptJob = (job: Job) => { setJobs(current => [job, ...current.filter(item => item.id !== job.id)]); setSelectedJobId(job.id); };
  const cancel = async (id: string) => { try { const job = await post<Job>(`/jobs/${id}/cancel`, {}); setJobs(current => current.map(item => item.id === id ? job : item)); } catch (e) { message.error((e as Error).message); } };
  const running = jobs.filter(job => job.status === 'queued' || job.status === 'running').length;
  const selectedJob = jobs.find(job => job.id === selectedJobId);
  return <Layout className="app-shell">
    <Layout.Sider width={232} theme="light" className="sidebar">
      <div className="brand"><div className="brand-icon"><ExperimentOutlined /></div><div><strong>FRM LAB</strong><span>市场风险工作台</span></div></div>
      <div className="sidebar-label">WORKSPACE</div>
      <Menu mode="inline" selectedKeys={[page]} onClick={({ key }) => navigate(key as PageName)} items={[
        { key: 'datasets', icon: <DatabaseOutlined />, label: '数据集' },
        { key: 'calculate', icon: <BookOutlined />, label: '章节计算' },
        { key: 'records', icon: <HistoryOutlined />, label: '计算记录' },
      ]} />
      <div className="sidebar-note"><div className="note-rule" /><Typography.Text strong>从教材到实证</Typography.Text><p>18 章计算引擎<br />第 1 章可视化工作区</p><Tag bordered={false} color="green">个人工作台</Tag></div>
      <div className="sidebar-footer">FRM PART II<br /><span>Market Risk Measurement</span></div>
    </Layout.Sider>
    <Layout className="main-layout"><Layout.Header className="topbar"><Space><span className="connection-dot" data-connected={!connectionError} /><Typography.Text type="secondary">{connectionError ? '服务连接待恢复' : '本机工作台'}</Typography.Text><span className="header-divider" /><Typography.Text>Market Risk</Typography.Text></Space><Badge count={running} size="small"><Button icon={<UnorderedListOutlined />} onClick={() => setTasksOpen(true)}>计算任务</Button></Badge></Layout.Header>
      <Layout.Content className="content">
        {connectionError && <Alert className="section-gap" showIcon type="error" title="无法连接计算服务" description={connectionError} action={<Button onClick={() => void connect()}>重试连接</Button>} />}
        <section hidden={page !== 'datasets'}><Datasets initialDataset={prepareDataset} onCalculate={dataset => { setSelectedDataset(dataset); navigate('calculate'); }} onChanged={() => setRevision(value => value + 1)} /></section>
        <section hidden={page !== 'calculate'}><Calculate catalog={catalog} revision={revision} selectedDataset={selectedDataset} selectedJob={selectedJob} reopen={reopen} onJob={acceptJob} onSaved={() => setRevision(value => value + 1)} onPrepare={id => { setPrepareDataset(id ? { id, key: Date.now() } : undefined); navigate('datasets'); }} /></section>
        <section hidden={page !== 'records'}><Records revision={revision} catalog={catalog} onReopen={request => { setReopen({ request, key: Date.now() }); setSelectedJobId(undefined); navigate('calculate'); }} /></section>
        <footer className="content-footer">数据口径显式确认 · 公式由 Python 计算引擎执行 · 结果按需保存</footer>
      </Layout.Content>
    </Layout>
    <Drawer title="计算任务" open={tasksOpen} onClose={() => setTasksOpen(false)} width={470}>
      <Typography.Paragraph type="secondary">任务在页面切换后继续运行。本机服务重启后，不恢复未保存的试算。</Typography.Paragraph>
      {!jobs.length && <Alert type="info" title="暂无任务。配置一个模型并开始试算。" />}
      {jobs.map(job => <div className="job-card" key={job.id}><div className="job-title"><Space>{job.status === 'running' ? <LoadingOutlined /> : job.status === 'completed' ? <CheckCircleOutlined /> : <ExperimentOutlined />}<strong>{catalog?.operations.find(op => op.id === job.operation)?.name ?? job.operation}</strong></Space><Tag color={statusColor[job.status]}>{statusText[job.status]}</Tag></div>
        <Typography.Paragraph type="secondary">{job.id.slice(0, 8)} · 数据 {job.dataset_id.slice(0, 8)}</Typography.Paragraph>
        {typeof job.progress === 'number' && <Progress percent={job.progress} size="small" />}
        {job.error && <Alert type="error" title={job.error} />}
        <Space><Button size="small" onClick={() => { setSelectedJobId(job.id); navigate('calculate'); setTasksOpen(false); }}>查看任务</Button>{(job.status === 'running' || job.status === 'queued') && <Button size="small" danger onClick={() => void cancel(job.id)}>取消任务</Button>}{job.record_id && <Tag>已保存</Tag>}</Space>
      </div>)}
    </Drawer>
  </Layout>;
}

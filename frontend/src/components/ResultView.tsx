import { useEffect, useRef } from 'react';
import { Alert, Button, Card, Empty, Space, Statistic, Table, Tabs } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import * as echarts from 'echarts/core';
import { BarChart, LineChart, ScatterChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, MarkAreaComponent, DataZoomComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { ChartData, Result, Row } from '../types';
import { csv, display, downloadBlob } from '../api';

echarts.use([BarChart, LineChart, ScatterChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, MarkAreaComponent, DataZoomComponent, CanvasRenderer]);

function Chart({ data }: { data: ChartData }) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.EChartsType | null>(null);
  useEffect(() => {
    if (!container.current) return;
    const chart = echarts.init(container.current); instance.current = chart;
    const categorical = data.series.some(s => s.data.some(point => typeof point[0] === 'string'));
    chart.setOption({
      color: ['#176b62', '#cf8b35', '#6575c4', '#ce6574'], animation: false,
      tooltip: { trigger: 'axis', confine: true }, legend: { top: 0 },
      grid: { left: 65, right: 30, top: 48, bottom: 65, containLabel: true },
      xAxis: { type: categorical ? 'category' : 'value', name: data.x_label, nameLocation: 'middle', nameGap: 35, axisLabel: { hideOverlap: true } },
      yAxis: { type: 'value', name: data.y_label, splitLine: { lineStyle: { color: '#edf0f2' } } },
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 14, bottom: 5 }],
      series: data.series.map((series, i) => ({ ...series, showSymbol: series.type === 'scatter', symbolSize: 5, connectNulls: false,
        data: series.data.map(([x, y]) => [x, typeof y === 'number' && Number.isFinite(y) ? y : null]),
        ...(i === 0 ? {
          markLine: { symbol: 'none', label: { formatter: '{b}' }, data: (data.markers ?? []).map(m => ({ name: m.name, xAxis: m.value })) },
          markArea: { itemStyle: { color: 'rgba(207,139,53,.12)' }, data: (data.areas ?? []).map(a => [{ xAxis: a.from }, { xAxis: a.to }]) },
        } : {}),
      })),
    });
    const observer = new ResizeObserver(() => chart.resize()); observer.observe(container.current);
    return () => { observer.disconnect(); chart.dispose(); instance.current = null; };
  }, [data]);
  const exportPng = () => {
    if (!instance.current) return;
    const anchor = document.createElement('a'); anchor.href = instance.current.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' });
    anchor.download = `${data.title}.png`; anchor.click();
  };
  return <Card size="small" title={data.title} extra={<Button type="text" icon={<DownloadOutlined />} onClick={exportPng}>PNG</Button>}>
    <div ref={container} className="chart" role="img" aria-label={data.title} />
  </Card>;
}

export function DataTable({ columns, rows, loading = false }: { columns: string[]; rows: Row[]; loading?: boolean }) {
  return <Table size="small" loading={loading} rowKey={(_, index) => String(index)} dataSource={rows}
    columns={columns.map(name => ({ title: name, dataIndex: name, key: name, render: display, ellipsis: true, width: 155 }))}
    scroll={{ x: Math.max(600, columns.length * 155) }} pagination={{ pageSize: 10, showSizeChanger: true, showTotal: total => `${total} 行预览` }} />;
}

export function ResultView({ result }: { result: Result }) {
  if (!result?.metrics || !Array.isArray(result.charts) || !Array.isArray(result.tables)) return <Alert type="info" title="历史格式结果" description="这条记录由早期计算器保存，未包含工作台图表结构。可导出配置，或选择数据集重新计算。" />;
  return <div className="result-stack">
    {!!result.notes?.length && <Alert type="info" showIcon title="计算说明" description={<ul className="compact-list">{result.notes.map((note, i) => <li key={i}>{note}</li>)}</ul>} />}
    <div className="metric-grid">{result.metrics.map((metric, i) => <Card size="small" key={i}><Statistic title={metric.name} value={display(metric.value)} suffix={metric.unit ? <small>{metric.unit}</small> : undefined} /></Card>)}</div>
    {!!result.charts.length && <div className="chart-grid">{result.charts.map((chart, i) => <Chart key={i} data={chart} />)}</div>}
    {!!result.tables.length && <Card title="结果明细" size="small"><Tabs items={result.tables.map((table, i) => ({ key: String(i), label: table.name, children: <>
      <Space className="table-actions"><Button icon={<DownloadOutlined />} onClick={() => downloadBlob(new Blob([csv(table)], { type: 'text/csv;charset=utf-8' }), `${table.name}.csv`)}>导出 CSV</Button></Space>
      <DataTable columns={table.columns} rows={table.rows} />
    </> }))} /></Card>}
    {!result.metrics.length && !result.charts.length && !result.tables.length && <Empty description="本次计算未产生结果" />}
  </div>;
}

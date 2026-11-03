import { expect, test, type Page } from '@playwright/test';
import type { Dataset, Job, SavedRecord, Result, Catalog } from '../src/types';

const catalog: Catalog = {
  chapters: Array.from({ length: 18 }, (_, index) => ({ number: index + 1, title: index === 0 ? 'Estimating Market Risk Measures' : `Chapter ${index + 1}`, pages: '2–16', available: index === 0 })),
  operations: [{ id: 'var', name: 'VaR', workspace: 'var', description: '损失分位数与模型比较', formula: 'VaRα = Qloss(α)', pages: '3–7', assumptions: ['收益率使用小数，盈利为正'], parameters: [
    { name: 'model', label: '模型', type: 'select', default: 'normal', options: [{ value: 'normal', label: '正态' }, { value: 'historical', label: '历史模拟' }, { value: 'lognormal', label: '对数正态' }, { value: 'compare', label: '三种模型比较' }] },
    { name: 'target_column', label: '样本列', type: 'column' },
    { name: 'confidence_level', label: '风险置信水平', type: 'number', default: 0.95, min: 0.001, max: 0.999 },
  ] }],
};
const frame: Dataset = { id: 'dataset-1', name: '教材例1.3', row_count: 3, column_count: 1, archived: false, columns: ['arithmetic_return'], rows: [{ arithmetic_return: -0.15 }, { arithmetic_return: 0.1 }, { arithmetic_return: 0.35 }], metadata: { fields: { arithmetic_return: { kind: 'arithmetic_return', unit: 'decimal', sign: 'profit' } } } };
const result: Result = { metrics: [{ name: 'VaR', value: 0.311213, unit: '损失比例' }], tables: [{ name: '模型结果', columns: ['model', 'value'], rows: [{ model: 'normal', value: 0.311213 }] }], charts: [{ title: '损失分布', x_label: '损失比例', y_label: '频数', series: [{ name: '频数', type: 'bar', data: [[-0.35, 1], [-0.1, 1], [0.15, 1]] }], markers: [{ name: 'VaR', value: 0.311213 }] }], notes: ['教材均值0.1、样本标准差0.25'] };

async function fixtures(page: Page, options: { queued?: boolean; empty?: boolean } = {}) {
  page.on('pageerror', error => console.error('BROWSER ERROR', error.message));
  let datasets: Dataset[] = options.empty ? [] : [structuredClone(frame)];
  const jobs: Job[] = []; const records: SavedRecord[] = []; const requests: unknown[] = [];
  await page.route('**/api/**', async route => {
    const request = route.request(); const url = new URL(request.url()); const path = url.pathname.replace('/api', ''); const method = request.method();
    const body = request.headers()['content-type']?.includes('application/json') && request.postData() ? request.postDataJSON() : {};
    const respond = (value: unknown) => route.fulfill({ json: value });
    if (path === '/health') return respond({ status: 'ok', database: 'FRM' });
    if (path === '/catalog') return respond(catalog);
    if (path === '/examples') return respond({ items: [{ id: 'normal', name: '教材例1.3：正态收益率', description: '构造样本，不是教材原始观测' }] });
    if (path === '/previews/example' || path === '/previews/upload') return respond({ id: 'preview-1', columns: frame.columns, rows: frame.rows, row_count: 3, metadata: frame.metadata, sheets: path.endsWith('upload') ? ['Sheet1', 'Sheet2'] : [] });
    if (path.endsWith('/prepare')) return respond({ id: 'preview-2', columns: frame.columns, rows: frame.rows, row_count: 3, metadata: body.metadata ?? frame.metadata, changes: { before_rows: 3, after_rows: 3, dropped_rows: 0, added_columns: [] } });
    if (path.startsWith('/previews/') && path.endsWith('/save')) { const saved = { ...structuredClone(frame), name: body.name, metadata: body.metadata }; datasets.push(saved); return respond(saved); }
    if (path === '/datasets') { const filtered = datasets.filter(d => d.archived === (url.searchParams.get('archived') === 'true')); return respond({ items: filtered, total: filtered.length }); }
    if (path === '/datasets/dataset-1' && method === 'PATCH') { datasets = datasets.map(d => ({ ...d, ...body })); return respond(datasets[0]); }
    if (path === '/datasets/dataset-1') return respond(datasets[0] ?? frame);
    if (path.endsWith('/export')) return route.fulfill({ body: url.searchParams.get('format') === 'json' ? JSON.stringify(records[0]?.request) : 'model,value\nnormal,0.311213', contentType: 'text/plain' });
    if (path === '/jobs' && method === 'POST') { requests.push(body); const job: Job = { ...body, id: `job-${jobs.length + 1}`, status: options.queued ? 'running' : 'completed', ...(options.queued ? {} : { result }) }; jobs.push(job); return respond(job); }
    if (path === '/jobs') return respond({ items: jobs });
    if (path.endsWith('/cancel')) { const job = jobs.find(j => path.includes(j.id))!; job.status = 'cancelled'; return respond(job); }
    if (path.endsWith('/save')) { const job = jobs.find(j => path.includes(j.id))!; const record: SavedRecord = { id: 'record-1', name: body.name, dataset_id: job.dataset_id, operation: job.operation, archived: false, request: { dataset_id: job.dataset_id, operation: job.operation, parameters: job.parameters }, result: job.result }; records.push(record); job.record_id = record.id; return respond(record); }
    if (path === '/records') { const filtered = records.filter(r => r.archived === (url.searchParams.get('archived') === 'true')); return respond({ items: filtered, total: filtered.length }); }
    if (path === '/records/record-1' && method === 'PATCH') { Object.assign(records[0], body); return respond(records[0]); }
    if (path === '/records/record-1') return respond(records[0]);
    return route.fulfill({ status: 404, json: { detail: `Fixture missing ${method} ${path}` } });
  });
  return { requests, jobs, records };
}

async function choose(page: Page, label: string, option: string) {
  await page.getByRole('combobox', { name: new RegExp(label + '$') }).click();
  await page.locator('.ant-select-dropdown:visible').getByText(option, { exact: true }).click();
}

test('教材示例 → 确认 → 计算 → 保存 → 重开 → 导出', async ({ page }) => {
  const state = await fixtures(page, { empty: true }); await page.goto('/');
  await page.getByRole('menuitem', { name: /数据集$/ }).click();
  await page.getByRole('button', { name: '导入 / 教材示例' }).click();
  await choose(page, '选择教材示例', '教材例1.3：正态收益率');
  await page.getByRole('button', { name: '载入示例' }).click();
  await expect(page.getByRole('button', { name: '保存新数据集' })).toBeDisabled();
  await page.getByRole('checkbox', { name: '我已确认字段含义、单位及正负号' }).check();
  await page.getByRole('button', { name: '保存新数据集' }).click();
  await page.getByRole('dialog').getByRole('button', { name: '用于计算' }).click();
  await choose(page, '样本列', 'arithmetic_return · arithmetic_return / decimal');
  await page.getByRole('button', { name: '开始试算' }).click();
  await expect(page.getByText('0.311213').first()).toBeVisible();
  await page.screenshot({ path: test.info().outputPath('calculation.png'), fullPage: true });
  expect(state.requests).toEqual([{ dataset_id: 'dataset-1', operation: 'var', parameters: { model: 'normal', target_column: 'arithmetic_return', confidence_level: 0.95 } }]);
  expect(state.records).toHaveLength(0);
  await page.getByRole('button', { name: '保存计算记录' }).click();
  await page.getByRole('textbox', { name: '计算记录名称' }).fill('教材验算');
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.getByRole('button', { name: /已保存$/ })).toBeDisabled();
  const png = page.waitForEvent('download'); await page.getByRole('button', { name: /PNG$/ }).click(); expect((await png).suggestedFilename()).toMatch(/\.png$/);
  await page.getByRole('menuitem', { name: /计算记录$/ }).click();
  await page.getByRole('button', { name: '教材验算', exact: true }).click();
  await expect(page.getByText('保存时的结果快照')).toBeVisible();
  const config = page.waitForEvent('download'); await page.getByRole('dialog').getByRole('button', { name: '配置 JSON' }).click(); expect((await config).suggestedFilename()).toBe('教材验算.json');
  await page.getByRole('button', { name: '修改参数后另存' }).click();
  await expect(page.getByRole('spinbutton', { name: '风险置信水平' })).toHaveValue('0.95');
});

test('后台任务跨页面保留，取消后不允许保存；未接入章节明确标识', async ({ page }) => {
  const state = await fixtures(page, { queued: true }); await page.goto('/');
  await choose(page, '计算数据集', '教材例1.3 · 3 行');
  await choose(page, '样本列', 'arithmetic_return · arithmetic_return / decimal');
  await page.getByRole('button', { name: '开始试算' }).click();
  await page.getByRole('menuitem', { name: /数据集$/ }).click();
  await page.getByRole('button', { name: /计算任务$/ }).click();
  await page.getByRole('button', { name: '取消任务' }).click();
  await expect(page.getByText('已取消', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '查看任务' }).click();
  await expect(page.getByText('任务已取消，未保存计算记录。')).toBeVisible();
  await expect(page.getByRole('button', { name: '保存计算记录' })).toHaveCount(0); expect(state.records).toHaveLength(0);
  await choose(page, '章节', '第 2 章 · Chapter 2 · 未接入');
  await expect(page.getByText('第 2 章计算器已存在，网页操作尚未接入。')).toBeVisible();
});

test('上传预览、显式准备与归档', async ({ page }) => {
  await fixtures(page, { empty: true }); await page.goto('/#datasets');
  await page.getByRole('button', { name: '导入 / 教材示例' }).click();
  await page.getByRole('tab', { name: '上传 CSV / Excel' }).click();
  await page.locator('input[type=file]').setInputFiles({ name: 'returns.csv', mimeType: 'text/csv', buffer: Buffer.from('arithmetic_return\n-0.15\n0.1\n0.35') });
  await page.getByRole('button', { name: '上传并预览' }).click();
  await expect(page.getByRole('combobox', { name: 'Excel工作表' })).toBeVisible();
  await page.getByText('数据准备：重命名、排序、转换与收益率计算').click();
  await page.getByRole('button', { name: '生成处理预览' }).click();
  await expect(page.getByText('处理前 3 行 → 处理后 3 行；删除 0 行')).toBeVisible();
  await page.getByRole('checkbox', { name: '我已确认字段含义、单位及正负号' }).check();
  await page.getByRole('button', { name: '保存新数据集' }).click();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: '归档', exact: true }).click();
  await page.getByRole('checkbox', { name: '已归档', exact: true }).check();
  await expect(page.getByRole('button', { name: '恢复', exact: true })).toBeVisible();
});

test('服务端字段错误清楚呈现且不产生保存记录', async ({ page }) => {
  const state = await fixtures(page); await page.route('**/api/jobs', async route => {
    if (route.request().method() === 'POST') return route.fulfill({ status: 422, json: { detail: '样本含缺失值，请显式准备后重试', field: 'target_column' } });
    return route.fallback();
  });
  await page.goto('/');
  await choose(page, '计算数据集', '教材例1.3 · 3 行');
  await choose(page, '样本列', 'arithmetic_return · arithmetic_return / decimal');
  await page.getByRole('button', { name: '开始试算' }).click();
  await expect(page.getByText('样本含缺失值，请显式准备后重试')).toBeVisible();
  expect(state.records).toHaveLength(0);
  await expect(page.getByRole('button', { name: '保存计算记录' })).toHaveCount(0);
});

# 市场风险工作台前端

React + TypeScript + Ant Design + Vite + ECharts。金融计算全部通过 Python HTTP 接口完成。

```powershell
npm ci
npm run dev
```

打开 `http://127.0.0.1:5173`。先启动 Python API（本机8000端口）；Vite 将 `/api` 请求代理过去。前端不保存数据库凭据。

```powershell
npm run typecheck
npm run build
npm test
```

测试使用 Playwright 浏览器与固定 HTTP 契约夹具验证交互，不代替真实 MySQL/计算器集成验收。首次运行测试需安装 Chromium：`npx playwright install chromium`。生产构建输出由部署层与 `/api` 同源服务，或者使用带代理的 `npm run preview` 本机预览。

支持数据预览/字段口径/显式准备、新快照、18章目录、第1章计算、全局任务状态与取消、手动保存、历史重开/另存/归档以及CSV/PNG/JSON导出。未保存预览和任务由后端本进程持有，重启不续算。缺失和非有限值不会画成零。

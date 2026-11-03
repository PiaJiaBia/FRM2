# 全章节接入验证

范围：GitHub #7 / PR #8，基线 `88c3426`，在既有第一章工作台之上扩展。

## 覆盖

- 第2–7章18操作、第8–11章14操作、第12–18章31操作；新增63操作，连同第一章4操作共67操作。
- 原有公开计算能力以单独操作或模型组合接入，详情见三个 coverage 文档。回调参数化边界明确记录，不接受任意Python代码。
- 每项新增操作的目录、默认参数、示例、输入口径与教材页码均可从API获取。

## 已执行

- `controller/risk_chapters_test.ipynb`：默认操作、模型分支、独立数值关系及非法域。
- `controller/dependence_chapters_test.ipynb`：14操作、组合矩/相关/Copula/回归/PCA关系。
- `controller/rates_chapters_test.ipynb`：31操作、34个选择分支、模型/树/期权/FRTB关系及15个无效边界。
- `api/all_chapters_test.ipynb`：63操作全部通过真实MySQL、HTTP、spawn子进程、保存、读取、配置及结果一致性检查；138.7秒。测试数据以本次UUID清理，保留用户记录。
- `controller/workbench_calculations_test.ipynb`：第一章原数值回归通过，目录断言更新为18章。
- `api/api_test.ipynb`：原HTTP/MySQL/取消/幂等/旧记录等回归通过。
- 最终8项浏览器测试全部通过：原6项、跨章复杂参数保存重开、真实利率树默认空现金流提交；非法JSON原始类型拒绝回归也通过。生产构建通过。已有UI/ECharts分包大于500KB警告保留。
- 实际浏览器完成第10章Copula示例载入、500样本试算、图表展示与保存；演示数据和记录供用户继续使用。
- 唯一service调整为第11章不依赖状态的对冲方法标记staticmethod，原Chapter11 notebook回归通过。

## 审查

Standards：2项（辅助权重列覆盖、结果索引列名冲突）。Spec：1项（合法空JSON数组被前端required拦截）。三项均已修复并由原审查者独立复核关闭：内部损失列隔离避免weight覆盖；共享无冲突索引标签保留普通/多层索引；JSON按结构而非长度校验，允许合法空数组、拒绝非法原始类型。数值notebook新增列重命名不变性与索引碰撞回归，浏览器新增真实ch12_tree默认配置回归。

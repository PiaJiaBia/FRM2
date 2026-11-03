# 工作台实施任务图

规格：[GitHub #1](https://github.com/PiaJiaBia/FRM2/issues/1)。草稿PR：[GitHub #6](https://github.com/PiaJiaBia/FRM2/pull/6)。

| 任务 | 范围 | 前置依赖 |
| --- | --- | --- |
| [#2](https://github.com/PiaJiaBia/FRM2/issues/2) | 计算适配、示例、操作目录和数值验证 | 已固定的实施契约 |
| [#3](https://github.com/PiaJiaBia/FRM2/issues/3) | 数据持久化、HTTP、后台任务和记录 | 已固定的实施契约；集成时需要#2 |
| [#4](https://github.com/PiaJiaBia/FRM2/issues/4) | React工作台与图表交互 | 已固定的实施契约；集成时需要#2和#3 |
| [#5](https://github.com/PiaJiaBia/FRM2/issues/5) | 合并、完整验收、文档、代码审查 | #2、#3、#4实现完成 |

三个实现任务在独立worktree和分支上并行。合并到同一功能分支后完成集成验收。PR关闭规格和任务；在PR合并前不提前关闭Issue。

已有18章和三层改造保存为基线提交 `83bcd24`；主分支起点为 `3b50f58`。本次PR包含基线提交，后续功能提交单独记录，便于区分此前工作。

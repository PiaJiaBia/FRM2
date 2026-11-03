# Issue tracker: GitHub

仓库：`PiaJiaBia/FRM2`。任务与规格保存在 GitHub Issues，通过 `gh` CLI 操作，显式指定 `--repo PiaJiaBia/FRM2`。

## 操作约定

- 创建：`gh issue create`，标题使用 `--title`，正文使用 `--body-file`。
- 读取：`gh issue view <number> --comments`，同时读取标签。
- 列举：`gh issue list`，按状态和标签筛选。
- 评论：`gh issue comment <number> --body-file <path>`。
- 标签：`gh issue edit <number> --add-label / --remove-label`。
- 关闭：`gh issue close <number>`。

多行正文先写入 UTF-8 文件，保留换行。技能要求发布到任务系统时，创建 GitHub Issue；要求读取任务时，读取 Issue 正文、标签和评论。

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Wayfinding

使用 wayfinder 时，以一个标记为 `wayfinder:map` 的 Issue 组织子任务；优先使用原生子任务和依赖关系，不可用时用任务列表、`Part of` 和 `Blocked by` 链接表达。

领取任务时分配给当前用户；完成后记录结果、关闭任务，并更新主 Issue 的决策摘要。

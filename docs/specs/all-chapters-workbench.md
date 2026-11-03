# 第2–18章工作台接入

对应 GitHub #7，接续第一章已完成工作台。用户要求全部接入，无需重新确认设计。

## 验收

- 18章均有可运行的真实计算操作；复用已有service，不复制公式或动态执行用户代码。
- 各章实质函数/类能力有覆盖清单，可按模型组合成操作；明确内部辅助函数。
- 提供每个操作的可复现示例、默认参数、公式、教材页码、输入单位与前提。
- 通用界面支持单列、多列、标量、枚举、布尔及结构化JSON参数。附加表用JSON行记录/矩阵显式传入，保存配置后可完整重开。
- 数据集仍是主DataFrame快照；次表属于计算配置，不隐式覆盖主表。
- 结果使用现有指标/表格/折线/柱图/散点契约；曲面按期限展示切片及完整表。
- 旧第一章操作ID、记录、数据准备流程保持兼容。
- 每个操作至少通过示例计算，另有数值锚点/关系验证；浏览器验证跨章切换、复杂参数、保存重开。

## 并行契约

三个适配模块：controller/chapter_groups/risk.py（2–7）、dependence.py（8–11）、rates.py（12–18）。各自提供 operations(), examples(), example_frame(id), calculate(df,metadata,request)。

操作新增 chapter:int、example_id:string；ID格式 chN_slug。参数类型 number/column/columns/select/text/json/boolean，支持 required:false、help。示例metadata含chapter。Result结构沿用workbench-contract.md。

根协调者实现注册、API和前端；各适配实施者独立worktree完成模块、对应notebook及覆盖清单。集成依赖四项全部完成，再审查修复。

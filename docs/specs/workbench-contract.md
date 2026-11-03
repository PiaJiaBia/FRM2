# 工作台实施契约

规格：market-risk-workbench.md / GitHub #1。以下契约供三个独立worktree并行实施，修改时先通知协调者。

## 第2–18章扩展（GitHub #7）

以下为初版契约的增量，覆盖后文“操作ID固定为四项”的历史限制：

- 新操作通过显式章节注册表加入，ID为 `chN_slug`；既有四个ID保留。catalog每操作新增 `chapter`，新增操作同时含 `example_id`。
- 参数增加 `columns`（有序多列）、`text`、`json`（数组/对象）和 `boolean`，以及 `required`、`help`。JSON空数组可表示无附加现金流，是合法值；不得解析执行代码。
- 示例metadata可带 `chapter`，用于进入正确章节。字段口径结构保持原样。
- HTTP的operation从枚举类型扩为经目录白名单校验的字符串，未知操作在提交时返回422。其余任务、保存、重开、导出接口不变。
- 附加表与矩阵作为请求参数保存；主DataFrame仍使用不可变dataset快照。章节适配源码纳入记录版本摘要。
- Result仍使用原有指标、完整表格和line/bar/scatter图；曲面使用明确的期限切片。

覆盖详情见 all-chapters-workbench.md 与 coverage-2-7.md、coverage-8-11.md、coverage-12-18.md。

## 任务边界

- calculation：拥有 controller/workbench_calculations.py 及其辅助模块、计算适配 notebook；不修改data/api/frontend。实现目录、示例、准备及计算函数。
- backend：拥有 data 新增持久化、api 包、API集成 notebook、Python依赖；不修改计算适配和frontend。兼容原有三张表和接口。
- frontend：拥有 frontend 包及前端测试；不修改Python代码。使用以下HTTP契约，不实现金融公式。
- integration：前三者完成后合并，真实MySQL和浏览器联调、文档、回归和审查。

## Python计算适配公开接口

controller.workbench_calculations 提供：
- catalog() -> {chapters: [{number,title,pages,available}], operations: [...]}。
- examples() -> [{id,name,description}]。
- example_frame(example_id) -> (DataFrame, metadata)。固定随机种子演示与教材给定值明确区分。
- prepare_frame(df, metadata, options) -> (DataFrame, metadata, changes)。options支持rename映射、date_column、sort_by数组、dropna_columns数组、conversions数组{column,kind:percent_to_decimal|loss_to_profit}、derive数组{operation:pnl|pvpnl|fvpnl|arithmetic_return|geometric_return,parameters:{...}}。metadata.fields以列名为key、value为{kind:date|price|payment|rate|arithmetic_return|geometric_return|pnl|loss|other,unit:decimal|percent|amount|date|other,sign:profit|loss|none}；转换须更新元数据；changes为{before_rows,after_rows,dropped_rows,added_columns}。
- calculate_frame(df, metadata, request) -> Result。request={operation:string,parameters:object}。对外操作ID固定为var、spectral、standard_error、diagnostics。字段角色和单位校验在此处，计算使用现有service。

操作参数：var {model:historical|normal|lognormal|compare,target_column,arithmetic_column?,geometric_column?,confidence_level}；spectral {model:historical|normal|lognormal,target_column,weight:es|exponential,confidence_level,gamma,method:integral|slices,n_slices}；standard_error {method:bootstrap|quantile|spectral,model:historical|normal|lognormal,target_column,confidence_level,interval_confidence,n_resamples,seed,n_slices?}；diagnostics {target_column}。未提供可选值由公开目录给出默认值。

Result={metrics:[{name,value:number|string|null,unit?}],tables:[{name,columns:string[],rows:object[]}],charts:[{title,x_label?,y_label?,series:[{name,type:line|bar|scatter,data:[number|string,number|null][]}],markers?:[{name,value:number}],areas?:[{from:number,to:number}]}],notes:string[]}。图表数据由Python产生，避免向浏览器发送Python对象或任意JS。NaN为null且notes明确说明，无穷值可用字符串±Infinity；前端不得绘制为0。

catalog.operations 每项含{id,name,workspace,description,formula,pages,assumptions,parameters:[{name,label,type:select|number|column,default?,options?:[{value,label}],min?,max?}]}。workspace为var|spectral|standard_error|diagnostics。前端可按operation固定组织交互，并使用目录说明。

## HTTP契约（统一 /api 前缀）

JSON错误响应 {detail:string}，字段错误可加field。所有JSON响应将非有限值安全表达。服务绑定127.0.0.1，开发代理允许本机前端。

- GET /health -> {status, database}。
- GET /catalog -> catalog()。
- GET /examples -> {items:examples()}。
- POST /previews/example {example_id} -> Preview。
- POST /previews/upload multipart(file,sheet?:string) -> Preview（Excel返回sheets数组，可选工作表重新上传预览）。
- POST /previews/{id}/prepare {metadata?,options} -> 新Preview（不改原预览）。
- POST /previews/{id}/save {name,metadata?,description?} -> Dataset摘要。
- GET /datasets?q=&archived=false&offset=0&limit=20 -> {items:Dataset[],total}。
- GET /datasets/{id}?offset=0&limit=100 -> Dataset详情。
- POST /datasets/{id}/prepare {options,metadata?} -> 新Preview，来源血缘保留。
- PATCH /datasets/{id} {name?,archived?} -> Dataset。
- GET /datasets/{id}/export -> CSV下载。
- POST /jobs {dataset_id,operation,parameters} -> Job。
- GET /jobs -> {items:Job[]}（包括本进程运行的任务）。
- GET /jobs/{id} -> Job（完成后含result）。
- POST /jobs/{id}/cancel -> Job。
- POST /jobs/{id}/save {name} -> Record（重复保存同一任务返回同一记录，防双击）。
- GET /records?q=&archived=false&offset=0&limit=20 -> {items:Record[],total}。
- GET /records/{id} -> Record详情，冻结的result和request。
- PATCH /records/{id} {name?,archived?} -> Record。
- GET /records/{id}/export?format=json|csv -> 配置或结果表下载。

Dataset={id,name,description?,row_count,column_count,created_at?,archived,metadata,columns?:string[],rows?:object[],total_rows?}。详情至少含分页样本列/行。Preview={id,columns,rows,row_count,metadata,sheets?:string[],changes?:object}，最多预览100行。Record={id,name,dataset_id,operation,created_at?,archived,request?,result?}。Job={id,dataset_id,operation,parameters,status:queued|running|completed|failed|cancelled,progress?:number|null,error?:string,result?:Result,record_id?:string}。

后端可新增表保存网页管理元数据，避免破坏旧快照。保存记录调用原repository计算记录接口并持久化request/result/name/archive；旧记录可读，无法映射为新Result时明确标记旧格式。预览和任务内存保存，重启不恢复。数据/记录的SQL只能位于data层。任务取消须真实中止或阻止结果发布，失败/取消不能保存。

## 验证约定

计算适配notebook使用手算/教材锚点。API集成notebook覆盖真实MySQL交易与HTTP流程，并只清理自身UUID数据。前端运行TypeScript及生产构建，补关键用户流程浏览器测试。每个实现代理提交自己的分支，不能操作主工作树的分支或凭据；本机配置仍读取D:/FRM2/config/mysql.local.toml，可通过环境变量指定，禁止提交密码。

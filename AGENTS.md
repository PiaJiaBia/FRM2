# 教材计算复现约定

本项目用于复现教材中的底层计算。以 `service/Market Risk Measurement and Mangement/Chapter1/market_risk_calculator.py` 和 `Chapter1_test.ipynb` 为代码组织与调用风格的参考；具体公式和参数以当前任务为准。

- 使用 `calculation-engine-coding` 时，默认直接在回复中提供代码并解释；用户明确要求创建、修改或迁移项目文件时，按该次授权落盘。下述 `.py` 与 `.ipynb` 分工不代表自动写入文件。
- 在 `.py` 中定义纯计算函数，在 `.ipynb` 中准备数据、导入函数、串联调用与验证结果。读取文件、数据清洗和展示属于调用层。
- 每章目录统一保留一个计算器 `.py` 和一个 `ChapterN_test.ipynb`；同章函数与类按主题分段放入该计算器。
- 数据输入统一使用 pandas DataFrame；窗口长度、置信度等计算参数可单独传入。逐行计算复制输入、增加结果列并返回 DataFrame，不修改传入对象；汇总计算允许返回标量或 Series。
- 底层假定调用方已保证字段、类型、单位、排序和数据有效性。直接实现公式，不添加缺列检查、自动转换、补值、排序、异常兜底或其他防御性处理。边界检查按调用任务的实际需求在调用层设计。
- 数学定义所需的分段、算法步骤属于计算本身，应完整实现。自然产生的 `NaN`（例如 `shift(1)` 的首行）保留，不默认填零或删除。
- 简要说明公式、字段含义、单位和必要前提；不把前提说明变成运行时校验。教材口径不明且会影响结果时先澄清，不能通过隐式默认值掩盖。
- 在 notebook 中通过教材例题、手算值或适当的数值关系验证计算；展示与核对即可，按需要添加简单断言，不默认引入测试框架。不要为此重构无关代码。

编写或修改底层计算器、配套 notebook 时，若可用，使用 `calculation-engine-coding` skill 获取可复用工作流程。上述项目约定独立于 skill 的安装状态生效。

## 三层目录

- `service/` 保存18章纯计算器及对应教材 notebook；不得依赖SQL、数据库配置或controller。通过 `service.load_chapter(number)` 获取章节模块。
- `data/` 管理MySQL连接、事务、DataFrame快照及计算记录；数据库为服务器上的 `FRM`。连接配置在被git忽略的 `config/mysql.local.toml` 或 `FRM_MYSQL_*` 环境变量中，禁止把密码写入代码、文档和notebook。
- `controller/` 负责读取、显式数据准备、调用service及保存结果。函数走 `calculate`，类组合走 `run`；边界校验按调用需求放在此层，底层计算器保持纯计算。
- 配套验证保留 `.ipynb`：`data/data_test.ipynb`、`controller/controller_test.ipynb`。数据库测试只清理本次生成的UUID记录，不覆盖真实业务数据。
- 一个工作流使用一个 `Database.session()` 事务；无异常才提交，异常回滚。初始化数据库是显式操作，不混入计算调用。

## Agent skills

### Issue tracker

使用 PiaJiaBia/FRM2 的 GitHub Issues 管理任务与规格。详见 [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md)。

### Triage labels

采用五个默认分诊标签。详见 [docs/agents/triage-labels.md](docs/agents/triage-labels.md)。

### Domain docs

采用 single-context：根目录 `CONTEXT.md` 与 `docs/adr/`。详见 [docs/agents/domain.md](docs/agents/domain.md)。

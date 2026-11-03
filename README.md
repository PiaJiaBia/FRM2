# FRM 教材计算项目

## 浏览器工作台

工作台使用 React、TypeScript、Ant Design、Vite 和 ECharts。Python HTTP接口复用本项目的纯计算器，连接已有MySQL。18章均提供实际计算操作、参数配置、示例和结果表图。

首次准备（项目根目录）：

```powershell
python -m pip install -r requirements.txt
python -m api init-db
cd frontend
npm ci
```

分别在两个终端启动：

```powershell
# 终端一，项目根目录
python -m api

# 终端二，frontend目录
npm run dev
```

打开 `http://127.0.0.1:5173`；API默认使用本机8000端口。MySQL配置仍由后端读取，可以设置 `FRM_MYSQL_CONFIG` 指向另一份本机TOML。凭据不进入浏览器和版本库。初始化只新增工作台配套表，不覆盖旧数据。

基本流程：选择示例或上传CSV/Excel → 预览与确认字段含义/单位/正负号 → 显式数据准备 → 保存数据集 → 选择章节模型试算 → 查看表格/图表 → 手动保存记录或导出。算术和对数收益率不混用；参数法结果为损失比例，尚不进行头寸换算。

第2–18章也可从操作页点击“载入本操作演示并保存数据集”，载入明确标注的合成演示数据和对应默认参数。主表选择已保存数据集；附加表、矩阵、向量使用参数中的JSON数组/对象，并随计算配置完整保存。列名参数可改成自己的字段；利率、波动率、期限、矩阵顺序等口径见每个操作说明。示例不代表真实行情，也不构成现行监管规则实现。

各章覆盖清单：[2–7章](docs/specs/coverage-2-7.md)、[8–11章](docs/specs/coverage-8-11.md)、[12–18章](docs/specs/coverage-12-18.md)。回调函数使用明确的模型族组合，不执行用户输入的Python表达式；波动率曲面显示期限切片与完整表格。

原始数据保留，准备结果保存成有来源记录的新快照。价格派生收益率产生的首行缺失不会自动删除；需要时显式选择删除缺失行后再计算。任务切换页面后仍运行，取消会终止或阻止结果发布。未保存的试算和预览不跨服务重启保留，已保存数据与结果保存在MySQL。记录保存采用当次结果，不在重新打开时偷偷重算。

前端验证：`npm run typecheck`、`npm run build`、`npm test`。计算及HTTP适配验证仍使用配套notebook；详见各notebook中的数据和清理约定。

当前受限开发环境的新增Python依赖安装在被忽略的 `outputs/runtime`，可在启动前执行 `$env:PYTHONPATH = "$PWD/outputs/runtime"`；正常安装requirements的环境无需此设置。

规格及任务：[Issue #1](https://github.com/PiaJiaBia/FRM2/issues/1)，实现PR：[PR #6](https://github.com/PiaJiaBia/FRM2/pull/6)。

全部章节扩展：[Issue #7](https://github.com/PiaJiaBia/FRM2/issues/7)、[PR #8](https://github.com/PiaJiaBia/FRM2/pull/8)。

计算器按章节放在 `service` 下，数据层以 DataFrame 为输入输出，controller 串联数据和计算。原有18章公式、注释及教材页码保留在章节计算器中。

```text
FRM2/
├── service/
│   ├── catalog.py                  # 统一加载18章计算器
│   └── Market Risk Measurement and Mangement/
│       ├── Chapter1/               # 一个calculator.py + Chapter1_test.ipynb
│       ├── ...
│       └── Chapter18/
├── data/
│   ├── database.py                 # 配置、连接、事务
│   ├── repository.py               # DataFrame快照、计算记录
│   ├── codec.py                    # 类型化JSON
│   ├── schema.sql
│   └── data_test.ipynb
├── controller/
│   ├── risk_controller.py
│   ├── __main__.py                  # CLI
│   └── controller_test.ipynb
└── config/
    ├── mysql.example.toml
    └── mysql.local.toml             # 本机配置，git忽略
```

## 数据库与运行

MySQL 位于 `10.8.100.149:3306`（Yichenlu），数据库 `FRM`。Python 三层代码在本项目运行，通过网络连接该数据库。需要 Python 3.11 或以上。

```powershell
cd D:\FRM2
python -m pip install -r requirements.txt
# 新机器先复制示例配置并填写连接信息；当前机器已配置。
python -m controller health
python -m controller list-datasets
```

`python -m controller init-db` 显式创建数据库及缺失表，不删除旧数据。也可以通过 `FRM_MYSQL_HOST`、`FRM_MYSQL_PORT`、`FRM_MYSQL_USER`、`FRM_MYSQL_PASSWORD`、`FRM_MYSQL_DATABASE` 覆盖本机配置。

三张表：`frm_schema_versions` 记录结构版本；`frm_datasets` 保存不可变DataFrame快照和元数据；`frm_calculations` 保存输入快照ID、操作名称、参数、显式数据准备步骤、结果及计算器源码摘要。每次保存生成新ID，同名数据集不覆盖。

## 函数与类调用

在项目根目录运行，或在notebook中把项目根目录加入 `sys.path`：

```python
import pandas as pd
from data import Database, MySQLConfig
from controller import RiskController
from service import load_chapter

database = Database(MySQLConfig.load())
frame = pd.DataFrame({'r': [-0.04, -0.02, 0.0, 0.01, 0.03]})

with database.session() as repository:
    dataset_id = repository.save_dataset(
        'daily_returns', frame, metadata={'unit': 'decimal', 'horizon': '1 day'}
    )
    controller = RiskController(repository)
    result = controller.calculate(
        dataset_id, chapter=1, function='cal_normal_var',
        parameters={'target_column': 'r', 'confidence_level': 0.95},
    )
print(result.value, result.run_id)
```

参数法收益率VaR的结果仍是损失比例；头寸换算由调用方决定。service支持直接调用全部章节中的函数和类，不必经过数据库。

类组合示例：

```python
chapter = load_chapter(1)

def historical_es(df, target_column, confidence_level):
    quantile = chapter.HistoricalLossQuantile(df, target_column)
    return chapter.ExpectedShortfall(quantile, confidence_level).calculate()

with database.session() as repository:
    result = RiskController(repository).run(
        dataset_id, operation='historical_es', calculator=historical_es,
        parameters={'target_column': 'r', 'confidence_level': 0.95},
    )
```

`calculate` 适合首参数为DataFrame的章节函数；多表输入、特殊参数以及类组合使用 `run` 包装。额外输入的ID/版本应在参数中显式记录。自定义函数不被序列化，重放须保留调用代码；源码摘要覆盖章节计算器，不代表已归档自定义包装函数。

## 数据准备与事务

默认保持原始样本。调用方可显式提供 `preparation={'rename': {...}, 'sort_by': [...], 'dropna_columns': [...]}`，按重命名、排序、删除指定列缺失行的顺序处理；这些步骤记录到计算记录，原始快照不变。字段含义、单位、置信度和数据适用性由调用方保证。

`save=False` 只计算，不保存计算记录。`Database.session()` 在正常退出时提交，异常退出时回滚。多次存取和计算可放在同一事务；`rollback=True` 可用于不留数据的试算。

快照使用带类型的JSON保存常见数值、字符串、分类、时间列，以及DataFrame、Series、数组等结果，保留NaN/无穷值。任意自定义Python对象不支持入库，不使用pickle。这是按数据集整体存取的存储方式；行级筛选在读取后的DataFrame上完成，后续若需要大规模行情逐行SQL查询，再扩展专门行情表。

CLI还提供 `import-csv`、`calculate`、`get-run`，详见 `python -m controller --help`。`calculate --options` 接收包含 `parameters` 和 `preparation` 的JSON文件。

## 验证

每章 `ChapterN_test.ipynb` 验证教材公式。`data_test.ipynb` 验证序列化、提交、跨连接读取及回滚；`controller_test.ipynb` 验证函数/类编排、结果持久化和18章加载。数据库集成测试使用临时UUID，完成后清理这些记录。

当前机器可执行：

```powershell
python outputs/execute_notebooks.py
python outputs/execute_notebooks.py data controller
```

# 第8–11章接入覆盖

对应 GitHub Issue #7。实现位于 `controller/chapter_groups/dependence.py`，验证位于 `controller/dependence_chapters_test.ipynb`。公式调用现有 service，调用边界负责有限值、维数、正定性、概率域及计算量检查，不修改计算器、样本、单位或顺序。

## 操作与教材页码

| 章 | 操作 ID | 接入的公开计算能力 | 教材页码 |
| --- | --- | --- | --- |
| 8 | ch8_moments | correlation_matrix（Pearson/Spearman/Kendall）、portfolio_moments | 104–106、118 |
| 8 | ch8_covariance_var | covariance_from_correlation、portfolio_var | 108–109 |
| 8 | ch8_implied | implied_average_correlation | 106–107 |
| 8 | ch8_joint_default | joint_default_probability | 113–114 |
| 9 | ch9_rolling | rolling_pair_correlation | 122–126 |
| 9 | ch9_regimes | average_pair_correlation、regime_correlations | 122–123 |
| 9 | ch9_reversion | mean_reversion_regression、autocorrelation | 124–126 |
| 10 | ch10_sample | GaussianCopula 构造与 sample | 130–133 |
| 10 | ch10_joint | GaussianCopula 构造与 joint_probability | 130–133 |
| 10 | ch10_default_times | exponential_default_times | 133 |
| 10 | ch10_marginals | map_marginals；支持正态、指数、Student-t逆CDF配置 | 130–133 |
| 11 | ch11_regression | RegressionHedge 构造、summary、predict、hedge_positions | 136–141 |
| 11 | ch11_pca | PrincipalComponents 构造、transform、loadings、explained_variance | 142–145 |
| 11 | ch11_factor_hedge | PrincipalComponents.hedge_positions | 145 |

上述四章所有公开计算函数、类和公开计算方法均已接入。函数内部使用的分布函数不是独立网页操作。任意 Python 回调不开放给网页：边际映射通过固定分布白名单配置替代可执行表达式。Student-t 和秩相关选项是现有通用接口的实例化扩展，不声称是教材另给的公式。

## 输入与输出

- 每个操作声明 `chapter`、`example_id`、参数类型与可编辑默认参数。原始样本列通过 column/columns 参数选择，矩阵和向量按明确的行/列顺序提供，不能自动重排。
- 相关与组合矩输入同频收益率，单位为小数；组合权重也允许有符号金额，输出随权重量纲。协方差VaR输入逐资产波动率及金额敞口，持有期以波动率样本期为单位。
- 第9章采用原始行顺序。滚动窗口的自然缺值保留为 null。分状态相关使用用户提供的状态字段，不猜测状态、不删除样本。均值回归系数是一步离散系数，不等同连续模型速度。
- Copula 模拟以主表每行代表一个变量，表内数值不参与模拟；潜变量相关矩阵和显式随机种子决定样本。联合概率使用逐变量概率列。边际映射输入必须是严格位于 (0,1) 的均匀变量；指数危险率的时间单位决定违约时间单位。
- 回归使用同单位、已对齐的变动样本及一致方向的 DV01，返回带符号对冲数量。PCA使用协方差，不擅自标准化，网页要求正定协方差。因子对冲使用已定义的共同因子敞口，不重复估计载荷。
- 输出包括标量、完整表格以及适用的滚动线、ACF柱、Copula散点、映射路径、回归拟合、PCA得分图。图超过1000点时只对显示抽样，完整表格不抽样。
- 不把多维正态CDF误称为确定性结果：二维使用现有确定性积分，多维使用SciPy数值CDF，说明末位可能变化。

## 验证

执行 notebook 全部代码单元：14个操作的默认示例均能运行、输入保持不变、结果可严格 JSON 序列化。另验证组合波动率手算、对角协方差、独立违约乘积、隐含相关、滚动空值、状态正负相关、离散回归速度、Copula固定种子一致性、教材联合概率0.0344、逆CDF反演、回归系数和对冲数量、PCA载荷重构协方差以及对冲后敞口为零。

无效域检查包括非正定相关矩阵、均匀变量端点、共线回归、不可行Bernoulli相关、小数窗口、超出模拟上限与缺失数值。没有连接数据库、读取真实持仓或修改已有记录。

# 第12–18章网页接入覆盖

对应 GitHub [#7](https://github.com/PiaJiaBia/FRM2/issues/7)。适配器为 `controller/chapter_groups/rates.py`，调用既有计算器，不复制金融公式、不改变底层计算接口。

每项操作都带 `chapter`、教材页码、公式、假设、可替换列映射和可运行示例。31个示例均为构造数据，随机路径固定种子42；不会将示例冒充教材原始观测。额外矩阵/第二张表以JSON显式输入，随请求保存，不执行用户代码。金额沿用输入币种；利率/波动率为小数，期限以年计，流动性期限以天计。

## 操作及服务覆盖

| 章 / 教材页码 | 网页操作 | 复用的计算器接口 |
| --- | --- | --- |
| 12 / 148–156 | `ch12_probability` | `risk_neutral_probability` |
| 12 | `ch12_replication` | `replicating_portfolio`，列映射与当前资产价格数组 |
| 12 | `ch12_tree` | `BinomialRateTree.rollback/price/option_adjusted_spread/calibrate_probabilities`；支付、节点现金流、提前put/call行权、OAS求根、概率校准 |
| 12 | `ch12_cmt`, `ch12_attribution` | `cmt_payments`, `pnl_attribution` |
| 13 / 160–163 | `ch13_discount` | `expected_discount_factor` |
| 13 | `ch13_forward` | `forward_from_discount_factors` |
| 13 | `ch13_decomposition` | `forward_decomposition` 与 `expected_bond_return` 组合输出 |
| 14 / 166–175 | `ch14_simulation` | `GaussianDrift`, `HoLee`, `HoLee.from_forward_derivative`, `Vasicek`；通用Euler及Vasicek精确模拟 |
| 14 | `ch14_curve` | 上述模型的 `discount`；Vasicek `moments/forward` |
| 15 / 178–182 | `ch15_simulation` | `TimeDependentGaussian`, `CIR.simulate_uniforms`, `Courtadon`, `LognormalRate`, `BlackKarasinski`, `TimeDependentBlackKarasinski` |
| 15 | `ch15_analytics` | `TimeDependentGaussian.moments/discount` 与 `CIR.discount` |
| 15 | `ch15_tree` | `LognormalRate.binomial_tree` |
| 16 / 184–191 | `ch16_curve` | `GaussPlus.moments/discount/yield_loadings/yield_volatility/regression_loadings` |
| 16 | `ch16_calibration` | `GaussPlus.fit_speeds/fit_volatilities/fit_long_run_mean/fit_state`，四个独立阶段 |
| 16 | `ch16_hedge`, `ch16_half_life` | `GaussPlus.hedge_positions`, `vasicek_half_life` |
| 17 / 194–204 | `ch17_options` | `EuropeanOption.price/quotes/greeks/implied_volatility`，call/put |
| 17 | `ch17_surface` | `VolatilitySurface.evaluate`，双线性插值和期限微笑切片图 |
| 17 | `ch17_density`, `ch17_jump`, `ch17_delta` | `risk_neutral_density`, `jump_mixture_price`, `minimum_variance_delta` |
| 18 / 206–212 | `ch18_sensitivity` | `sensitivity_charge` 与 `correlation_scenarios` |
| 18 | `ch18_curvature`, `ch18_default`, `ch18_residual` | `curvature_charge`, `default_charge`, `residual_add_on` |
| 18 | `ch18_liquidity`, `ch18_stress`, `ch18_weighted` | `liquidity_adjusted_es`, `stress_scaled_es`, `weighted_es` |
| 18 | `ch18_capital`, `ch18_pla` | `capital_requirement`, `pnl_attribution_ratios` |

抽象基类 `ShortRateModel` 不作为可实例化操作；各模型 `drift/diffusion` 在模拟中使用，`GaussPlus._transition` 为内部转移算法。第16章导入的Vasicek复用第14章操作，无须重复按钮。CIR使用教材计算器提供的精确非中心卡方转换，不开放继承的可能产生负利率Euler方法。

## 网页参数化边界

- Ho-Lee漂移及远期导数为 `a+b*t`；时间依赖高斯波动率为 `σ exp(−decay*t)`。时间依赖BK中 `k` 为常数，中心利率为 `θ exp(a*t)`，波动率为 `σ exp(−decay*t)`。这些是明确可编辑的函数族，未声称支持任意Python回调。
- 利率树提前行权提供常数执行价的put/call规则；任意节点回调仍属于Python计算器调用方式。现金流可输入每个节点值，支持无现金流的空数组。
- Gauss+校准边界在操作说明中明示：速度 `[.001,3]`，波动率 `[.00001,.1]`，相关 `[-.99,.99]`。当前模型参数作为拟合初值或前阶段已知参数。输出优化成功标志、成本和迭代信息，不隐藏未收敛状态。
- 输入数据需要显式排序与处理缺失；适配层检查有限数、正期限、概率和、相关矩阵、满秩复制矩阵等适用前提。不会自动删行、换单位或补值。树结构中的无效节点允许null并保留缺值。
- 波动率曲面使用完整矩形网格，查询不外推；风险中性密度允许展示负估计值并说明其对应报价凸性问题，不裁剪。
- FRTB所有操作均复现本教材口径，包括旧PLA比率，不将结果称为现行监管合规结论。
- 标量操作仍保存所选数据集作为输入快照，但数值完全由表单的显式参数决定；说明中已标明。
- 单次普通输入上限10000行；树100步；路径100000冲击；Gauss+曲线500期限、校准50观测；IV1000报价；敏感度300因子。图表最多12列/1000点，完整表格保留全部结果。

## 验证

`controller/rates_chapters_test.ipynb` 已在真实Python kernel运行通过，6个代码单元：

- 31个操作全部默认示例通过，结果可严格JSON往返、输入DataFrame不被修改。
- 34个select选项分支全部运行通过；CIR分支显式使用(0,1)均匀冲击。
- 树复制价格、回溯、OAS、校准、提前行权/现金流，收益率分解和CMT使用手算值。
- 高斯确定性路径/解析矩、Ho-Lee平坦曲线、Vasicek矩、CIR非负性、BK转换与对数树中心节点使用独立关系。
- Gauss+从合成曲线恢复三状态、速度、波动率和长期均值；协方差半正定；三因子对冲和半衰期核对。
- 期权put-call平价、IV反解、曲面插值与对数正态密度、跳跃价格及最小方差Delta核对。
- 第18章9项操作全部有手算锚点；15个无效边界拒绝测试及任意列名映射测试通过。

这些适配测试不代替数据库/API与浏览器集成验证，后者由总体集成流程执行。

# 第2–7章工作台覆盖清单

对应 GitHub #7。适配器 `controller/chapter_groups/risk.py` 提供18个实际计算工作区；每个工作区有独立示例，模型选择覆盖下表分支。未向前端开放任意 Python 表达式或动态函数名。

| 章/教材页 | 工作区 | 已接入计算器能力 |
|---|---|---|
| 2 / 18–34 | distribution | HistoricalDistribution.quantile/expected_shortfall；age_weights；自定义权重；KernelDistribution.cdf（分位数求根内部调用）/quantile/expected_shortfall；quantile_interval |
| 2 | scenarios | historical_scenarios、volatility_scale、correlation_scale、filtered_scenarios，全部4种可选 |
| 2 | garch | AsymmetricGARCH 指定参数与fit；filter；filtered_paths；拟合不收敛报告错误 |
| 2 | bootstrap | bootstrap_estimates；IID/循环区块；注册估计器为历史VaR、历史ES、样本均值 |
| 3 / 36–47 | gev | block_maxima；GeneralizedExtremeValue 指定参数、fit、fit_gumbel_moments、fit_gumbel_regression、fit_quantile_regression；quantile、parent_quantile、expected_shortfall |
| 3 | pot | PeaksOverThreshold 指定参数、fit、fit_moments；quantile、expected_shortfall |
| 3 | tail | hill_index、pickands_index、tail_extrapolation（以Hill尾指数外推） |
| 4 / 50–57 | coverage | exception_series；CoverageBacktest.unconditional/independence/conditional；支持已有异常序列 |
| 4 | counts | exception_count_probabilities；traffic_light，仅250日/99%显示教材历史规则 |
| 5 / 60–72 | linear | LinearRiskMapping.var/components/tracking_var |
| 5 | cashflows | cashflow_present_values → duration_map；明确节点久期和复利次数 |
| 5 | derivatives | forward_exposures、fra_value、swap_cashflows；选择工具，互换时点0浮息债价值另行说明 |
| 5 | delta_gamma | delta_gamma_pnl，输入标的价格绝对变动 |
| 6 / 74–84 | sensitivity | finite_difference_sensitivity；安全注册估计器为第5章线性VaR，逐行扰动敞口 |
| 6 | intervals | quantile_confidence_interval、order_probability_interval、exception_probability_interval |
| 6 | benchmark | benchmark_comparison |
| 7 / 89–100 | pit | probability_integral_transform（正态预测参数逐行输入）→ pit_diagnostics；也接受已有其他连续模型PIT |
| 7 | dependence | ljung_box、pit_independence、linear_probability_model、exception_logit、duration_test |

所有公共服务能力均已直接暴露或组合调用。`_bernoulli_loglik` 为覆盖率检验内部实现，不做单独网页操作。接受 Python 回调的底层接口在网页使用上述命名估计器/分布组合；需要其他模型的PIT可预先计算后导入，网页不执行用户代码。

输入及限制：

- 一次任务以保存的数据集为主DataFrame；额外协方差矩阵、模型参数与拟合边界作为JSON数组进入任务参数并随记录保存。矩阵顺序与所选因子/敞口行一致；不推断顺序。
- 收益率与利率采用小数，期限为年。历史损失分布/EVT输入损失为正；不会把盈利列自动反号。第4章损失和提前预测VaR须同期间同单位。
- 各操作的默认示例为固定种子或构造值，不宣称真实市场数据。章节页码取自现有计算器头注，PDF页序为教材页码+11。
- 数值列要求无缺失且有限；域限制、矩阵维度/半正定、整数参数、计算规模约束在controller检查，service未修改。
- 带权/KDE工作区中附带的顺序统计区间仍对应原始等权样本，结果名称及说明明确该差别。
- GEV可按等长分组提取区块最大值；母分布区块大小需与组大小一致。POT概率必须进入阈值以上尾部，ES要求尾指数小于1。
- 绘图最多8条序列、600个等距展示点，完整表格不截断。非有限值在表格按null/字符串表达，不绘成零。
- 第7章回归要求预先对齐预测变量；不隐式shift。持续期仅使用完整相邻异常间隔。

验证 `controller/risk_chapters_test.ipynb`：全部18个默认操作、全部模型选择分支、输入不变、固定种子可重现、各章已知解析/教材值、非法PIT/异常序列/阶数/矩阵/整数边界。直接执行全部代码单元通过。原18章service未改动。

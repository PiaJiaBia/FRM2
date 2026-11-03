# 市场风险教材计算复现

依据用户提供的 **2025 FRM Part II — Market Risk Measurement and Management** 扫描教材，按原目录 `Chapter1` … `Chapter18` 组织。保留项目原有英文目录拼写。

每章的计算器在 `.py`，数据准备、公式核对、调用示例在 `ChapterN_test.ipynb`。从该章目录启动 notebook，按顺序运行全部单元格。跨章复用通过项目根目录导入；第15、16章复用第14章的短率模型。依赖见 `requirements.txt`。

## 统一约定

- 数据输入是 DataFrame；列名通过参数传入，业务字段映射由调用层完成。样本有效性、缺值、单位、时间排序由调用层负责。
- 计算器直接计算并返回数值、Series或DataFrame；逐行输出复制输入。没有自动补值、异常兜底和输入校验框架。
- 正负号写在函数注释中：第1章 VaR 接收盈利为正的数据并取负；第2、3章损失分布直接接收损失为正的数据。
- 算术收益率正态模型输出损失比例；对数收益率正态模型经指数转换输出损失比例。头寸规模不由分布模型自动决定。
- 收益率、利率、波动率默认使用小数。时间默认以年计；历史日样本、持有期步数与监管流动性天数在对应函数注明。百分数单位的教材例题会显式说明。
- 类用于分布、可替换权重、校准模型或需复用状态的计算。简单公式保留函数形式。
- 数学定义所需的分段、排序、似然零项、跳变积分点属于计算本身。输入前提由调用者保证。
- 随机示例固定生成器种子；模拟器可直接接受调用层生成的冲击DataFrame。

## 页码与复现范围

正文第1页是PDF第12页，**PDF页序 = 教材页码 + 11**。代码内 `p.` / `pp.` 都指印刷页码，不是PDF页序。每章模块头及 notebook 给出对应页码，函数注释进一步指向公式或小节。

这里交付的是18章的计算方法、可执行示例与公式验证。**不等于逐张复刻全部图表、重建未提供的银行/市场原始数据，也不包括为每个课后题单独作答。** 定性内容、未提供数据和实现简化见下表；不以随机数据冒充教材真实结果。

| 章 | 教材 / PDF页序 | 计算器与覆盖内容 | 测试入口 |
|---|---|---|---|
| 1 | 2–16 / 13–27 | `market_risk_calculator.py`：收益、VaR、ES/谱风险、切片与积分、StandardError（quantile/spectral/bootstrap）、QQ与平均超额 | [Chapter1_test](Chapter1/Chapter1_test.ipynb) |
| 2 | 18–34 / 29–45 | `historical_calculator.py`：历史重估输入、经验/加权VaR与ES、KDE、顺序统计区间、年龄/波动率/相关调整、AGARCH、filtered HS及block bootstrap | [Chapter2_test](Chapter2/Chapter2_test.ipynb) |
| 3 | 36–47 / 47–58 | `extreme_value_calculator.py`：GEV/Gumbel、母分布分位数、尾积分、MLE/排序回归/矩估计、Hill、Pickands、POT/GPD | [Chapter3_test](Chapter3/Chapter3_test.ipynb) |
| 4 | 50–57 / 61–68 | `backtest_calculator.py`：异常指示、Kupiec、Christoffersen独立/条件覆盖、二项概率、教材交通灯表 | [Chapter4_test](Chapter4/Chapter4_test.ipynb) |
| 5 | 60–72 / 71–83 | `mapping_calculator.py`：线性因子VaR、Euler分解、跟踪风险、久期/现金流映射、FX远期、FRA、swap现金流、delta-gamma | [Chapter5_test](Chapter5/Chapter5_test.ipynb) |
| 6 | 74–84 / 85–95 | `validation_calculator.py`：有限差分敏感度、分位数区间、顺序统计概率区间、异常概率区间、基准比较；回测复用第4章 | [Chapter6_test](Chapter6/Chapter6_test.ipynb) |
| 7 | 89–100 / 100–111 | `pit_calculator.py`：PIT、KS/AD/CVM、Ljung–Box、LPM/Logit、PIT回归、完整异常间隔的Weibull duration LR | [Chapter7_test](Chapter7/Chapter7_test.ipynb) |
| 8 | 102–120 / 113–131 | `correlation_calculator.py`：相关矩阵、组合均值/波动/VaR、隐含平均相关、Bernoulli联合违约概率 | [Chapter8_test](Chapter8/Chapter8_test.ipynb) |
| 9 | 122–128 / 133–139 | `empirical_correlation_calculator.py`：滚动/分组相关、平均相关、离散均值回复、自相关 | [Chapter9_test](Chapter9/Chapter9_test.ipynb) |
| 10 | 130–133 / 141–144 | `copula_calculator.py`：Gaussian copula、联合概率、相关均匀抽样、边际逆映射、指数默认时间 | [Chapter10_test](Chapter10/Chapter10_test.ipynb) |
| 11 | 136–145 / 147–156 | `hedging_calculator.py`：通用多变量OLS、DV01对冲、PCA、方差贡献与因子对冲；水平/变化/反向回归通过交换调用列实现 | [Chapter11_test](Chapter11/Chapter11_test.ipynb) |
| 12 | 148–156 / 159–167 | `tree_calculator.py`：复制组合、风险中性概率、多期回溯、曲线概率校准、提前行权、CMT、OAS和顺序P&L归因 | [Chapter12_test](Chapter12/Chapter12_test.ipynb) |
| 13 | 160–163 / 171–174 | `forward_decomposition_calculator.py`：远期、期望折现、预期收益、漂移/风险溢价/凸性分解 | [Chapter13_test](Chapter13/Chapter13_test.ipynb) |
| 14 | 166–175 / 177–186 | `short_rate_calculator.py`：短率模型抽象、常数高斯漂移、Ho–Lee曲线匹配、Vasicek矩/模拟/折现/远期 | [Chapter14_test](Chapter14/Chapter14_test.ipynb) |
| 15 | 178–182 / 189–193 | `volatility_model_calculator.py`：时间波动高斯、CIR精确转换及闭式债价、Courtadon、对数利率树、常数/时间变化BK | [Chapter15_test](Chapter15/Chapter15_test.ipynb) |
| 16 | 184–191 / 195–202 | `gauss_plus_calculator.py`：Vasicek复用、Gauss+三状态两冲击、矩与债价、状态反解、三阶段校准、因子对冲 | [Chapter16_test](Chapter16/Chapter16_test.ipynb) |
| 17 | 194–204 / 205–215 | `volatility_surface_calculator.py`：BSM、隐波、双线性曲面、Greeks/MV delta、离散跳跃、隐含风险中性密度 | [Chapter17_test](Chapter17/Chapter17_test.ipynb) |
| 18 | 206–212 / 217–223 | `trading_book_calculator.py`：敏感度/相关情景、曲率、默认与残余风险、流动性ES、压力缩放、WES、资本和教材PLA比率 | [Chapter18_test](Chapter18/Chapter18_test.ipynb) |

## 已知口径与数据限制

1. **教材与市场数据**：第1章保留已有BYD价格数据及合成现金流演示；其他章优先用教材明示数据或可独立核对的合成数据。第6–9章银行及市场实证样本、第11章LIBOR全样本、第16章美债全样本没有随PDF提供，因此不重建其完整实证结果。
2. **第3章**：阈值选择、极值簇处理、多变量EVT是教材扩展讨论，不把某个自动阈值或多变量尾模型当作教材规定。条件EVT可由第2章标准化残差接入POT。Pickands是教材脚注提及方法的实现。
3. **第5章**：复杂产品的逐情景全重估由调用方定价函数提供；现有模块覆盖映射与组合计算，不是全品种交易定价系统。现金流可在调用层构造后复用折现/映射方法。
4. **第7章**：duration LR使用完整的相邻异常间隔；窗口首尾删失区间没有纳入其似然。AD只报告统计量，未冒用其他分布下的临界值。PIT等检验的预测值必须事先对齐，不能用未来数据拟合。
5. **第12–15章**：利率树使用单期简单复利，连续模型债价使用连续复利。Euler方法存在离散误差；Vasicek、CIR和常参数BK另外提供精确转移。时间相关BK用对数Euler路径，不声称为一般时间相关参数构造了精确重组树。
6. **第16章**：Gauss+是教材r、m、l三状态、两冲击的模型，不是G2++。分阶段校准返回优化结果，调用方负责查看求解成功状态与识别性。实际市场曲线的插值、市场日历等由调用层准备。
7. **第18章**：复现该教材的监管例子，不据此判断现行合规。监管权重、净额规则、风险类别、不可建模因素等输入由调用层确定。

## 教材数值勘误及实现选择

- 第3章p.45 / PDF56，Example 3.6：`beta=0.8, xi=0.15, u=2, Nu/n=0.04`，99.5% VaR/ES为3.952/5.238。99.9% VaR为5.942，按式(3.23) ES为**7.578**，不是原文印出的17.578。测试按公式核对。
- 第18章p.207 / PDF218，式(18.1)印刷的二次型缺少清晰的平方根。计算器按其紧邻文字的“标准差”解释返回平方根，保持金额量纲；注释明确此选择。
- 历史分位数采用经验逆CDF的`ceil(n*p)`阶，不插值；经验ES对边界观测取部分概率质量。教材整数尾样本情形与此一致。
- 第1章谱风险同时保留教材`n-1`内部点平均法和连续数值积分，两者在小切片数下本来就不同。

## 验证

18个notebook均通过真实Python内核执行，输出保存在文件中。检查包括教材例题、解析公式、守恒关系、独立有限差分、概率变换回代及合成参数恢复；不是仅检查文件可导入。

执行记录位于 `D:/FRM2/outputs/verification/`。第一章原notebook备份在 `D:/FRM2/outputs/chapter1_before_update.ipynb`。临时OCR、依赖和生成辅助脚本不属于计算引擎接口。

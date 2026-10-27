import json
from pathlib import Path

p = Path('D:/FRM2/Market Rist Measurement and Mangement/Chapter1_Estimating_Market_Risk_Measures.ipynb')
original = p.read_bytes()
n = json.loads(original)
backup = p.with_suffix('.before_var_es.ipynb.bak')
if not backup.exists():
    backup.write_bytes(original)

source = ''.join(n['cells'][3]['source'])
old = '''def prepare_data(df):
    result = df.copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"])
    return result.sort_values("trade_date").reset_index(drop=True)'''
new = '''def prepare_data(df):
    """统一排序及基础校验；数据应为单只资产、完整交易日序列。"""
    result = df.copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"]).dt.normalize()
    if result["trade_date"].isna().any():
        raise ValueError("交易日期不能缺失")
    if result["trade_date"].duplicated().any():
        raise ValueError("每个交易日只能有一条记录，请先筛选单只资产")
    if "thscode" in result and result["thscode"].nunique(dropna=False) != 1:
        raise ValueError("请先筛选单只资产")
    required = ["book_value", "interim_payments", "discount_rate"]
    if not np.isfinite(result[required].to_numpy(dtype=float)).all():
        raise ValueError("市值、现金流和利率必须为有限数值")
    if (result["book_value"] <= 0).any():
        raise ValueError("book_value 必须为正")
    if (1 + result["discount_rate"] / 252 <= 0).any():
        raise ValueError("日增长因子必须为正")
    return result.sort_values("trade_date").reset_index(drop=True)'''
assert old in source
n['cells'][3]['source'] = source.replace(old, new).splitlines(keepends=True)

common = '''    if not np.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("confidence 必须在 0 和 1 之间")
    result = prepare_data(df)
    if len(result) < 3:
        raise ValueError("至少需要三个日期，形成两个收益观测")
    # 复用前面 cal_ar / cal_gr 已生成的列；仅首行无上一期数据。
    samples = result[["arithmetic_return", "log_return"]].iloc[1:]
    if not np.isfinite(samples.to_numpy(dtype=float)).all():
        raise ValueError("收益率包含缺失或非有限值，请检查现金流及总收益倍数")
    gross = 1 + samples["arithmetic_return"]
    if (gross <= 0).any():
        raise ValueError("对数正态模型要求总收益倍数为正")
    if not np.allclose(np.log(gross), samples["log_return"], rtol=1e-10, atol=1e-12):
        raise ValueError("两列收益率不一致，请重新运行 cal_ar 和 cal_gr")

    # position 是数量；book_value 才是用于金额风险计算的市值。
    v0 = float(result["book_value"].iloc[-1] if position_value is None else position_value)
    rate = float(result["discount_rate"].iloc[-1] if discount_rate is None else discount_rate)
    growth = 1 + rate / 252
    if not np.isfinite(v0) or v0 <= 0:
        raise ValueError("position_value 必须为有限正数")
    if not np.isfinite(growth) or growth <= 0:
        raise ValueError("日增长因子必须为有限正数")

    parameters = {
        "normal": (gross.mean(), gross.std(ddof=1)),
        "lognormal": (samples["log_return"].mean(), samples["log_return"].std(ddof=1)),
    }
    # 情景盈亏 X = a*G - b。统一施加到当前市值，非直接拟合历史金额盈亏。
    coefficients = {
        "pnl": (v0, v0),
        "pvpnl": (v0 / growth, v0),
        "fvpnl": (v0, v0 * growth),
    }
'''
var = '''def cal_var(df, confidence=0.95, position_value=None, discount_rate=None):
    """三种一天 P&L 的正态 / 对数正态 VaR，损失为正。

    先运行 cal_ar 和 cal_gr。默认使用最后一期市值、利率。
    利率为按 252 个交易日计息的名义年利率。
    """
''' + common + '''
    z = norm.ppf(1 - confidence)
    rows = []
    for model, (mu, sigma) in parameters.items():
        quantile = mu + sigma * z
        if model == "lognormal":
            quantile = np.exp(quantile)
        for pnl_type, (a, b) in coefficients.items():
            rows.append({
                "pnl_type": pnl_type, "model": model,
                "confidence": confidence, "VaR": b - a * quantile,
                "position_value": v0, "discount_rate": rate,
                "observations": len(samples),
            })
    return pd.DataFrame(rows)
'''
es = '''def cal_es(df, confidence=0.95, position_value=None, discount_rate=None):
    """三种一天 P&L 的 ES；对收益左尾数值积分，未使用 ES 闭式公式。"""
''' + common + '''
    tail_probability = 1 - confidence
    z_cutoff = norm.ppf(tail_probability)
    rows = []
    for model, (mu, sigma) in parameters.items():
        for pnl_type, (a, b) in coefficients.items():
            def integrand(z):
                gross_return = mu + sigma * z
                if model == "lognormal":
                    gross_return = np.exp(gross_return)
                return (b - a * gross_return) * norm.pdf(z)

            integral, error = quad(
                integrand, -np.inf, z_cutoff,
                epsabs=1e-8, epsrel=1e-8, limit=200,
            )
            rows.append({
                "pnl_type": pnl_type, "model": model,
                "confidence": confidence, "ES": integral / tail_probability,
                "integration_error": error / tail_probability,
            })
    return pd.DataFrame(rows)
'''
usage = '''# 使用最后一期 book_value 和 discount_rate，也可以显式传入覆盖值。
confidence = 0.99
var_result = cal_var(df, confidence=confidence)
es_result = cal_es(df, confidence=confidence)
risk_result = var_result.merge(
    es_result,
    on=["pnl_type", "model", "confidence"],
    validate="one_to_one",
)
risk_result.round(6)
'''
for index, text in [(6, var), (7, es), (8, usage)]:
    n['cells'][index]['source'] = text.splitlines(keepends=True)

# Updated source invalidates old outputs; retain all other notebook structure.
for cell in n['cells']:
    if cell['cell_type'] == 'code':
        cell['outputs'] = []
        cell['execution_count'] = None
n['cells'][5]['source'] = [
    '# 1.2 Estimating Historical Simulation & parametric VaR\n',
    '\n',
    '以下为参数法 VaR / ES。复用 `prepare_data`、`arithmetic_return` 和 `log_return`。\n',
    '正态模型拟合总收益倍数 G，对数正态模型拟合 ln(G)；P&L 本身不假设为对数正态。\n',
    '历史收益统一施加到当前头寸市值，默认采用最后一期 book_value 和 discount_rate。\n',
    '一天持有期，按名义年利率 /252 计息；要求每个交易日一行且无缺失。\n',
    'interim_payments 当前是随机模拟现金流，因此结果用于练习，不代表真实股票风险。\n',
    '复权价格乘以固定 position 构造的是练习用市值序列，非原始成交价下实际账户市值。\n',
    'ES 使用 scipy.integrate.quad 数值积分；integration_error 为积分误差估计，不是统计标准误。\n',
]
p.write_text(json.dumps(n, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print('Updated:', p)
print('Backup:', backup)

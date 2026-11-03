"""第12–18章网页调用边界。公式只调用service；结构化参数只接受JSON数据。

利率/波动率为小数，时间为年；FRTB流动性期限为天。每个操作提供可替换的
列映射，第二张表/矩阵使用显式JSON参数，不执行用户表达式。
"""
from copy import deepcopy
import math

import numpy as np
import pandas as pd

from service import load_chapter
from service.catalog import MANIFEST


def number(name, label, default, minimum=-1e9, maximum=1e9):
    return dict(name=name, label=label, type='number', default=default, min=minimum, max=maximum)


def column(name, label, default):
    return dict(name=name, label=label, type='column', default=default)


def columns(name, label, default):
    return dict(name=name, label=label, type='columns', default=default)


def choice(name, label, values, default):
    return dict(name=name, label=label, type='select', default=default,
                options=[dict(value=v, label=l) for v, l in values])


def structured(name, label, default):
    return dict(name=name, label=label, type='json', default=default)


DT = number('dt', '时间步长（年）', .5, .00001, 30)
RATE = number('initial_rate', '初始短率（小数）', .03, -1, 2)
VOL = number('volatility', '波动率（小数/√年）', .01, 0, 2)
SPEED = number('speed', '均值回复速度', .2, .0001, 10)
MEAN = number('long_run_mean', '长期均值（小数）', .05, .00001, 2)
SHOCKS = columns('target_columns', '冲击路径列（每行一个时间步）', ['path_a', 'path_b'])
MATURITY = column('maturity_column', '期限列（年）', 'maturity')
SIGN = choice('option_sign', '期权方向', [('call', '看涨'), ('put', '看跌')], 'call')

_OPS = []
_HANDLERS = {}
_EXAMPLES = {}


def register(chapter, slug, title, formula, parameters, frame, description, assumptions=()):
    """显式注册白名单；frame工厂只生成带说明的可复现演示数据。"""
    def decorator(function):
        identifier = f'ch{chapter}_{slug}'
        example_id = identifier + '_example'
        _OPS.append(dict(id=identifier, chapter=chapter, workspace=identifier, name=title,
                         description=description, formula=formula, pages=MANIFEST[str(chapter)]['pages'],
                         assumptions=['输入利率、波动率均为小数；时间为年（流动性期限除外）。', *assumptions],
                         parameters=parameters, example_id=example_id))
        _HANDLERS[identifier] = function
        _EXAMPLES[example_id] = (chapter, title, frame)
        return function
    return decorator


def operations():
    return deepcopy(_OPS)


def examples():
    return [dict(id=key, chapter=value[0], name=f'第{value[0]}章 · {value[1]}',
                 description='按教材计算口径构造的可复现演示数据；不是原始行情。')
            for key, value in _EXAMPLES.items()]


def example_frame(identifier):
    chapter, title, factory = _EXAMPLES[identifier]
    frame = factory()
    return frame, dict(chapter=chapter, example_id=identifier, source=f'{title}：构造示例，非原始行情',
                       fields={str(c): dict(kind='other', unit='other', sign='none') for c in frame})


def scalar(value):
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None if math.isnan(value) else str(value)
    return value


def result(value, name='计算结果', notes=()):
    """统一展示纯计算返回值，保留索引含义和自然缺值。"""
    out = dict(metrics=[], tables=[], charts=[], notes=list(notes))
    if isinstance(value, pd.Series):
        out['metrics'] = [dict(name=str(k), value=scalar(v)) for k, v in value.items()]
    elif isinstance(value, pd.DataFrame):
        frame = value.copy()
        frame.columns = [str(c) for c in frame.columns]
        index_label = 'row_index'
        while index_label in frame.columns:
            index_label = '_' + index_label
        frame.insert(0, index_label, [scalar(v) for v in frame.index])
        out['tables'] = [dict(name=name, columns=list(frame), rows=[{k: scalar(v) for k, v in r.items()} for r in frame.to_dict('records')])]
        numeric = list(value.select_dtypes(include='number').columns)
        if numeric:
            positions = np.unique(np.linspace(0, len(value)-1, min(1000, len(value))).astype(int)) if len(value) else []
            out['charts'] = [dict(title=name, x_label='行序号 / 时间索引', series=[dict(name=str(c), type='line', data=[[scalar(value.index[i]), scalar(value[c].iloc[i])] for i in positions]) for c in numeric[:12]])]
            if len(value) > 1000 or len(numeric) > 12:
                out['notes'].append('图表最多展示12列、1000个等距点；结果表保留完整数据。')
    else:
        out['metrics'] = [dict(name=name, value=scalar(value))]
    out['notes'].append('自然缺值保留为空，不填零；金额结果沿用输入币种。')
    return out


def combine(*items):
    return {key: sum((item[key] for item in items), []) for key in ('metrics', 'tables', 'charts', 'notes')}


def numeric(frame, selected, positive=False):
    names = [selected] if isinstance(selected, str) else selected
    if not names or len(set(names)) != len(names) or any(c not in frame for c in names):
        raise ValueError('请选择存在且不重复的输入列')
    values = frame[names]
    if any(not pd.api.types.is_numeric_dtype(t) for t in values.dtypes) or not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError('输入列必须全部为有限数值；请显式准备缺失数据')
    if positive and (values <= 0).any().any():
        raise ValueError('此输入必须严格大于零')
    return values


def matrix(value, name, size=None, correlation=False):
    try:
        arr = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name}须为二维数值数组') from exc
    if arr.ndim != 2 or arr.size == 0 or arr.size > 100000 or not np.isfinite(arr).all() or (size is not None and arr.shape != size):
        raise ValueError(f'{name}维度不匹配或包含非有限数值')
    if correlation and (not np.allclose(arr, arr.T) or not np.allclose(np.diag(arr), 1) or np.linalg.eigvalsh(arr).min() < -1e-10):
        raise ValueError('相关矩阵须对称、半正定且对角为1')
    return pd.DataFrame(arr)


def probabilities(values):
    if (values < 0).any() or not np.isclose(values.sum(), 1):
        raise ValueError('状态概率必须非负且合计为1')


def calculate(df, metadata, request):
    identifier = request['operation']
    operation = next(item for item in _OPS if item['id'] == identifier)
    supplied = request.get('parameters', {})
    if not isinstance(supplied, dict):
        raise ValueError('参数须为对象')
    unknown = set(supplied) - {item['name'] for item in operation['parameters']}
    if unknown:
        raise ValueError('未知参数：' + ', '.join(sorted(unknown)))
    params = {item['name']: deepcopy(item.get('default')) for item in operation['parameters']}
    params.update(supplied)
    for item in operation['parameters']:
        value = params[item['name']]
        if item['type'] == 'number':
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not item['min'] <= value <= item['max']:
                raise ValueError(f"{item['label']}必须在{item['min']}至{item['max']}之间")
        if item['type'] == 'select' and value not in [option['value'] for option in item['options']]:
            raise ValueError(f"{item['label']}选项无效")
    if len(df) == 0 or len(df) > 10000:
        raise ValueError('此章节单次计算需1至10000行输入')
    return _HANDLERS[identifier](df.copy(), params)


@register(12, 'probability', '风险中性概率', 'p = [P(1+rΔt)−Vd]/(Vu−Vd)',
          [number('price', '当前价格', 98), number('up_value', '上状态价值', 105), number('down_value', '下状态价值', 95), number('rate', '短率（小数）', .02), DT],
          lambda: pd.DataFrame({'reference': [1]}), '单期简单复利风险中性概率；数据集作为计算记录输入快照。')
def probability(df, p):
    if p['up_value'] == p['down_value']:
        raise ValueError('两个状态价值不能相同')
    value = load_chapter(12).risk_neutral_probability(**p)
    if not 0 <= value <= 1:
        raise ValueError('价格不满足无套利区间，风险中性概率超出[0,1]')
    return result(value, '向上概率')


@register(12, 'replication', '复制组合', 'A x = b；P = xᵀp',
          [columns('payoff_columns', '交易资产状态支付列', ['asset_a', 'asset_b']), column('target_column', '待复制支付列', 'target'), structured('prices', '资产当前价格数组（顺序同支付列）', [98, 1])],
          lambda: pd.DataFrame({'asset_a': [105., 95.], 'asset_b': [1.01, 1.01], 'target': [5., 0.]}), '满秩方阵状态支付求复制头寸与价格。')
def replication(df, p):
    a = numeric(df, p['payoff_columns'])
    numeric(df, p['target_column'])
    if a.shape[0] != a.shape[1] or np.linalg.matrix_rank(a) != len(a):
        raise ValueError('交易资产支付矩阵须为满秩方阵')
    prices = matrix([p['prices']], '价格数组', (1, len(a))).T
    prices.columns = ['price']
    return result(load_chapter(12).replicating_portfolio(df, p['payoff_columns'], p['target_column'], prices, 'price'))


@register(12, 'tree', '二叉利率树 / OAS / 校准', 'Vt = [(1−p)Vd+pVu]/[1+(r+OAS)Δt]',
          [column('target_column', '终端支付列（n+1行）', 'payoff'), structured('rates', '短率树 n×n 数组；下三角无效位填null', [[.02, .015], [None, .025]]),
           structured('probabilities', '向上概率树 n×n；无效位填null', [[.8, .5], [None, .5]]), DT,
           choice('mode', '计算方式', [('price', '价格与回溯'), ('oas', '反解OAS'), ('calibrate', '校准概率')], 'price'),
           number('spread', '贴现利差OAS（小数）', 0, -.5, 1), number('market_price', 'OAS目标价格', 980, 0, 1e9),
           structured('bracket', 'OAS求根区间', [-.01, .1]), structured('discounts', '校准零息折现因子（Δt至nΔt）', [1/1.01, .980347]),
           structured('cashflows', '各时间节点附加现金流 n×n；空数组表示无', []),
           choice('exercise', '提前行权规则', [('none', '无'), ('put', '节点价值不低于行权价'), ('call', '节点价值不高于赎回价')], 'none'), number('exercise_price', '提前行权/赎回价格', 990)],
          lambda: pd.DataFrame({'payoff': [1000., 1000., 1000.]}), '行表示累计向上次数，列表示时间步；回溯表保留树结构自然缺值。')
def tree(df, p):
    service = load_chapter(12)
    numeric(df, p['target_column'])
    n = len(df)-1
    if not 1 <= n <= 100:
        raise ValueError('利率树需1至100步，终端支付行数=步数+1')
    rates = np.asarray(p['rates'], dtype=float)
    probs = np.asarray(p['probabilities'], dtype=float)
    if rates.shape != (n, n) or probs.shape != (n, n):
        raise ValueError('利率和概率树须为(终端行数−1)阶方阵')
    valid = np.triu_indices(n)
    if not np.isfinite(rates[valid]).all() or not np.isfinite(probs[valid]).all() or ((probs[valid] < 0) | (probs[valid] > 1)).any():
        raise ValueError('有效树节点必须有限且概率在[0,1]')
    rates, probs = pd.DataFrame(rates), pd.DataFrame(probs)
    model = service.BinomialRateTree(rates, probs, p['dt'])
    if p['mode'] == 'calibrate':
        discounts = matrix([p['discounts']], '折现因子', (1, n)).T
        if (discounts <= 0).any().any() or not np.isclose(discounts.iloc[0, 0], 1/(1+rates.iloc[0, 0]*p['dt'])):
            raise ValueError('折现因子须为正，首期必须与初始短率匹配')
        model = service.BinomialRateTree.calibrate_probabilities(rates, discounts, 0, p['dt'])
    kwargs = dict(spread=p['spread'])
    if p['cashflows']:
        kwargs['cashflows'] = matrix(p['cashflows'], '现金流树', (n, n))
    if p['exercise'] != 'none':
        method = np.maximum if p['exercise'] == 'put' else np.minimum
        kwargs['exercise'] = lambda t, v: method(v, p['exercise_price'])
    if p['mode'] == 'oas':
        bracket = matrix([p['bracket']], 'OAS区间', (1, 2)).iloc[0].to_list()
        if bracket[0] >= bracket[1] or np.min(1+(rates.to_numpy()[valid]+bracket[0])*p['dt']) <= 0:
            raise ValueError('OAS区间须递增且贴现分母为正')
        kwargs.pop('spread')
        spread = model.option_adjusted_spread(df, p['target_column'], p['market_price'], bracket, **kwargs)
        kwargs['spread'] = spread
    if np.min(1+(rates.to_numpy()[valid]+kwargs['spread'])*p['dt']) <= 0:
        raise ValueError('贴现分母须严格为正')
    rolled = model.rollback(df, p['target_column'], **kwargs)
    return combine(result(rolled, '节点价值'), result(pd.Series({'price': rolled.iloc[0, 0], 'spread': kwargs['spread']})), result(pd.DataFrame(model.probabilities), '节点向上概率'))


@register(12, 'cmt', 'CMT现金流', 'CF = N Δt (y−k)', [column('yield_column', '参考收益率列', 'yield'), number('notional', '名义本金', 1e6), number('fixed_rate', '固定利率', .02), number('accrual', '计息年数', .5, .00001, 30)], lambda: pd.DataFrame({'yield': [.025, .015]}), '逐行结算CMT现金流。')
def cmt(df, p):
    numeric(df, p['yield_column'])
    return result(load_chapter(12).cmt_payments(df, **p))


@register(12, 'attribution', '债券P&L顺序归因', '总P&L = carry/roll + curve + spread', [number('start_price', '期初价格', 100), number('rolled_price', '滚动后价格', 101), number('curve_price', '曲线变化后价格', 99), number('final_price', '期末价格', 98), number('payments', '现金流', 2)], lambda: pd.DataFrame({'reference': [1]}), '沿用户给定重估路径进行归因；数据集为记录快照。')
def attribution(df, p):
    return result(load_chapter(12).pnl_attribution(**p))


@register(13, 'discount', '预期折现因子', 'E[D] = Σ pᵢ/(1+rᵢΔt)', [column('rate_column', '状态利率列', 'rate'), column('probability_column', '状态概率列', 'probability'), DT], lambda: pd.DataFrame({'rate': [.05, .13], 'probability': [.5, .5]}), '离散状态概率加权；简单复利。')
def expected_discount(df, p):
    numeric(df, [p['rate_column'], p['probability_column']])
    probabilities(df[p['probability_column']])
    if (1+df[p['rate_column']]*p['dt'] <= 0).any():
        raise ValueError('简单复利贴现分母须为正')
    return result(load_chapter(13).expected_discount_factor(df, **p), '预期折现因子')


@register(13, 'forward', '折现曲线远期利率', 'f = log(Dstart/Dend)/ΔT', [column('start_discount_column', '起始折现因子列', 'start'), column('end_discount_column', '结束折现因子列', 'end'), column('tenor_column', '远期间隔列（年）', 'tenor')], lambda: pd.DataFrame({'start': [np.exp(-.03)], 'end': [np.exp(-.07)], 'tenor': [1.]}), '连续复利远期利率。')
def forward(df, p):
    numeric(df, list(p.values()), positive=True)
    return result(load_chapter(13).forward_from_discount_factors(df, **p))


@register(13, 'decomposition', '远期利率分解 / 预期债券收益', 'f = r + Dμ + Dλ − Cσ²/2；E[R] = r + Dλ', [column('duration_column', '久期列', 'duration'), column('convexity_column', '凸性列', 'convexity'), number('short_rate', '短率', .01), number('physical_drift', '真实漂移', .002), number('risk_premium', '每单位久期风险溢价', .001), VOL], lambda: pd.DataFrame({'duration': [1., 3., 5.], 'convexity': [2., 12., 30.]}), '风险溢价不是Sharpe比率；返回分量与债券预期收益。')
def decomposition(df, p):
    numeric(df, [p['duration_column'], p['convexity_column']])
    s = load_chapter(13)
    frame = s.forward_decomposition(df, **p)
    return result(s.expected_bond_return(frame, p['duration_column'], p['short_rate'], p['risk_premium']))


def shock_frame(uniform=False):
    rng = np.random.default_rng(42)
    return pd.DataFrame(rng.uniform(.001, .999, (40, 2)) if uniform else rng.normal(size=(40, 2)), columns=['path_a', 'path_b'])


def drift_parameters():
    return [RATE, VOL, SPEED, MEAN, number('drift_rate', '常数/时间函数漂移截距', .002, -.5, .5), number('drift_slope', '漂移时间斜率', 0, -.5, .5),
            choice('model', '短率模型', [('gaussian', '常漂移高斯'), ('holee', 'Ho-Lee：线性漂移'), ('holee_curve', 'Ho-Lee：线性远期导数'), ('vasicek', 'Vasicek')], 'vasicek')]


def short_model(p):
    s = load_chapter(14)
    if p['model'] == 'gaussian':
        return s.GaussianDrift(p['drift_rate'], p['volatility'])
    if p['model'] == 'vasicek':
        return s.Vasicek(p['speed'], p['long_run_mean'], p['volatility'])
    function = lambda t: p['drift_rate']+p['drift_slope']*t
    if p['model'] == 'holee_curve':
        return s.HoLee.from_forward_derivative(function, p['volatility'])
    return s.HoLee(function, p['volatility'])


@register(14, 'simulation', '短率路径模拟', 'dr = μ(t,r)dt + σdW', [*drift_parameters(), SHOCKS, DT, choice('method', 'Vasicek离散法', [('exact', '精确转换'), ('euler', 'Euler')], 'exact')], shock_frame, '使用输入标准正态冲击，每列一条路径；Ho-Lee通过两个系数定义线性函数。')
def short_simulation(df, p):
    shocks = numeric(df, p['target_columns'])
    if shocks.size > 100000:
        raise ValueError('路径模拟最多100000个冲击值')
    model = short_model(p)
    method = model.simulate_exact if p['model'] == 'vasicek' and p['method'] == 'exact' else model.simulate
    return result(method(shocks, p['initial_rate'], p['dt']), '短率路径')


@register(14, 'curve', '短率模型期限结构', 'P(0,T)=E[e^(−∫r dt)]', [*drift_parameters(), MATURITY], lambda: pd.DataFrame({'maturity': [.5, 1., 2., 5., 10.]}), '折现因子及Vasicek远期/矩；参数均为风险中性口径。')
def short_curve(df, p):
    numeric(df, p['maturity_column'], positive=True)
    model = short_model(p)
    out = df.copy()
    out['discount'] = [model.discount(p['initial_rate'], t) for t in out[p['maturity_column']]]
    if p['model'] == 'vasicek':
        out['forward'] = [model.forward(p['initial_rate'], t) for t in out[p['maturity_column']]]
        moments = [model.moments(p['initial_rate'], t) for t in out[p['maturity_column']]]
        out['mean'] = [m['mean'] for m in moments]
        out['variance'] = [m['variance'] for m in moments]
    return result(out, '期限结构')


def volatility_parameters():
    return [RATE, number('volatility', '波动率（小数/√年）', .1, .00001, 2), SPEED, MEAN,
            number('drift_rate', '高斯/对数漂移截距', .002, -.5, .5), number('drift_slope', '高斯漂移时间斜率', 0, -.5, .5), number('volatility_decay', '波动率指数衰减速度', .025, 0, 10),
            choice('model', '波动率模型', [('gaussian', '时间依赖高斯'), ('cir', 'CIR精确转换（输入U）'), ('courtadon', 'Courtadon Euler'), ('lognormal', '对数正态利率'), ('bk', 'Black-Karasinski精确转换'), ('time_bk', '时间依赖BK（指数函数）')], 'lognormal')]


def volatility_model(p):
    s = load_chapter(15)
    models = {
        'gaussian': lambda: s.TimeDependentGaussian(lambda t: p['drift_rate']+p['drift_slope']*t, lambda t: p['volatility']*np.exp(-p['volatility_decay']*t)),
        'cir': lambda: s.CIR(p['speed'], p['long_run_mean'], p['volatility']),
        'courtadon': lambda: s.Courtadon(p['speed'], p['long_run_mean'], p['volatility']),
        'lognormal': lambda: s.LognormalRate(p['drift_rate'], p['volatility']),
        'bk': lambda: s.BlackKarasinski(p['speed'], p['long_run_mean'], p['volatility']),
        'time_bk': lambda: s.TimeDependentBlackKarasinski(lambda t: p['speed'], lambda t: p['long_run_mean']*np.exp(p['drift_rate']*t), lambda t: p['volatility']*np.exp(-p['volatility_decay']*t)),
    }
    return models[p['model']]()


@register(15, 'simulation', '波动率模型路径比较', 'CIR: σ√r；Courtadon: σr；BK: d log(r)', [*volatility_parameters(), SHOCKS, DT], shock_frame, 'CIR选择时输入列必须为(0,1)均匀数；其他模型输入标准正态冲击。时间依赖BK：k常数、中心利率θ exp(漂移×t)、σ exp(−衰减×t)。')
def volatility_simulation(df, p):
    shocks = numeric(df, p['target_columns'])
    if shocks.size > 100000:
        raise ValueError('路径模拟最多100000个冲击值')
    if p['initial_rate'] <= 0 and p['model'] in {'cir', 'lognormal', 'bk', 'time_bk'}:
        raise ValueError('所选模型的初始利率须为正')
    model = volatility_model(p)
    if p['model'] == 'cir':
        if ((shocks <= 0) | (shocks >= 1)).any().any():
            raise ValueError('CIR精确转换要求(0,1)均匀数输入，请更换数据')
        out = model.simulate_uniforms(shocks, p['initial_rate'], p['dt'])
    else:
        out = model.simulate(shocks, p['initial_rate'], p['dt'])
    return result(out, '短率路径', ['Euler方法不自动截断负利率。'])


@register(15, 'analytics', '高斯 / CIR解析期限结构', 'P(0,T)=E[e^(−∫r dt)]', [*volatility_parameters(), MATURITY], lambda: pd.DataFrame({'maturity': [.5, 1., 2., 5.]}), '解析折现仅适用于时间依赖高斯和CIR；其他模型请用路径操作。')
def volatility_analytics(df, p):
    numeric(df, p['maturity_column'], positive=True)
    if p['model'] not in {'gaussian', 'cir'}:
        raise ValueError('解析期限结构请选择时间依赖高斯或CIR')
    if p['model'] == 'cir' and p['initial_rate'] < 0:
        raise ValueError('CIR初始利率不能为负')
    model = volatility_model(p)
    out = df.copy()
    out['discount'] = [model.discount(p['initial_rate'], t) for t in df[p['maturity_column']]]
    if p['model'] == 'gaussian':
        moments = [model.moments(p['initial_rate'], t) for t in df[p['maturity_column']]]
        out['mean'] = [m['mean'] for m in moments]
        out['variance'] = [m['variance'] for m in moments]
    return result(out, '解析期限结构')


# 解析操作默认选择有解析方法的模型；与路径操作共享参数角色。
_analytic_model = next(p for p in _OPS[-1]['parameters'] if p['name'] == 'model')
_analytic_model['default'] = 'gaussian'
_analytic_model['options'] = [item for item in _analytic_model['options'] if item['value'] in {'gaussian', 'cir'}]


@register(15, 'tree', '对数正态短率树', 'r(i,j)=r₀ exp(μiΔt+(2j−i)σ√Δt)', [RATE, VOL, number('log_drift', '对数漂移', .01), number('n_steps', '树步数（整数）', 3, 1, 100), DT], lambda: pd.DataFrame({'reference': [1]}), '常数参数重组树；数据集用作计算记录快照。')
def lognormal_tree(df, p):
    if p['n_steps'] != int(p['n_steps']) or p['initial_rate'] <= 0:
        raise ValueError('树步数必须为整数，初始利率须为正')
    return result(load_chapter(15).LognormalRate(p['log_drift'], p['volatility']).binomial_tree(p['initial_rate'], int(p['n_steps']), p['dt']), '短率节点')


def gauss_parameters():
    return [number('short_speed', '短端回复速度', 1.0547, .001, 3), number('medium_speed', '中端回复速度', .6358, .001, 3), number('long_speed', '长端回复速度', .0165, .001, 3),
            number('medium_volatility', '中端波动率', .01092, .00001, .1), number('long_volatility', '长端波动率', .00964, .00001, .1), number('correlation', '因子相关系数', .212, -.99, .99), number('long_run_mean', '长期均值μ', .10555, -.5, 1)]


def gauss(p):
    return load_chapter(16).GaussPlus(**{item['name']: p[item['name']] for item in gauss_parameters()})


def gauss_example():
    model = load_chapter(16).GaussPlus(1.0547, .6358, .0165, .01092, .00964, .212, .10555)
    state = pd.DataFrame([[.02, .04, .06]], columns=['r', 'm', 'l'])
    tenors = [.5, 1., 3., 5., 7., 15., 20.]
    coeff = np.array([model.regression_loadings(t, [2, 10]) for t in tenors])
    return pd.DataFrame({'maturity': tenors, 'yield': [-np.log(model.discount(state, t))/t for t in tenors],
                         'coefficient_a': coeff[:, 0], 'coefficient_b': coeff[:, 1], 'volatility': [model.yield_volatility(t) for t in tenors],
                         'short_rate': .02, 'reference_a': -np.log(model.discount(state, 2))/2, 'reference_b': -np.log(model.discount(state, 10))/10})


@register(16, 'curve', 'Gauss+期限结构与载荷', 'r → m → l → μ；y(T)=a(T)ᵀstate+b(T)', [*gauss_parameters(), MATURITY, structured('state', '当前状态[r,m,l]', [.02, .04, .06]), structured('reference_maturities', '两个参考期限（年）', [2., 10.]), number('horizon', '状态矩预测期限（年）', 1, .001, 30)], gauss_example, '精确线性高斯转移；输出折现、收益率载荷、波动率、回归载荷和状态矩。')
def gauss_curve(df, p):
    numeric(df, p['maturity_column'], positive=True)
    if len(df) > 500:
        raise ValueError('Gauss+期限结构单次最多500个期限')
    state = matrix([p['state']], '状态向量', (1, 3)); state.columns = ['r', 'm', 'l']
    refs = _references(p)
    model = gauss(p)
    rows = []
    for t in df[p['maturity_column']]:
        loadings, intercept = model.yield_loadings(t)
        regression = model.regression_loadings(t, refs)
        rows.append(dict(maturity=t, discount=model.discount(state, t), loading_r=loadings[0], loading_m=loadings[1], loading_l=loadings[2], intercept=intercept, volatility=model.yield_volatility(t), coefficient_a=regression[0], coefficient_b=regression[1]))
    mean, covariance = model.moments(state, p['horizon'])
    return combine(result(pd.DataFrame(rows), 'Gauss+期限结构'), result(mean.rename(lambda c: '期望_'+c)), result(covariance, '状态协方差'))


def _references(p):
    refs = matrix([p['reference_maturities']], '参考期限', (1, 2)).iloc[0].to_list()
    if min(refs) <= 0 or refs[0] == refs[1]:
        raise ValueError('两个参考期限必须为不同正数')
    return refs


@register(16, 'calibration', 'Gauss+分阶段校准', '回归载荷→速度；期限波动→σ,ρ；曲线→μ/state', [*gauss_parameters(), MATURITY,
          choice('mode', '校准阶段', [('speeds', '回复速度'), ('volatilities', '波动率与相关系数'), ('mean', '长期均值μ'), ('state', '当前状态')], 'state'),
          columns('coefficient_columns', '两个回归系数列', ['coefficient_a', 'coefficient_b']), column('volatility_column', '期限波动率列', 'volatility'), column('yield_column', '连续复利零息收益率列', 'yield'), column('short_rate_column', '同日短率列', 'short_rate'), columns('reference_yield_columns', '两个参考收益率列', ['reference_a', 'reference_b']), structured('reference_maturities', '两个参考期限（年）', [2., 10.])], gauss_example, '当前参数作为初始值或已知前阶段参数；速度边界[.001,3]，波动率[.00001,.1]，相关系数[-.99,.99]。')
def gauss_calibration(df, p):
    numeric(df, p['maturity_column'], positive=True)
    if not 3 <= len(df) <= 50:
        raise ValueError('校准要求3至50个期限观测')
    model = gauss(p); refs = _references(p); service = load_chapter(16)
    speeds = [p['short_speed'], p['medium_speed'], p['long_speed']]
    if p['mode'] == 'speeds':
        numeric(df, p['coefficient_columns'])
        if len(p['coefficient_columns']) != 2:
            raise ValueError('需要两个回归系数列')
        fit = service.GaussPlus.fit_speeds(df, p['maturity_column'], p['coefficient_columns'], refs, speeds, ([.001]*3, [3.]*3))
        names = ['short_speed', 'medium_speed', 'long_speed']
    elif p['mode'] == 'volatilities':
        numeric(df, p['volatility_column'], positive=True)
        fit = service.GaussPlus.fit_volatilities(df, p['maturity_column'], p['volatility_column'], speeds, [p['medium_volatility'], p['long_volatility'], p['correlation']], ([.00001, .00001, -.99], [.1, .1, .99]))
        names = ['medium_volatility', 'long_volatility', 'correlation']
    elif p['mode'] == 'mean':
        numeric(df, [p['yield_column'], p['short_rate_column'], *p['reference_yield_columns']])
        if len(p['reference_yield_columns']) != 2:
            raise ValueError('需要两个参考收益率列')
        return result(model.fit_long_run_mean(df, p['maturity_column'], p['yield_column'], p['short_rate_column'], p['reference_yield_columns'], refs), '长期均值μ')
    else:
        numeric(df, p['yield_column'])
        if df[p['maturity_column']].nunique() < 3:
            raise ValueError('状态拟合需要至少3个不同期限')
        return result(model.fit_state(df, p['maturity_column'], p['yield_column']), '拟合状态')
    return result(pd.Series({**dict(zip(names, fit.x)), 'success': str(fit.success), 'cost': fit.cost, 'evaluations': fit.nfev}), notes=[str(fit.message)])


@register(16, 'hedge', 'Gauss+三因子对冲', 'Hᵀq = −target', [columns('target_columns', '三状态金额敏感度列（顺序r,m,l）', ['r', 'm', 'l']), structured('target', '目标三因子金额敏感度', [10., 20., 30.])], lambda: pd.DataFrame(np.eye(3), columns=['r', 'm', 'l']), '每行一个对冲工具，三行三列满秩敏感度；输出对冲数量。')
def gauss_hedge(df, p):
    hedges = numeric(df, p['target_columns'])
    if hedges.shape != (3, 3) or np.linalg.matrix_rank(hedges) != 3:
        raise ValueError('三因子对冲需要3×3满秩敏感度矩阵')
    target = matrix([p['target']], '目标敏感度', (1, 3))
    model = load_chapter(16).GaussPlus(1., .5, .1, .01, .01, 0., .03)
    return result(model.hedge_positions(target, hedges).rename(lambda i: f'hedge_{i}'))


@register(16, 'half_life', 'Vasicek半衰期', 't½ = log(2)/k', [SPEED], lambda: pd.DataFrame({'reference': [1]}), '均值回复半衰期，单位年。')
def half_life(df, p):
    return result(load_chapter(16).vasicek_half_life(p['speed']), '半衰期（年）')


def option_parameters():
    return [number('spot', '标的现价', 100, .00001, 1e9), number('rate', '连续复利无风险利率', .03, -1, 2), number('dividend_yield', '股息率 / 外币利率', .01, -1, 2), SIGN]


def option_example():
    s = load_chapter(17).EuropeanOption(100, .03, .01)
    frame = pd.DataFrame({'strike': [90., 100., 110.], 'maturity': [1., 1., 1.], 'volatility': [.22, .2, .21]})
    return s.quotes(frame, 'strike', 'maturity', 'volatility')


@register(17, 'options', '欧式期权报价 / Greeks / 隐含波动率', 'BSM报价；σimp解 Price(σ)=市场价格', [*option_parameters(), column('strike_column', '执行价列', 'strike'), MATURITY, column('volatility_column', '波动率列', 'volatility'), column('price_column', '市场价格列（反解使用）', 'price'), choice('mode', '报价方式', [('price', '已知波动率报价'), ('implied', '反解隐含波动率')], 'price'), structured('bracket', '隐含波动率求根区间', [.001, 2.])], option_example, '输出价格、delta/gamma/vega；vega对应波动率变动1.0。')
def option_quotes(df, p):
    s = load_chapter(17); model = s.EuropeanOption(p['spot'], p['rate'], p['dividend_yield'])
    sign = 1 if p['option_sign'] == 'call' else -1
    numeric(df, [p['strike_column'], p['maturity_column']], positive=True)
    if p['mode'] == 'implied':
        if len(df) > 1000:
            raise ValueError('单次隐含波动率反解最多1000条报价')
        numeric(df, p['price_column'], positive=True)
        bracket = matrix([p['bracket']], '波动率区间', (1, 2)).iloc[0].to_list()
        if not 0 < bracket[0] < bracket[1]:
            raise ValueError('波动率区间须为递增正数')
        df['implied_volatility'] = [model.implied_volatility(row[p['price_column']], row[p['strike_column']], row[p['maturity_column']], bracket, sign) for _, row in df.iterrows()]
        vol_column = 'implied_volatility'
    else:
        numeric(df, p['volatility_column'], positive=True)
        vol_column = p['volatility_column']
    out = model.quotes(df, p['strike_column'], p['maturity_column'], vol_column, sign)
    greeks = pd.DataFrame([model.greeks(row[p['strike_column']], row[p['maturity_column']], row[vol_column], sign) for _, row in out.iterrows()], index=out.index)
    return result(pd.concat([out, greeks], axis=1), '期权报价及Greeks')


@register(17, 'surface', '波动率曲面插值', '矩形网格双线性插值 σ(T,m)', [MATURITY, column('moneyness_column', '价内外程度列', 'moneyness'), structured('maturities', '网格期限（年，递增）', [.5, 1., 2.]), structured('moneyness', '网格价内外程度（递增）', [.9, 1., 1.1]), structured('grid', '波动率矩阵（行期限/列价内外，小数）', [[.18, .16, .19], [.19, .17, .2], [.2, .18, .21]])], lambda: pd.DataFrame({'maturity': [.75, 1.5], 'moneyness': [.95, 1.05]}), '完整矩形网格，禁止隐式外推；曲面按期限切片显示。')
def surface(df, p):
    numeric(df, [p['maturity_column'], p['moneyness_column']], positive=True)
    ts = matrix([p['maturities']], '网格期限').iloc[0].to_numpy()
    ms = matrix([p['moneyness']], '网格价内外程度').iloc[0].to_numpy()
    if len(ts) < 2 or len(ms) < 2 or (np.diff(ts) <= 0).any() or (np.diff(ms) <= 0).any() or min(ts) <= 0 or min(ms) <= 0:
        raise ValueError('每条网格轴至少两个递增正数')
    grid = matrix(p['grid'], '波动率网格', (len(ts), len(ms)))
    if (grid <= 0).any().any():
        raise ValueError('波动率网格须为正')
    grid.index, grid.columns = ts, ms
    queries = df[[p['maturity_column'], p['moneyness_column']]].to_numpy()
    if ((queries < [ts[0], ms[0]]) | (queries > [ts[-1], ms[-1]])).any():
        raise ValueError('查询点必须位于网格内')
    out = result(load_chapter(17).VolatilitySurface(grid).evaluate(df, p['maturity_column'], p['moneyness_column']), '插值查询')
    out['charts'] = [dict(title='波动率微笑期限切片', x_label='价内外程度', y_label='波动率（小数）', series=[dict(name=f'{t:g}年', type='line', data=[[float(m), float(v)] for m, v in zip(ms, grid.loc[t])]) for t in ts])]
    return out


@register(17, 'density', '风险中性密度', 'f(K)=exp(rT) ∂²C/∂K²', [column('strike_column', '执行价列（严格递增）', 'strike'), column('call_price_column', '同一期限看涨期权价格列', 'call_price'), number('rate', '连续复利无风险利率', .03), number('maturity', '统一期限（年）', 1, .00001, 100)], lambda: pd.DataFrame({'strike': np.linspace(60, 140, 81), 'call_price': load_chapter(17).EuropeanOption(100, .03).price(np.linspace(60, 140, 81), 1, .2)}), '只返回内部执行价点；不自动排序或修复违反凸性的报价。')
def density(df, p):
    numeric(df, [p['strike_column'], p['call_price_column']])
    if len(df) < 3 or (np.diff(df[p['strike_column']]) <= 0).any():
        raise ValueError('至少三个严格递增执行价')
    return result(load_chapter(17).risk_neutral_density(df, **p), '隐含风险中性密度', ['负密度提示输入报价不满足局部凸性；未裁剪。'])


@register(17, 'jump', '离散跳跃状态期权', 'V=e^(−rT)Σpᵢ max(sign(Sᵢ−K),0)', [column('terminal_column', '终端价格列', 'terminal'), column('probability_column', '风险中性概率列', 'probability'), number('strike', '执行价', 50, .0001, 1e9), number('rate', '连续复利利率', 0), number('maturity', '期限（年）', 1, .00001, 100), SIGN], lambda: pd.DataFrame({'terminal': [42., 58.], 'probability': [.5, .5]}), '用户输入风险中性离散状态概率。')
def jump(df, p):
    numeric(df, [p['terminal_column'], p['probability_column']])
    probabilities(df[p['probability_column']])
    p = {**p, 'option_sign': 1 if p['option_sign'] == 'call' else -1}
    return result(load_chapter(17).jump_mixture_price(df, **p), '期权价格')


@register(17, 'delta', '最小方差Delta', 'ΔMV=ΔBSM+Vega·dE[σ]/dS', [number('delta', 'BSM Delta', .5), number('vega', 'BSM Vega（波动率单位1）', 20), number('volatility_spot_slope', '预期波动率对现价斜率', -.001)], lambda: pd.DataFrame({'reference': [1]}), '标量Delta调整；数据集作为计算记录快照。')
def minimum_delta(df, p):
    return result(load_chapter(17).minimum_variance_delta(**p), '最小方差Delta')


@register(18, 'sensitivity', '敏感度资本与相关情景', 'K=√[(s⊙w)ᵀρ(s⊙w)]', [column('sensitivity_column', '金额敏感度列', 'sensitivity'), column('weight_column', '风险权重列（小数）', 'weight'), structured('correlation', '相关矩阵（行顺序同数据）', [[1., .5], [.5, 1.]]), structured('multipliers', '相关乘数场景', [.75, 1., 1.25])], lambda: pd.DataFrame({'sensitivity': [100., 80.], 'weight': [.2, .3]}), '教材口径的敏感度二次型平方根；不是完整现行监管规则引擎。')
def sensitivity(df, p):
    numeric(df, [p['sensitivity_column'], p['weight_column']])
    if len(df) > 300:
        raise ValueError('单次敏感度相关矩阵最多300个风险因子')
    correlation = matrix(p['correlation'], '相关矩阵', (len(df), len(df)), correlation=True)
    multipliers = matrix([p['multipliers']], '相关乘数').iloc[0].to_list()
    if not 1 <= len(multipliers) <= 20 or min(multipliers) < 0:
        raise ValueError('需1至20个非负相关乘数')
    s = load_chapter(18)
    base = s.sensitivity_charge(df, p['sensitivity_column'], p['weight_column'], correlation)
    scenarios = s.correlation_scenarios(df, p['sensitivity_column'], p['weight_column'], correlation, multipliers)
    if not np.isfinite(scenarios).all():
        raise ValueError('相关场景产生负二次型，请检查场景矩阵适用性')
    return combine(result(base, '基准敏感度资本'), result(scenarios.rename_axis('multiplier').reset_index(), '相关场景资本'))


@register(18, 'curvature', '曲率资本', 'max(Δ×shock−P&Lup,−Δ×shock−P&Ldown,0)', [column('delta_column', 'Delta列', 'delta'), column('shock_column', '冲击列', 'shock'), column('up_pnl_column', '向上重估P&L列', 'up'), column('down_pnl_column', '向下重估P&L列', 'down')], lambda: pd.DataFrame({'delta': [2., 2.], 'shock': [1., 1.], 'up': [1., 3.], 'down': [-3., -1.]}), '双向重估减去线性贡献，逐项输出。')
def curvature(df, p):
    numeric(df, list(p.values()))
    return result(load_chapter(18).curvature_charge(df, **p))


@register(18, 'default', '违约风险资本', 'K=exposure×LGD×RW', [column('exposure_column', '敞口列', 'exposure'), column('lgd_column', 'LGD列（小数）', 'lgd'), column('weight_column', '风险权重列（小数）', 'weight')], lambda: pd.DataFrame({'exposure': [100.], 'lgd': [.75], 'weight': [.03]}), '教材单项计算；净额与多空分组由输入数据准备完成。')
def default(df, p):
    numeric(df, list(p.values()))
    if ((df[p['lgd_column']] < 0) | (df[p['lgd_column']] > 1)).any():
        raise ValueError('LGD须在[0,1]')
    return result(load_chapter(18).default_charge(df, **p))


@register(18, 'residual', '残余风险附加', 'RRAO=Σnotional×weight', [column('notional_column', '名义本金列', 'notional'), column('weight_column', '附加权重列', 'weight')], lambda: pd.DataFrame({'notional': [100., 200.], 'weight': [.01, .01]}), '输入已识别的残余风险头寸。')
def residual(df, p):
    numeric(df, list(p.values()))
    return result(load_chapter(18).residual_add_on(df, **p), '残余风险附加')


@register(18, 'liquidity', '流动性调整ES', 'ESLH=√ΣESⱼ²(LHⱼ−LHⱼ₋₁)/base', [column('es_column', '嵌套因子子集ES列', 'es'), column('horizon_column', '递增流动性期限列（天）', 'horizon'), number('base_horizon', '基准期限（天）', 10, .0001, 10000)], lambda: pd.DataFrame({'es': [10., 8., 6., 4., 2.], 'horizon': [10., 20., 40., 60., 120.]}), '按输入顺序计算增量期限；不自动排序，ES须为对应嵌套因子子集。')
def liquidity(df, p):
    numeric(df, [p['es_column'], p['horizon_column']])
    if df[p['horizon_column']].iloc[0] <= 0 or (np.diff(df[p['horizon_column']]) <= 0).any():
        raise ValueError('流动性期限须为严格递增正数')
    return result(load_chapter(18).liquidity_adjusted_es(df, **p), '流动性调整ES')


@register(18, 'stress', '压力缩放ES', 'ESstress=ESstress,reduced×EScurrent,full/EScurrent,reduced', [number('stressed_reduced', '压力期精简因子ES', 20), number('current_full', '当前完整因子ES', 15), number('current_reduced', '当前精简因子ES', 10, .00001, 1e9)], lambda: pd.DataFrame({'reference': [1]}), '教材压力缩放；三个ES须同单位、同损失口径。')
def stress(df, p):
    return result(load_chapter(18).stress_scaled_es(**p), '压力缩放ES')


@register(18, 'weighted', '风险类别加权ES', 'ESweighted=w·EStotal+(1−w)ΣESpartial', [number('total_es', '全组合ES', 10), column('target_column', '各风险类别ES列', 'es'), number('aggregation_weight', '全组合权重', .5, 0, 1)], lambda: pd.DataFrame({'es': [8., 6.]}), '风险类别独立ES与全组合ES的教材加权公式。')
def weighted(df, p):
    numeric(df, p['target_column'])
    return result(load_chapter(18).weighted_es(partial_es=df, **p), '加权ES')


@register(18, 'capital', '内部模型资本', 'max(ESprev+NMRFprev,m×ESavg+NMRFavg)', [number('previous_es', '前日ES', 10), number('previous_nonmodellable', '前日不可建模风险', 2), number('average_es', '窗口平均ES', 9), number('average_nonmodellable', '窗口平均不可建模风险', 1), number('multiplier', '乘数', 1.5, 0, 100)], lambda: pd.DataFrame({'reference': [1]}), '平均窗口由调用者预先准备；复现教材公式，不判断现行合规。')
def capital(df, p):
    return result(load_chapter(18).capital_requirement(**p), '资本要求')


@register(18, 'pla', '教材P&L归因比率', 'mean(A−M)/std(A)；var(A−M)/var(A)', [column('actual_column', '实际P&L列', 'actual'), column('model_column', '模型P&L列', 'model')], lambda: pd.DataFrame({'actual': [-1., 2., 3., -2.], 'model': [-1., 2., 3., -2.]}), '教材旧PLA比率，不能用作现行监管合规判断。')
def pla(df, p):
    numeric(df, list(p.values()))
    if len(df) < 2 or df[p['actual_column']].std(ddof=1) <= 0:
        raise ValueError('实际P&L需至少两行且样本方差为正')
    return result(load_chapter(18).pnl_attribution_ratios(df, **p))

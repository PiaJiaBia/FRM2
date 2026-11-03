"""第8–11章网页调用边界；公式全部复用各章纯计算器。

主样本为已保存DataFrame，向量/矩阵参数按界面明确的列顺序转换为DataFrame。
不清洗、填补、排序或修改样本；缺失的滚动结果保留为JSON null。
"""
import math

import numpy as np
import pandas as pd
from scipy.stats import expon, norm, t

from service import load_chapter


def _p(name, label, kind, default, **extra):
    return dict(name=name, label=label, type=kind, default=default, **extra)


def _num(name, label, default, minimum=None, maximum=None):
    return _p(name, label, 'number', default, min=minimum, max=maximum)


def _sel(name, label, choices, default):
    return _p(name, label, 'select', default,
              options=[dict(value=v, label=k) for v, k in choices])


def _col(name='target_column', label='样本列', default='a'):
    return _p(name, label, 'column', default)


def _cols(default=None):
    return _p('target_columns', '样本列（顺序对应向量参数）', 'columns', default or ['a', 'b'])


def _json(name, label, default):
    return _p(name, label, 'json', default)


def operations():
    """显式业务操作目录；不反射执行用户提供的Python名称。"""
    definitions = [
        (8, 'moments', '相关矩阵与组合矩', '104–106,118', 'σP² = wᵀΣw', 'returns',
         '样本为同频率、对齐的小数收益率；权重可为有符号金额，结果量纲随权重。',
         [_cols(), _json('weights', '权重/金额数组（依所选列顺序）', [.6, .4]),
          _sel('method', '相关方法', [('pearson', 'Pearson'), ('spearman', 'Spearman（接口扩展）'), ('kendall', 'Kendall（接口扩展）')], 'pearson')]),
        (8, 'covariance_var', '协方差与组合VaR', '108–109', 'VaRα = zα √(h xᵀΣx)', 'positions',
         '每行一个资产；波动率为小数，敞口为金额，相关矩阵按样本行顺序。零均值IID平方根时间缩放。',
         [_col('volatility_column', '单期波动率列', 'sigma'), _col('exposure_column', '金额敞口列', 'amount'),
          _json('correlation', '相关矩阵（按资产行顺序）', [[1, .7], [.7, 1]]),
          _num('confidence_level', '置信水平', .99, .001, .999), _num('horizon', '持有期（样本期数）', 10, .0001, 10000)]),
        (8, 'implied', '隐含平均相关系数', '106–107', 'ρ̄ = (σP² − Σ(wiσi)²) / Σi≠j wiσi wjσj', 'positions',
         '各行波动率与组合波动率必须同频率、同小数口径；共同相关假设。',
         [_col('weight_column', '权重列', 'weight'), _col('volatility_column', '波动率列', 'sigma'),
          _num('portfolio_volatility', '组合波动率（小数）', .016, 0, 100)]),
        (8, 'joint_default', '违约指示联合概率', '113–114', 'P(A∩B) = pA pB + ρ √[pA(1−pA)pB(1−pB)]', 'probabilities',
         '使用样本前两行的违约概率；ρ是Bernoulli指示变量相关，不是copula潜变量相关。',
         [_col('probability_column', '违约概率列', 'probability'), _num('correlation', '违约指示相关系数', 0, -1, 1)]),
        (9, 'rolling', '滚动相关', '122–126', 'ρt = Corr(xt−w+1:t, yt−w+1:t)', 'returns',
         '按输入行顺序向后滚动；不自动排序。首window−1行保留空值。',
         [_col('first_column', '第一样本列', 'a'), _col('second_column', '第二样本列', 'b'), _num('window', '窗口观测数', 20, 2, 10000)]),
        (9, 'regimes', '平均与分状态相关', '122–123', 'ρ̄ = mean(ρij, i<j)', 'returns',
         '状态由样本字段明确提供，不自动划分；每状态至少两行、各列非零方差。',
         [_cols(), _col('regime_column', '状态分组列', 'regime')]),
        (9, 'reversion', '均值回归与自相关', '124–126', 'ΔSt = a + b St−1; speed = −b', 'reversion',
         'speed为一步离散回归系数，不是连续OU kappa；按输入顺序计算。',
         [_col(default='level'), _json('lags', '自相关滞后期数组', [1, 2, 5, 10])]),
        (10, 'sample', 'Gaussian Copula模拟', '130–133', 'U = Φ(LZ), LLᵀ = R', 'probabilities',
         '样本每行对应一个变量；相关矩阵为潜变量正态相关，需正定。输出为均匀边际。',
         [_json('correlation', '潜变量相关矩阵（按样本行顺序）', [[1, .4], [.4, 1]]),
          _num('n_samples', '模拟样本数', 500, 2, 20000), _num('seed', '随机种子', 42, 0, 4294967295)]),
        (10, 'joint', 'Copula联合违约概率', '130–133', 'P = ΦR(Φ⁻¹(p1),…,Φ⁻¹(pn))', 'probabilities',
         '每行一个变量，输入小数概率；相关矩阵按样本行顺序。二维为确定性积分，多维为SciPy数值CDF。',
         [_col('probability_column', '边际违约概率列', 'probability'),
          _json('correlation', '潜变量相关矩阵', [[1, .4], [.4, 1]])]),
        (10, 'default_times', '指数违约时点映射', '133', 'τi = −ln(1−Ui) / hi', 'uniforms',
         '输入是(0,1)均匀边际，危险率为正，若危险率按年则输出时间为年。',
         [_cols(), _json('hazards', '常数危险率数组（按列顺序）', [.02, .05])]),
        (10, 'marginals', 'Copula边际分布映射', '130–133', 'Xi = Fi⁻¹(Ui)', 'uniforms',
         '输入(0,1)均匀边际；按所选列顺序配置分布。type为normal/exponential/student_t，loc/scale/df为对应参数。',
         [_cols(), _json('marginals', '边际配置数组（按列顺序）', [{'type': 'normal', 'loc': 0, 'scale': 1}, {'type': 'exponential', 'loc': 0, 'scale': 2}])]),
        (11, 'regression', '回归对冲', '136–141', 'y = β0 + Xβ + ε; ni = −DV01target βi / DV01i', 'hedge',
         '输入已对齐且单位一致，预测包含截距；DV01采用同一方向定义，有符号数量为对冲方向。',
         [_col('target_column', '被解释样本列', 'target'), _p('predictor_columns', '解释变量列（顺序对应DV01）', 'columns', ['a', 'b']),
          _num('target_dv01', '目标DV01', 100), _json('hedge_dv01', '工具DV01数组（按解释变量顺序）', [50, 80])]),
        (11, 'pca', '主成分分解', '142–145', 'Σ = VΛVᵀ; scores = (X−μ)V', 'hedge',
         '对原始变动协方差做PCA，不自动标准化。载荷为一标准差冲击；特征向量整体正负号等价。',
         [_cols(['a', 'b', 'target']), _num('n_components', '保留主成分数', 2, 1, 50)]),
        (11, 'factor_hedge', 'PCA因子敞口对冲', '145', 'Hᵀ n = −target', 'factor_exposures',
         '主表每行是一个对冲工具、每列是一个共同因子敞口；工具数等于所选因子数，矩阵可逆。',
         [_cols(['PC1', 'PC2']), _json('target_exposures', '目标因子敞口数组（按列顺序）', [10, 20])]),
    ]
    return [dict(id=f'ch{ch}_{key}', chapter=ch, name=name, workspace=f'ch{ch}',
                 description=description, formula=formula, pages=pages, assumptions=[description],
                 parameters=parameters, example_id=f'ch{ch}_{example}')
            for ch, key, name, pages, formula, example, description, parameters in definitions]


def examples():
    descriptions = {
        'ch8_returns': '第8章：固定种子对齐收益率', 'ch8_positions': '第8章：两个资产的波动率与敞口',
        'ch8_probabilities': '第8章：两个边际违约概率', 'ch9_returns': '第9章：两状态相关样本',
        'ch9_reversion': '第9章：固定种子均值回归水平', 'ch10_probabilities': '第10章：B/Caa边际概率',
        'ch10_uniforms': '第10章：固定种子Copula均匀样本', 'ch11_hedge': '第11章：两因子回归与PCA样本',
        'ch11_factor_exposures': '第11章：两个工具的因子敞口',
    }
    return [dict(id=key, name=value, chapter=int(key.split('_')[0][2:]),
                 description=value + '；构造演示数据，不是教材原始观测。') for key, value in descriptions.items()]


def example_frame(example_id):
    entry = next((e for e in examples() if e['id'] == example_id), None)
    if entry is None:
        raise ValueError('未知第8–11章示例')
    rng = np.random.default_rng(42)
    suffix = example_id.split('_', 1)[1]
    if suffix == 'returns':
        a = rng.normal(0, .02, 200)
        b = np.r_[.7 * a[:100], -.5 * a[100:]] + rng.normal(0, .01, 200)
        df = pd.DataFrame({'a': a, 'b': b, 'regime': ['normal'] * 100 + ['stress'] * 100})
    elif suffix == 'positions':
        df = pd.DataFrame({'amount': [1e7, 5e6], 'sigma': [.02, .01], 'weight': [.6, .4]})
    elif suffix == 'probabilities':
        df = pd.DataFrame({'probability': [.0651, .2383]})
    elif suffix == 'reversion':
        x = [80.]
        for _ in range(199):
            x.append(x[-1] + .3 * (100 - x[-1]) + rng.normal(0, .5))
        df = pd.DataFrame({'level': x})
    elif suffix == 'uniforms':
        df = load_chapter(10).GaussianCopula(pd.DataFrame([[1, .4], [.4, 1]], columns=['a', 'b'])).sample(500, rng)
    elif suffix == 'hedge':
        a, b, noise = rng.normal(size=(3, 200))
        df = pd.DataFrame({'a': a, 'b': b, 'target': .06 + .842 * a - .3 * b + .1 * noise})
    else:
        df = pd.DataFrame({'PC1': [2., 1.], 'PC2': [1., 3.]})
    fields = {c: {'kind': 'other', 'unit': 'other', 'sign': 'none'} for c in df}
    return df, {'fields': fields, 'chapter': entry['chapter'], 'example_id': example_id, 'source': entry['description']}


def _numeric(df, columns, minimum=1):
    if not isinstance(columns, list) or not columns or len(set(columns)) != len(columns):
        raise ValueError('请选择不重复的样本列')
    if any(not isinstance(c, str) or c not in df for c in columns):
        raise ValueError('所选样本列不存在')
    if len(df) < minimum or len(df) > 100000:
        raise ValueError(f'样本行数须在{minimum}至100000之间')
    values = df[columns]
    if any(not pd.api.types.is_numeric_dtype(values[c]) for c in columns) or not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError('所选样本必须为有限数值，不自动删除缺失值')
    return values


def _number(value, label, minimum=-np.inf, maximum=np.inf, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum or (integer and int(value) != value):
        raise ValueError(f'{label}不是允许范围内的{"整数" if integer else "有限数值"}')
    return int(value) if integer else float(value)


def _vector(value, size, label):
    if not isinstance(value, list) or len(value) != size:
        raise ValueError(f'{label}须为长度{size}的数组，顺序与所选列或样本行一致')
    return np.array([_number(x, label) for x in value])


def _correlation(value, size, positive=False):
    if size < 2 or size > 50 or not isinstance(value, list) or len(value) != size:
        raise ValueError('相关矩阵维数须与2至50个资产一致')
    matrix = np.array([_vector(row, size, '相关矩阵行') for row in value])
    if not np.allclose(matrix, matrix.T) or not np.allclose(np.diag(matrix), 1) or (np.abs(matrix) > 1).any():
        raise ValueError('相关矩阵必须对称、对角线为1、元素在[-1,1]')
    eigenvalues = np.linalg.eigvalsh(matrix)
    if eigenvalues.min() < -1e-10 or (positive and eigenvalues.min() <= 1e-10):
        raise ValueError('相关矩阵须正定' if positive else '相关矩阵须半正定')
    return pd.DataFrame(matrix)


def _scalar(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None if math.isnan(value) else ('Infinity' if value > 0 else '-Infinity')
    return value


def _table(name, frame, index=False):
    if isinstance(frame, pd.Series):
        frame = frame.rename('value').rename_axis('name').reset_index()
    elif index:
        frame = frame.rename_axis('variable').reset_index()
    frame = frame.copy()
    frame.columns = [str(c) for c in frame.columns]
    return dict(name=name, columns=list(frame.columns), rows=[{k: _scalar(v) for k, v in row.items()} for row in frame.to_dict('records')])


def _chart(title, frame, columns=None, kind='line'):
    columns = columns or list(frame.columns)
    # Only display is sampled; complete calculation tables remain available.
    positions = np.unique(np.linspace(0, len(frame) - 1, min(len(frame), 1000)).astype(int))
    return dict(title=title, x_label='行序号', series=[dict(name=str(c), type=kind,
                data=[[int(i), float(frame[c].iloc[i]) if np.isfinite(frame[c].iloc[i]) else None]
                      for i in positions]) for c in columns])


def _out(metrics=None, tables=None, charts=None, notes=None):
    return dict(metrics=[dict(name=k, value=_scalar(v)) for k, v in (metrics or {}).items()],
                tables=tables or [], charts=charts or [],
                notes=(notes or []) + ['数值图超过1000行时仅等距抽取展示点；表格保留完整结果。自然缺值显示为空，不替换为零。'])


def calculate(df, metadata, request):
    operation = next((o for o in operations() if o['id'] == request.get('operation')), None)
    if operation is None:
        raise ValueError('未知第8–11章操作')
    supplied = request.get('parameters') or {}
    if not isinstance(supplied, dict):
        raise ValueError('参数须为对象')
    p = {x['name']: x['default'] for x in operation['parameters']}
    if set(supplied) - set(p):
        raise ValueError('存在未注册的参数')
    p.update(supplied)
    ch = load_chapter(operation['chapter'])
    key = operation['id'].split('_', 1)[1]
    if key == 'moments':
        columns = p['target_columns']; values = _numeric(df, columns, 2)
        if len(columns) < 2 or (values.std() <= 0).any():
            raise ValueError('相关矩阵需要至少两列非零方差样本')
        if p['method'] not in ('pearson', 'spearman', 'kendall'):
            raise ValueError('未知相关方法')
        weights = pd.DataFrame({'weight': _vector(p['weights'], len(columns), '权重')})
        corr = ch.correlation_matrix(df, columns, p['method'])
        moments = ch.portfolio_moments(df, columns, weights, 'weight')
        return _out(moments.to_dict(), [_table('相关矩阵', corr, True)], notes=['组合矩始终使用原始样本协方差；秩相关选择只影响相关矩阵展示。'])
    if key == 'covariance_var':
        values = _numeric(df, [p['volatility_column'], p['exposure_column']])
        if (values[p['volatility_column']] < 0).any():
            raise ValueError('波动率不能为负')
        correlation = _correlation(p['correlation'], len(df))
        covariance = ch.covariance_from_correlation(df, p['volatility_column'], correlation)
        alpha = _number(p['confidence_level'], '置信水平', .001, .999)
        horizon = _number(p['horizon'], '持有期', .0001, 10000)
        value = ch.portfolio_var(df, p['exposure_column'], covariance, alpha, horizon)
        return _out({'VaR（金额）': value}, [_table('协方差矩阵', covariance, True)])
    if key == 'implied':
        values = _numeric(df, [p['weight_column'], p['volatility_column']], 2)
        sigma = values[p['volatility_column']]
        if (sigma < 0).any():
            raise ValueError('波动率不能为负')
        x = values[p['weight_column']] * sigma
        if np.isclose(x.sum() ** 2 - x @ x, 0, atol=1e-15):
            raise ValueError('隐含相关公式分母为零')
        result = ch.implied_average_correlation(df, p['weight_column'], p['volatility_column'], _number(p['portfolio_volatility'], '组合波动率', 0))
        return _out({'隐含平均相关系数': result}, notes=['若结果超出共同相关矩阵可行域，说明给定组合波动率与共同相关假设不一致；不截断结果。'])
    if key == 'joint_default':
        values = _numeric(df, [p['probability_column']], 2).iloc[:, 0]
        if len(values) != 2 or not values.between(0, 1).all():
            raise ValueError('本操作需要恰好两个[0,1]边际概率')
        a, b = values.to_numpy()
        value = ch.joint_default_probability(a, b, _number(p['correlation'], '违约相关系数', -1, 1))
        if value < max(0, a + b - 1) - 1e-12 or value > min(a, b) + 1e-12:
            raise ValueError('给定违约相关系数违反边际概率的Fréchet界')
        return _out({'联合违约概率': value})
    if key == 'rolling':
        _numeric(df, [p['first_column'], p['second_column']], 2)
        window = _number(p['window'], '窗口', 2, min(10000, len(df)), True)
        result = ch.rolling_pair_correlation(df, p['first_column'], p['second_column'], window)
        return _out(tables=[_table('滚动相关', result)], charts=[_chart('滚动相关', result, ['correlation'])])
    if key == 'regimes':
        columns = p['target_columns']; values = _numeric(df, columns, 2)
        regime = p['regime_column']
        if len(columns) < 2 or regime not in df or regime in columns or df[regime].isna().any():
            raise ValueError('至少两列数值及独立、无缺失的状态列')
        for _, group in df.groupby(regime):
            if len(group) < 2 or (group[columns].std() <= 0).any():
                raise ValueError('每个状态至少两个观测且各列方差非零')
        result = ch.regime_correlations(df, columns, regime).rename_axis(index=['regime', 'variable']).reset_index()
        return _out({'平均不同资产相关': ch.average_pair_correlation(values, columns)}, [_table('状态相关矩阵', result)])
    if key == 'reversion':
        values = _numeric(df, [p['target_column']], 4)
        if values.iloc[:, 0].std() <= 0:
            raise ValueError('均值回归需要非零方差')
        if not isinstance(p['lags'], list) or not 1 <= len(p['lags']) <= 100:
            raise ValueError('滞后期须为1至100个整数的数组')
        lags = [_number(x, '滞后期', 1, len(df) - 2, True) for x in p['lags']]
        result = ch.mean_reversion_regression(df, p['target_column'])
        acf = ch.autocorrelation(df, p['target_column'], lags)
        return _out(result.to_dict(), [_table('回归系数', result), _table('自相关', acf)],
                    charts=[dict(title='自相关函数', x_label='滞后期', series=[dict(name='自相关', type='bar', data=[[k, _scalar(v)] for k, v in acf.items()])])],
                    notes=['speed≤0或speed≥2时不应解释为稳定的离散均值回归；speed=0时长期均值无定义。'])
    if key in ('sample', 'joint'):
        if key == 'joint':
            values = _numeric(df, [p['probability_column']], 2).iloc[:, 0]
            if not ((values > 0) & (values < 1)).all():
                raise ValueError('边际概率须严格在(0,1)内')
        correlation = _correlation(p['correlation'], len(df), positive=True)
        correlation.columns = [f'variable_{i + 1}' for i in range(len(df))]
        model = ch.GaussianCopula(correlation)
        if key == 'joint':
            return _out({'联合违约概率': model.joint_probability(df, p['probability_column'])}, notes=['二维使用确定性数值积分；高维CDF使用数值积分估计，末位可能波动。'])
        count = _number(p['n_samples'], '模拟样本数', 2, 20000, True)
        seed = _number(p['seed'], '随机种子', 0, 4294967295, True)
        result = model.sample(count, np.random.default_rng(seed))
        scatter = result.iloc[np.unique(np.linspace(0, count - 1, min(count, 1000)).astype(int))]
        return _out({'模拟观测数': count}, [_table('均匀边际样本', result)],
                    [dict(title='前两个均匀边际', x_label=result.columns[0], y_label=result.columns[1],
                          series=[dict(name='Copula', type='scatter', data=scatter.iloc[:, :2].values.tolist())])],
                    ['输入主表行数确定变量数量，主表数值不参与模拟；相关矩阵和种子确定样本。'])
    if key in ('default_times', 'marginals'):
        columns = p['target_columns']; values = _numeric(df, columns)
        if not ((values > 0) & (values < 1)).all().all():
            raise ValueError('映射输入须严格在(0,1)内的均匀边际')
        if key == 'default_times':
            hazards = _vector(p['hazards'], len(columns), '危险率')
            if (hazards <= 0).any():
                raise ValueError('危险率必须为正')
            result = ch.exponential_default_times(df, columns, pd.DataFrame({'hazard': hazards}), 'hazard')
        else:
            specifications = p['marginals']
            if not isinstance(specifications, list) or len(specifications) != len(columns):
                raise ValueError('边际配置数量须与所选列一致')
            inverse = {}
            for column, spec in zip(columns, specifications):
                if not isinstance(spec, dict) or spec.get('type') not in ('normal', 'exponential', 'student_t') or set(spec) - {'type', 'loc', 'scale', 'df'}:
                    raise ValueError('边际配置需要type及合法的loc、scale、df参数')
                loc = _number(spec.get('loc', 0), '位置')
                scale = _number(spec.get('scale', 1), '尺度', 1e-12)
                model = {'normal': norm, 'exponential': expon, 'student_t': t}[spec['type']]
                kwargs = {'loc': loc, 'scale': scale}
                if spec['type'] == 'student_t':
                    kwargs['df'] = _number(spec.get('df', 5), '自由度', 1e-6)
                inverse[column] = model(**kwargs).ppf
            result = ch.map_marginals(df, inverse)
        return _out(tables=[_table('映射结果', result)], charts=[_chart('边际映射结果', result)])
    if key == 'regression':
        predictors = p['predictor_columns']; target = p['target_column']
        if not isinstance(predictors, list):
            raise ValueError('解释变量必须为列名数组')
        values = _numeric(df, [target, *predictors], len(predictors) + 2)
        if not predictors or len(predictors) > 50:
            raise ValueError('解释变量数量须在1至50之间')
        design = np.column_stack([np.ones(len(df)), values[predictors]])
        if np.linalg.matrix_rank(design) != design.shape[1]:
            raise ValueError('回归设计矩阵必须满列秩')
        dv01 = _vector(p['hedge_dv01'], len(predictors), '工具DV01')
        if (dv01 == 0).any():
            raise ValueError('工具DV01不能为零')
        model = ch.RegressionHedge(df, target, predictors)
        fitted = pd.DataFrame({'observed': df[target], 'predicted': model.predict(df)})
        fitted['residual'] = fitted.observed - fitted.predicted
        positions = model.hedge_positions(_number(p['target_dv01'], '目标DV01'), pd.DataFrame({'dv01': dv01}), 'dv01')
        return _out({'残差方差': model.residual_variance}, [_table('回归摘要', model.summary(), True), _table('对冲数量', positions), _table('拟合与残差', fitted)], [_chart('回归拟合', fitted, ['observed', 'predicted'])])
    if key == 'pca':
        columns = p['target_columns']; values = _numeric(df, columns, 2)
        if len(columns) > 50 or values.var().sum() <= 0 or np.linalg.matrix_rank(values - values.mean()) < len(columns):
            raise ValueError('PCA样本须有正定协方差且至多50列')
        count = _number(p['n_components'], '主成分数', 1, len(columns), True)
        model = ch.PrincipalComponents(df, columns)
        scores = model.transform(df, count)
        loadings = model.loadings(); loadings.columns = [f'PC{i + 1}' for i in range(len(columns))]
        variance = model.explained_variance(); variance.index = loadings.columns
        return _out({'保留解释方差比例': variance.iloc[:count].sum()}, [_table('解释方差比例', variance), _table('一标准差载荷', loadings, True), _table('主成分得分', scores)], [_chart('主成分得分', scores)])
    if key == 'factor_hedge':
        columns = p['target_columns']; exposures = _numeric(df, columns, 1)
        if len(columns) > 50 or len(df) != len(columns) or np.linalg.matrix_rank(exposures) != len(columns):
            raise ValueError('因子敞口矩阵必须为至多50维可逆方阵')
        target = pd.DataFrame([_vector(p['target_exposures'], len(columns), '目标敞口')], columns=columns)
        # Factor hedging uses supplied exposures, independent of any fitted PCA state.
        positions = ch.PrincipalComponents.hedge_positions(target, exposures)
        residual = exposures.to_numpy().T @ positions.to_numpy() + target.to_numpy().ravel()
        return _out({'最大绝对残余因子敞口': np.abs(residual).max()}, [_table('工具对冲数量', positions), _table('残余因子敞口', pd.Series(residual, index=columns))])
    raise ValueError('操作未实现')

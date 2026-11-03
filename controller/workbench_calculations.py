"""第1章网页适配：显式口径→教材服务→可持久化的指标、表格与图表。

此模块是调用边界，不改变教材计算器。所有风险公式复用service；
分布密度使用SciPy标准分布或显式说明的历史样本核密度估计。
"""
import math

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde, lognorm, norm

from service import load_chapter
from .workbench_catalog import catalog, examples, example_frame
from .workbench_preparation import numeric_column, prepare_frame, validate_fields

__all__ = ['catalog', 'examples', 'example_frame', 'prepare_frame', 'calculate_frame']


def _probability(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value < 1:
        raise ValueError(f'{name}必须在0和1之间')
    return float(value)


def _integer(value, name, lower, upper):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or int(value) != value or not lower <= value <= upper:
        raise ValueError(f'{name}必须为{lower}至{upper}之间的整数')
    return int(value)


def _scalar(value):
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None if math.isnan(value) else ('Infinity' if value > 0 else '-Infinity')
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def _table(name, frame):
    return {'name': name, 'columns': list(frame.columns),
            'rows': [{str(key): _scalar(value) for key, value in row.items()} for row in frame.to_dict('records')]}


def _series(name, x, y, kind='line'):
    return {'name': name, 'type': kind,
            'data': [[_scalar(a), float(b) if np.isfinite(b) else None] for a, b in zip(x, y)]}


def _result(metrics=None, tables=None, charts=None, notes=None):
    return {'metrics': metrics or [], 'tables': tables or [], 'charts': charts or [],
            'notes': (notes or []) + ['缺失数值显示为空；无穷值标明Infinity，不替换为零。']}


def _metric(name, value, unit=None):
    return {'name': name, 'value': _scalar(value), 'unit': unit}


class RiskSample:
    """已确认元数据中的单位和符号，供各种风险估计共享。"""
    def __init__(self, df, metadata, column, model):
        if model not in {'historical', 'normal', 'lognormal'}:
            raise ValueError('未知分布模型')
        values = numeric_column(df, column, minimum=1 if model == 'historical' else 2)
        spec = metadata.get('fields', {}).get(column, {})
        kind, unit, sign = (spec.get(key) for key in ('kind', 'unit', 'sign'))
        if model == 'historical':
            if kind not in {'arithmetic_return', 'pnl', 'loss'} or unit not in {'decimal', 'amount'}:
                raise ValueError('历史风险输入须为小数算术收益率或金额P&L/损失，不能直接使用对数收益率')
            if kind == 'arithmetic_return' and unit != 'decimal':
                raise ValueError('算术收益率必须使用小数单位')
        elif kind != ('arithmetic_return' if model == 'normal' else 'geometric_return') or unit != 'decimal':
            raise ValueError('正态模型需要小数算术收益率；对数正态模型需要小数对数收益率')
        if sign not in {'profit', 'loss'}:
            raise ValueError('风险样本必须明确盈利为正或损失为正')
        if model != 'historical' and sign != 'profit':
            raise ValueError('参数法收益率须盈利为正；请显式执行loss_to_profit转换')
        self.frame = pd.DataFrame({'sample': values.to_numpy(dtype=float) * (-1 if sign == 'loss' else 1)})
        self.model = model
        self.unit = '损失比例' if unit == 'decimal' else '金额损失'
        self.notes = [f'输入字段：{column}；原始单位：{unit}；约定：{"损失为正，按声明反号后调用教材服务" if sign == "loss" else "盈利为正"}。']
        chapter = load_chapter(1)
        quantiles = {'historical': chapter.HistoricalLossQuantile, 'normal': chapter.NormalLossQuantile,
                     'lognormal': chapter.LognormalLossQuantile}
        self.quantile = quantiles[model](self.frame, 'sample')
        self.mean = self.frame['sample'].mean()
        self.std = self.frame['sample'].std(ddof=1)

    def var(self, alpha, frame=None):
        chapter = load_chapter(1)
        functions = {'historical': chapter.cal_historical_var, 'normal': chapter.cal_normal_var,
                     'lognormal': chapter.cal_lognormal_var}
        return functions[self.model](self.frame if frame is None else frame, alpha, 'sample')

    def density(self):
        if len(self.frame) < 2 or not np.isfinite(self.std) or self.std <= 0:
            raise ValueError('密度与标准误计算需要至少两个观测且样本方差为正')
        if self.model == 'historical':
            self.notes.append('历史样本的分位点密度采用高斯核密度估计（SciPy默认Scott带宽），标准误为连续密度近似。')
            kde = gaussian_kde(-self.frame['sample'].to_numpy())
            return lambda q: np.asarray(kde(np.atleast_1d(q)))
        if self.model == 'normal':
            return lambda q: norm.pdf(q, loc=-self.mean, scale=self.std)
        distribution = lognorm(s=self.std, scale=np.exp(self.mean))
        return lambda q: distribution.pdf(1 - np.asarray(q))

    def observed_losses(self):
        values = self.frame['sample'].to_numpy()
        return -np.expm1(values) if self.model == 'lognormal' else -values


def _loss_charts(sample, threshold, name):
    losses = sample.observed_losses()
    chapter = load_chapter(1)
    edges = np.histogram_bin_edges(losses, bins=min(30, max(3, round(np.sqrt(len(losses))))))
    histogram = chapter.histogram_table(pd.DataFrame({'loss': losses}), 'loss', edges)
    ordered = np.sort(losses)
    positions = np.unique(np.linspace(0, len(ordered)-1, min(len(ordered), 1000)).astype(int))
    markers = [{'name': name, 'value': float(threshold)}] if np.isfinite(threshold) else []
    charts = [
        {'title': '损失分布', 'x_label': sample.unit, 'y_label': '频数', 'markers': markers,
         'series': [_series('样本频数', histogram['bin_midpoint'], histogram['count'], 'bar')]},
        {'title': '经验累计分布', 'x_label': sample.unit, 'y_label': '累计概率', 'markers': markers,
         'series': [_series('经验CDF', ordered[positions], (positions+1)/len(ordered))]},
    ]
    return histogram, charts


def _var(df, metadata, parameters):
    model = parameters.get('model', 'historical')
    alpha = _probability(parameters.get('confidence_level', .95), '风险置信水平')
    if model == 'compare':
        arithmetic = parameters.get('arithmetic_column') or parameters.get('target_column')
        geometric = parameters.get('geometric_column')
        a = numeric_column(df, arithmetic, minimum=2).to_numpy(dtype=float)
        g = numeric_column(df, geometric, minimum=2).to_numpy(dtype=float)
        if (a <= -1).any() or not np.allclose(np.log1p(a), g, rtol=1e-7, atol=1e-10):
            raise ValueError('比较需要同一观测的算术/对数收益率满足log(1+r)=R；请由同一价格样本派生，不能独立删行')
        samples = [RiskSample(df, metadata, arithmetic, 'historical'), RiskSample(df, metadata, arithmetic, 'normal'),
                   RiskSample(df, metadata, geometric, 'lognormal')]
        values = [sample.var(alpha) for sample in samples]
        names = ['历史模拟', '正态', '对数正态']
        frame = pd.DataFrame({'model': names, 'VaR': values, 'confidence_level': alpha, 'sample_size': len(df)})
        histogram, charts = _loss_charts(samples[0], values[0], '历史VaR')
        for chart in charts:
            chart['markers'] = [{'name': name, 'value': float(value)} for name, value in zip(names, values) if np.isfinite(value)]
        charts.append({'title': '同口径VaR比较', 'x_label': '模型', 'y_label': '损失比例',
                       'series': [_series('VaR', names, values, 'bar')]})
        return _result([_metric(name+' VaR', value, '损失比例') for name, value in zip(names, values)],
                       [_table('模型比较', frame), _table('损失直方图', histogram)], charts,
                       ['三个模型使用同一DataFrame的全部观测；未隐式删除样本。参数法不乘头寸。'])
    sample = RiskSample(df, metadata, parameters.get('target_column'), model)
    value = sample.var(alpha)
    histogram, charts = _loss_charts(sample, value, 'VaR')
    return _result([_metric('VaR', value, sample.unit), _metric('风险置信水平', alpha), _metric('样本数', len(df))],
                   [_table('损失直方图', histogram)], charts, sample.notes)


def _spectral(df, metadata, parameters):
    chapter = load_chapter(1)
    sample = RiskSample(df, metadata, parameters.get('target_column'), parameters.get('model', 'historical'))
    alpha = _probability(parameters.get('confidence_level', .95), '风险置信水平')
    weight = parameters.get('weight', 'es')
    if weight == 'es':
        engine = chapter.ExpectedShortfall(sample.quantile, alpha)
        title = 'ES'
    elif weight == 'exponential':
        gamma = parameters.get('gamma', .05)
        if isinstance(gamma, bool) or not isinstance(gamma, (int, float)) or not np.isfinite(gamma) or not .0001 <= gamma <= 10:
            raise ValueError('γ必须在0.0001至10之间')
        engine = chapter.SpectralRisk(sample.quantile, chapter.ExponentialWeight(gamma))
        title = '指数谱风险'
    else:
        raise ValueError('未知权重函数')
    method = parameters.get('method', 'integral')
    if method not in {'integral', 'slices'}:
        raise ValueError('估计方式须为integral或slices')
    count = _integer(parameters.get('n_slices', 100), '切片数量', 2, 10000)
    value = engine.calculate() if method == 'integral' else engine.calculate_slices(count)
    probabilities = np.unique(np.r_[np.linspace(.001, .999, 250), alpha])
    q = np.array([sample.quantile(p) for p in probabilities])
    weights = np.array([engine.weight_function(p) for p in probabilities])
    nodes = pd.DataFrame({'probability': probabilities, 'loss_quantile': q, 'weight': weights})
    sizes = sorted(set([10, 25, 50, 100, 250, count]))
    convergence = pd.DataFrame({'n_slices': sizes, 'estimate': [engine.calculate_slices(n) for n in sizes]})
    charts = [
        {'title': '损失分位数', 'x_label': '累计概率p', 'y_label': sample.unit,
         'series': [_series('Qloss(p)', probabilities, q)],
         'areas': [{'from': alpha, 'to': 1}] if weight == 'es' else []},
        {'title': '风险权重', 'x_label': '累计概率p', 'y_label': 'φ(p)', 'series': [_series('权重', probabilities, weights)]},
        {'title': '切片收敛', 'x_label': '切片数', 'y_label': sample.unit,
         'series': [_series(title, convergence['n_slices'], convergence['estimate'])]},
    ]
    return _result([_metric(title, value, sample.unit), _metric('样本数', len(df))],
                   [_table('分位数与权重', nodes), _table('切片收敛', convergence)], charts,
                   sample.notes + ['切片结果按教材内部网格计算，不将有限网格权重重新归一化。'])


def _standard_error(df, metadata, parameters):
    chapter = load_chapter(1)
    sample = RiskSample(df, metadata, parameters.get('target_column'), parameters.get('model', 'historical'))
    alpha = _probability(parameters.get('confidence_level', .95), '风险置信水平')
    confidence = _probability(parameters.get('interval_confidence', .90), '区间置信水平')
    method = parameters.get('method', 'bootstrap')
    engine = chapter.StandardError(confidence)
    tables = []
    if method == 'bootstrap':
        count = _integer(parameters.get('n_resamples', 500), '重采样次数', 2, 10000)
        seed = _integer(parameters.get('seed', 42), '随机种子', 0, 4294967295)
        stats = engine.bootstrap(sample.frame, lambda frame: sample.var(alpha, frame), count, np.random.default_rng(seed))
        low, high = stats['percentile_ci_lower'], stats['percentile_ci_upper']
        sample.notes.append('Bootstrap为IID整行重采样，估计对象为VaR；区间图显示百分位区间，表格同时显示正态近似区间。')
    elif method in {'quantile', 'spectral'}:
        density = sample.density()
        if method == 'quantile':
            q = sample.quantile(alpha)
            f = float(np.asarray(density(q)).reshape(-1)[0])
            if not np.isfinite(f) or f <= 0:
                raise ValueError('分位点密度须为有限正数，请调整样本或置信水平')
            nodes = pd.DataFrame({'p': [alpha], 'q': [q], 'density': [f]})
            calculated = engine.quantile(nodes, 'q', 'p', 'density', len(df))
            stats = calculated.iloc[0].rename({'q': 'estimate'})
            tables.append(_table('分位点与密度', calculated))
        else:
            count = _integer(parameters.get('n_slices', 100), 'ES积分节点数', 2, 500)
            # Midpoint quadrature on the ES tail; no infinite endpoint quantiles.
            probabilities = alpha + (1-alpha) * (np.arange(count)+.5)/count
            q = np.array([sample.quantile(p) for p in probabilities])
            f = np.asarray(density(q))
            if not np.isfinite(f).all() or (f <= 0).any():
                raise ValueError('谱积分节点密度须为有限正数')
            weight = chapter.ESWeight(alpha)
            nodes = pd.DataFrame({'p': probabilities, 'q': q, 'density': f,
                                  'spectrum': [weight(p) for p in probabilities], 'dp': (1-alpha)/count})
            stats = engine.spectral(nodes, 'p', 'q', 'density', 'spectrum', 'dp', len(df))
            tables.append(_table('ES积分节点', nodes))
            sample.notes.append('谱标准误针对ES；在尾部使用中点积分节点，结果为有限节点近似。')
        low, high = stats['ci_lower'], stats['ci_upper']
    else:
        raise ValueError('未知标准误方法')
    summary = pd.DataFrame({'statistic': stats.index, 'value': stats.to_numpy()})
    tables.insert(0, _table('估计误差', summary))
    charts = [{'title': '估计值与置信区间', 'x_label': sample.unit, 'y_label': '区间',
               'series': [_series('置信区间', [low, high], [1., 1.]), _series('估计值', [stats['estimate']], [1.], 'scatter')]}]
    return _result([_metric('估计值', stats['estimate'], sample.unit),
                    _metric('标准误', stats['standard_error'], sample.unit), _metric('区间置信水平', confidence)],
                   tables, charts, sample.notes)


def _diagnostics(df, metadata, parameters):
    chapter = load_chapter(1)
    column = parameters.get('target_column')
    values = numeric_column(df, column, minimum=4)
    if values.std(ddof=1) <= 0:
        raise ValueError('分布诊断需要非零样本方差')
    edges = np.histogram_bin_edges(values, bins=min(30, max(3, round(np.sqrt(len(values))))))
    summary = chapter.summary_statistics(df, column, edges)
    histogram = chapter.histogram_table(df, column, edges)
    qq = chapter.qq_coordinates(df, column, norm)
    thresholds = pd.DataFrame({'threshold': np.quantile(values, np.linspace(.5, .99, 30))})
    excess = chapter.mean_excess(df, column, thresholds, 'threshold')
    positions = np.unique(np.linspace(0, len(df)-1, min(len(df), 1000)).astype(int))
    date = metadata.get('date_column')
    if date not in df.columns:
        date = next((name for name, spec in metadata.get('fields', {}).items() if spec.get('kind') == 'date'), None)
    x = df[date].astype(str).to_numpy() if date else np.arange(len(df))
    unit = metadata.get('fields', {}).get(column, {}).get('unit', '原始单位')
    charts = [
        {'title': '样本时间序列', 'x_label': date or '行序号', 'y_label': unit,
         'series': [_series(column, x[positions], values.to_numpy()[positions])]},
        {'title': '样本直方图', 'x_label': unit, 'y_label': '频数',
         'series': [_series('频数', histogram['bin_midpoint'], histogram['count'], 'bar')]},
        {'title': '正态QQ图', 'x_label': '标准正态理论分位数', 'y_label': unit,
         'series': [_series('样本分位数', qq['theoretical_quantile'].iloc[positions], qq['empirical_quantile'].iloc[positions], 'scatter'),
                    _series('四分位参考线', qq['theoretical_quantile'].iloc[positions], qq['reference_line'].iloc[positions])]},
        {'title': '右尾平均超额', 'x_label': '阈值', 'y_label': unit,
         'series': [_series('平均超额', excess['threshold'], excess['mean_excess'])]},
    ]
    return _result([_metric('样本数', len(df)), _metric('均值', summary['mean'], unit),
                    _metric('样本标准差', summary['standard_deviation'], unit)],
                   [_table('描述统计', pd.DataFrame({'statistic': summary.index, 'value': summary.to_numpy()})),
                    _table('直方图', histogram), _table('QQ坐标', qq), _table('平均超额', excess)], charts,
                   ['图表超过1000点时抽取等距行用于展示；描述统计和表格使用完整样本，未删除观测。'])


def calculate_frame(df, metadata, request):
    """显式操作注册，不接受任意函数名或Python可执行表达式。"""
    validate_fields(df, metadata or {})
    operations = {'var': _var, 'spectral': _spectral, 'standard_error': _standard_error, 'diagnostics': _diagnostics}
    operation = request.get('operation')
    if operation not in operations:
        raise ValueError('未知网页计算操作')
    parameters = request.get('parameters') or {}
    if not isinstance(parameters, dict):
        raise ValueError('计算参数必须为对象')
    return operations[operation](df, metadata or {}, parameters)

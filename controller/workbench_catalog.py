"""网页操作目录与可复现样本；教材页码沿用第1章计算器。"""
import numpy as np
import pandas as pd

from service.catalog import MANIFEST


def _select(name, label, choices, default):
    return {'name': name, 'label': label, 'type': 'select', 'default': default,
            'options': [{'value': value, 'label': title} for value, title in choices]}


def _number(name, label, default, minimum, maximum):
    return {'name': name, 'label': label, 'type': 'number', 'default': default,
            'min': minimum, 'max': maximum}


def catalog():
    models = [('historical', '历史模拟'), ('normal', '正态'), ('lognormal', '对数正态')]
    model = _select('model', '分布模型', models, 'historical')
    column = {'name': 'target_column', 'label': '样本列', 'type': 'column'}
    alpha = _number('confidence_level', '风险置信水平', .95, .001, .999)
    definitions = [
        ('var', 'VaR', '损失分位数与同口径模型比较', 'VaRα = Qloss(α)', '3–7',
         ['收益率使用小数，盈利为正；金额损失仅支持历史模拟。', '比较模式要求算术与对数收益率来自同一组观测。'],
         [_select('model', '模型', models + [('compare', '三种模型比较')], 'historical'), column,
          {'name': 'arithmetic_column', 'label': '比较用算术收益率列', 'type': 'column'},
          {'name': 'geometric_column', 'label': '比较用对数收益率列', 'type': 'column'}, alpha]),
        ('spectral', 'ES / 谱风险', '组合损失分位数模型与风险权重', 'Mφ = ∫₀¹ Qloss(p) φ(p) dp', '7–10',
         ['谱权重非负、递增且积分为1。', '切片使用教材内部网格；ES在尾部切片，指数谱风险在全分布切片。'],
         [model, column, _select('weight', '权重函数', [('es', 'ES等尾部权重'), ('exponential', '指数权重')], 'es'),
          alpha, _number('gamma', '指数权重γ', .05, .0001, 10),
          _select('method', '估计方式', [('integral', '数值积分'), ('slices', '教材切片')], 'integral'),
          _number('n_slices', '切片数量', 100, 2, 10000)]),
        ('standard_error', '估计误差', 'VaR标准误、ES标准误与Bootstrap区间',
         'SE(Qα) = √[α(1−α)/(n f(Qα)²)]', '10–13',
         ['独立同分布样本；分位点密度须为正。', '历史模型密度使用高斯核估计，需非零样本方差。',
          'Bootstrap估计VaR；spectral方法估计ES。区间置信水平与风险置信水平独立。'],
         [_select('method', '标准误方法', [('bootstrap', 'Bootstrap VaR'), ('quantile', '分位数VaR'), ('spectral', 'ES谱积分')], 'bootstrap'),
          model, column, alpha, _number('interval_confidence', '区间置信水平', .90, .001, .999),
          _number('n_resamples', '重采样次数', 500, 2, 10000),
          _number('seed', '随机种子', 42, 0, 4294967295),
          _number('n_slices', 'ES积分节点数', 100, 2, 500)]),
        ('diagnostics', '分布诊断', '时间序列、描述统计、直方图、QQ及平均超额',
         'QQ: (F⁻¹((i−0.5)/n), x(i))', '13–16',
         ['至少4个有效观测且样本方差为正；QQ参考分布为标准正态。'], [column]),
    ]
    return {
        'chapters': [{'number': int(number), 'title': item['title'], 'pages': item['pages'],
                      'available': number == '1'} for number, item in MANIFEST.items()],
        'operations': [{'id': op, 'name': name, 'workspace': op, 'description': description,
                        'formula': formula, 'pages': pages, 'assumptions': assumptions,
                        'parameters': parameters}
                       for op, name, description, formula, pages, assumptions, parameters in definitions],
    }


def examples():
    return [
        {'id': 'textbook_normal', 'name': '教材例1.3：正态收益率',
         'description': '教材p.5：均值0.1、样本标准差0.25的构造样本；用于复现参数VaR，不是教材原始观测。'},
        {'id': 'textbook_lognormal', 'name': '教材例1.4：对数正态VaR',
         'description': '教材p.6：对数收益率均值0.05、样本标准差0.20的构造样本。'},
        {'id': 'demo_returns', 'name': '固定种子：每日收益率演示',
         'description': '固定随机种子生成500个对数收益率及对应算术收益率；不代表真实行情或教材原始数据。'},
        {'id': 'demo_prices', 'name': '价格与现金流演示',
         'description': '固定种子的价格、零现金流及年化贴现率，用于派生P&L和收益率；不是实际持仓。'},
    ]


def field(kind, unit='decimal', sign='profit'):
    return {'kind': kind, 'unit': unit, 'sign': sign}


def example_frame(example_id):
    entries = {item['id']: item for item in examples()}
    if example_id not in entries:
        raise ValueError('未知教材示例')
    if example_id in ('textbook_normal', 'textbook_lognormal'):
        standardized = np.array([-1., 0., 1.])  # ddof=1 gives mean=0, std=1.
        if example_id == 'textbook_normal':
            frame = pd.DataFrame({'arithmetic_return': .1 + .25 * standardized})
            fields = {'arithmetic_return': field('arithmetic_return')}
        else:
            frame = pd.DataFrame({'geometric_return': .05 + .2 * standardized})
            fields = {'geometric_return': field('geometric_return')}
    else:
        rng = np.random.default_rng(42)
        log_returns = rng.normal(.0004, .015, 500)
        dates = pd.bdate_range('2024-01-01', periods=500)
        if example_id == 'demo_returns':
            frame = pd.DataFrame({'date': dates, 'arithmetic_return': np.expm1(log_returns),
                                  'geometric_return': log_returns})
            fields = {'date': field('date', 'date', 'none'),
                      'arithmetic_return': field('arithmetic_return'), 'geometric_return': field('geometric_return')}
        else:
            frame = pd.DataFrame({'date': dates, 'book_value': 100 * np.exp(log_returns.cumsum()),
                                  'interim_payments': 0., 'discount_rate': .03})
            fields = {'date': field('date', 'date', 'none'), 'book_value': field('price', 'amount', 'none'),
                      'interim_payments': field('payment', 'amount', 'none'), 'discount_rate': field('rate', 'decimal', 'none')}
    return frame, {'fields': fields, 'source': entries[example_id]['description'], 'example_id': example_id,
                   'frequency': 'daily' if example_id.startswith('demo_') else 'one_period'}

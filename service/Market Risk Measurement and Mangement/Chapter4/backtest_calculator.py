"""第 4 章：Backtesting VaR。
教材 pp. 50–57；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.special import xlogy
from scipy.stats import chi2, binom

def exception_series(df, loss_column, var_column):
    """pp.50–51：每行损失与此前预测的同期间 VaR 已由调用方对齐。"""
    result = df.copy()
    result['exception'] = (df[loss_column]>df[var_column]).astype(int)
    return result

def _bernoulli_loglik(success, failure, probability):
    return xlogy(success,probability)+xlogy(failure,1-probability)

class CoverageBacktest:
    """pp.51–56：Kupiec 无条件覆盖、Christoffersen 独立性/条件覆盖。"""
    def __init__(self, df, target_column, confidence_level=.99):
        self.hits = df[target_column].to_numpy(dtype=int)
        self.probability = 1-confidence_level

    def unconditional(self):
        n, x = len(self.hits), self.hits.sum()
        lr = 2*(_bernoulli_loglik(x,n-x,x/n)-_bernoulli_loglik(x,n-x,self.probability))
        return pd.Series({'statistic':lr,'p_value':chi2.sf(lr,1),'exceptions':x})

    def independence(self):
        before, after = self.hits[:-1], self.hits[1:]
        counts = np.array([[np.sum((before==i)&(after==j)) for j in (0,1)] for i in (0,1)])
        # 未观测到的转移行对似然贡献为零；其概率取任意值均相同。
        alternative = sum(_bernoulli_loglik(row[1],row[0],row[1]/row.sum())
                          for row in counts if row.sum()>0)
        total = counts.sum(axis=0)
        null = _bernoulli_loglik(total[1],total[0],total[1]/total.sum())
        lr = 2*(alternative-null)
        return pd.Series({'statistic':lr,'p_value':chi2.sf(lr,1)})

    def conditional(self):
        lr = self.unconditional()['statistic']+self.independence()['statistic']
        return pd.Series({'statistic':lr,'p_value':chi2.sf(lr,2)})

def exception_count_probabilities(sample_size, confidence_level, count):
    """pp.52–54：二项分布的精确点概率和右尾概率。"""
    p = 1-confidence_level
    return pd.Series({'probability':binom.pmf(count,sample_size,p),
                      'upper_tail':binom.sf(count-1,sample_size,p)})

def traffic_light(exception_count):
    """p.54 表4.3：教材旧 Basel 250 日/99% 规则，不表示当前监管标准。"""
    if exception_count<=4:
        return pd.Series({'zone':'green','add_on':0.0})
    if exception_count>=10:
        return pd.Series({'zone':'red','add_on':1.0})
    return pd.Series({'zone':'yellow','add_on':{5:.4,6:.5,7:.65,8:.75,9:.85}[exception_count]})

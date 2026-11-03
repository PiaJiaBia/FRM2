"""第 6 章：Validating VaR Models。
教材 pp. 74–84；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.stats import norm, beta, binom

def finite_difference_sensitivity(df, parameter_column, base_estimate, estimator, bump):
    """pp.76–77：逐行参数中心差分；estimator(DataFrame) 返回标量。"""
    rows=[]
    for i in range(len(df)):
        up, down = df.copy(), df.copy()
        j = df.columns.get_loc(parameter_column)
        up.iloc[i,j] += bump
        down.iloc[i,j] -= bump
        vu, vd = estimator(up), estimator(down)
        rows.append(((vu-vd)/(2*bump),(vu-2*base_estimate+vd)/bump**2))
    return pd.DataFrame(rows,index=df.index,columns=['first_derivative','second_derivative'])

def quantile_confidence_interval(estimate, probability, density, sample_size, confidence_level=.95):
    """p.77：独立同分布渐近区间；density 是损失分位点处密度。"""
    se=np.sqrt(probability*(1-probability)/sample_size)/density
    z=norm.ppf((1+confidence_level)/2)
    return pd.Series({'estimate':estimate,'standard_error':se,'lower':estimate-z*se,'upper':estimate+z*se})

def order_probability_interval(sample_size, rank, confidence_level=.90):
    """pp.77–78：F(X_(rank)) ~ Beta(rank,n+1-rank)。"""
    tail=(1-confidence_level)/2
    return pd.Series(beta.ppf([tail,1-tail],rank,sample_size+1-rank),index=['lower','upper'])

def exception_probability_interval(exceptions, sample_size, confidence_level=.95):
    """pp.79–82：精确二项区间，作为覆盖率的验证实现。"""
    tail=(1-confidence_level)/2
    lower=0. if exceptions==0 else beta.ppf(tail,exceptions,sample_size-exceptions+1)
    upper=1. if exceptions==sample_size else beta.ppf(1-tail,exceptions+1,sample_size-exceptions)
    return pd.Series({'lower':lower,'upper':upper})

def benchmark_comparison(df, estimate_column, benchmark_column):
    """p.83：同口径估计与基准比较；差值和比率由调用方解释。"""
    result=df.copy()
    result['difference']=df[estimate_column]-df[benchmark_column]
    result['ratio']=df[estimate_column]/df[benchmark_column]
    return result

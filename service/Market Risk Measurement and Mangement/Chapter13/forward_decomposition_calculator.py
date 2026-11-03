"""第 13 章：Expectations, Risk Premium, Convexity and the Term Structure。
教材 pp. 160–163；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd

def expected_discount_factor(df, rate_column, probability_column, dt):
    """pp.160–162：离散状态下 E[1/(1+r*dt)]，不是 1/(1+E[r]*dt)。"""
    return (df[probability_column]/(1+df[rate_column]*dt)).sum()

def forward_from_discount_factors(df, start_discount_column, end_discount_column, tenor_column):
    """pp.160–162：连续复利远期；输入为两个日期的零息折现因子。"""
    result=df.copy()
    result['forward_rate']=np.log(df[start_discount_column]/df[end_discount_column])/df[tenor_column]
    return result

def forward_decomposition(df, duration_column, convexity_column, short_rate,
                          physical_drift, risk_premium, volatility):
    """p.163，式(13.20)：lambda 是每单位久期年风险溢价，不是 Sharpe ratio。"""
    result=df.copy()
    result['expectations']=short_rate+df[duration_column]*physical_drift
    result['risk_premium']=df[duration_column]*risk_premium
    result['convexity_adjustment']=-.5*df[convexity_column]*volatility**2
    result['forward_rate']=result[['expectations','risk_premium','convexity_adjustment']].sum(axis=1)
    return result

def expected_bond_return(df, duration_column, short_rate, risk_premium):
    """p.163，式(13.18)：瞬时年化预期收益。"""
    result=df.copy()
    result['expected_return']=short_rate+risk_premium*df[duration_column]
    return result

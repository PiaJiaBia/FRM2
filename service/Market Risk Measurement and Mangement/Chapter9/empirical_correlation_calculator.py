"""第 9 章：Empirical Properties of Correlation。
教材 pp. 122–128；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd

def rolling_pair_correlation(df, first_column, second_column, window):
    """pp.122–126：向后窗口；首 window-1 行自然为 NaN。"""
    result=df.copy()
    result['correlation']=df[first_column].rolling(window).corr(df[second_column])
    return result

def average_pair_correlation(df, target_columns):
    """p.122：只平均不同资产的相关系数，不包含对角线。"""
    matrix=df[target_columns].corr().to_numpy()
    return matrix[np.triu_indices(len(matrix),1)].mean()

def mean_reversion_regression(df, target_column):
    """pp.124–125，式(9.5)：Delta S = intercept + slope*S_previous。
    speed=-slope 是一步离散回归系数，不是连续 OU kappa。
    """
    values=df[target_column].to_numpy()
    x=np.column_stack([np.ones(len(values)-1),values[:-1]])
    intercept,slope=np.linalg.lstsq(x,np.diff(values),rcond=None)[0]
    speed=-slope
    return pd.Series({'intercept':intercept,'slope':slope,'speed':speed,
                      'long_run_mean':intercept/speed,'ar_coefficient':1+slope})

def autocorrelation(df, target_column, lags):
    """pp.125–126：各 lag 的样本 Pearson 自相关。"""
    return pd.Series({lag:df[target_column].autocorr(lag) for lag in lags},name='autocorrelation')

def regime_correlations(df, target_columns, regime_column):
    """pp.122–123：按调用方给定的经济状态分组。"""
    return df.groupby(regime_column)[target_columns].corr()

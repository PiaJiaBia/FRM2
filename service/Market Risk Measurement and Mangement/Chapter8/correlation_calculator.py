"""第 8 章：Correlation Basics。
教材 pp. 102–120；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

def correlation_matrix(df, target_columns, method='pearson'):
    """pp.104–106,118：Pearson；rank 方法是接口可选扩展。"""
    return df[target_columns].corr(method=method)

def portfolio_moments(df, target_columns, positions, weight_column):
    """pp.104–105：权重/金额向量顺序与 target_columns 一致。"""
    weights=positions[weight_column].to_numpy()
    covariance=df[target_columns].cov().to_numpy()
    return pd.Series({'mean':df[target_columns].mean().to_numpy()@weights,
                      'volatility':np.sqrt(weights@covariance@weights)})

def covariance_from_correlation(df, volatility_column, correlation):
    """p.108，式(8.9)：C = diag(sigma) R diag(sigma)。"""
    sigma=df[volatility_column].to_numpy()
    return pd.DataFrame(np.outer(sigma,sigma)*correlation.to_numpy(),index=df.index,columns=df.index)

def portfolio_var(df, exposure_column, covariance, confidence_level=.99, horizon=1):
    """pp.108–109：零均值 IID 假设下 sqrt(horizon) 时间缩放。"""
    x=df[exposure_column].to_numpy()
    return norm.ppf(confidence_level)*np.sqrt(horizon*(x@covariance.to_numpy()@x))

def implied_average_correlation(df, weight_column, volatility_column, portfolio_volatility):
    """pp.106–107：由指数方差反解单一平均相关系数。"""
    x=(df[weight_column]*df[volatility_column]).to_numpy()
    return (portfolio_volatility**2-x@x)/(x.sum()**2-x@x)

def joint_default_probability(probability_a, probability_b, default_correlation):
    """pp.113–114：Bernoulli 默认指示相关系数；区别于 copula 潜变量相关。"""
    return probability_a*probability_b+default_correlation*np.sqrt(
        probability_a*(1-probability_a)*probability_b*(1-probability_b))

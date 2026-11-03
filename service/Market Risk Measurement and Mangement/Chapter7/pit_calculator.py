"""第 7 章：Backtesting the Entire Distribution Using PIT。
教材 pp. 89–100；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.stats import norm, kstest, cramervonmises, chi2, weibull_min
from scipy.optimize import minimize
from scipy.special import expit


def ljung_box(df, target_column, max_lag):
    """p.96 / PDF107，式(7.12)：中心化样本ACF，分母采用总离差平方和。"""
    x=df[target_column].to_numpy()
    x=x-x.mean()
    n=len(x)
    lags=np.arange(1,max_lag+1)
    acf=np.array([x[k:]@x[:-k]/(x@x) for k in lags])
    statistic=n*(n+2)*np.sum(acf**2/(n-lags))
    return pd.Series({'statistic':statistic,'p_value':chi2.sf(statistic,max_lag)})


def linear_probability_model(df, target_column, predictor_columns):
    """pp.95–96：线性概率模型；White HC0 异方差稳健系数标准误。"""
    x=np.column_stack([np.ones(len(df)),df[predictor_columns]])
    y=df[target_column].to_numpy()
    coefficients=np.linalg.lstsq(x,y,rcond=None)[0]
    residual=y-x@coefficients
    bread=np.linalg.inv(x.T@x)
    covariance=bread@(x.T@((residual**2)[:,None]*x))@bread
    return pd.DataFrame({'coefficient':coefficients,'standard_error':np.sqrt(np.diag(covariance))},
                        index=['intercept',*predictor_columns])

def probability_integral_transform(df, target_column, cdf_function):
    """pp.89–92：cdf_function 接收整张表，以使用逐期预先估计的参数。"""
    result=df.copy()
    result['pit']=cdf_function(df[target_column],df)
    return result

def pit_diagnostics(df, target_column):
    """pp.98–99：连续分布 PIT 位于 (0,1)，报告 KS/CVM 和 AD 统计量。"""
    u=np.sort(df[target_column].to_numpy())
    n=len(u)
    i=np.arange(1,n+1)
    ks=kstest(u,'uniform')
    cvm=cramervonmises(u,'uniform')
    ad=-n-np.sum((2*i-1)*(np.log(u)+np.log(1-u[::-1])))/n
    return pd.Series({'ks':ks.statistic,'ks_p_value':ks.pvalue,
                      'cvm':cvm.statistic,'cvm_p_value':cvm.pvalue,'ad':ad})

def pit_independence(df, target_column, predictor_columns):
    """p.99：正态化 PIT 对调用方已对齐的滞后变量做 OLS；不隐式 shift。"""
    y=norm.ppf(df[target_column])
    x=np.column_stack([np.ones(len(df)),df[predictor_columns]])
    coefficients=np.linalg.lstsq(x,y,rcond=None)[0]
    errors=y-x@coefficients
    variance=errors@errors/(len(y)-x.shape[1])
    se=np.sqrt(np.diag(variance*np.linalg.inv(x.T@x)))
    return pd.DataFrame({'coefficient':coefficients,'standard_error':se,'t':coefficients/se},
                        index=['intercept',*predictor_columns])

def duration_test(df, target_column, exception_probability):
    """p.97：只用完整相邻异常间隔，Weibull 对固定强度指数分布的 LR。
    首尾未完成区间由调用层另行处理；本函数为完整间隔样本的似然。
    """
    durations=np.diff(np.flatnonzero(df[target_column].to_numpy()))
    shape, _, scale=weibull_min.fit(durations,floc=0)
    unrestricted=weibull_min.logpdf(durations,shape,scale=scale).sum()
    restricted=(np.log(exception_probability)-exception_probability*durations).sum()
    lr=2*(unrestricted-restricted)
    return pd.Series({'shape':shape,'intensity':1/scale,'statistic':lr,'p_value':chi2.sf(lr,2)})

def exception_logit(df, target_column, predictor_columns):
    """pp.95–97：异常指示对滞后预测变量 logistic MLE；数据已由调用层对齐。"""
    x=np.column_stack([np.ones(len(df)),df[predictor_columns]])
    y=df[target_column].to_numpy()
    objective=lambda b:np.sum(np.logaddexp(0,x@b)-y*(x@b))
    fit=minimize(objective,np.zeros(x.shape[1]),jac=lambda b:x.T@(expit(x@b)-y))
    p=expit(x@fit.x)
    covariance=np.linalg.inv(x.T@((p*(1-p))[:,None]*x))
    return pd.DataFrame({'coefficient':fit.x,'standard_error':np.sqrt(np.diag(covariance))},
                        index=['intercept',*predictor_columns])

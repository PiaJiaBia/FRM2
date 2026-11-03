"""第 10 章：Financial Correlation Modeling — Bottom-Up Approaches。
教材 pp. 130–133；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.stats import norm, multivariate_normal
from scipy.integrate import quad

class GaussianCopula:
    """pp.130–133：correlation 为潜在标准正态变量相关矩阵。"""
    def __init__(self, correlation):
        self.columns=correlation.columns
        self.correlation=correlation.to_numpy()
        self.cholesky=np.linalg.cholesky(self.correlation)

    def sample(self, n_samples, rng):
        z=rng.standard_normal((n_samples,len(self.columns)))@self.cholesky.T
        return pd.DataFrame(norm.cdf(z),columns=self.columns)

    def joint_probability(self, df, probability_column):
        thresholds=norm.ppf(df[probability_column].to_numpy())
        if len(thresholds)==2:
            rho=self.correlation[0,1]
            a,b=thresholds
            return quad(lambda x:norm.pdf(x)*norm.cdf((b-rho*x)/np.sqrt(1-rho*rho)), -np.inf,a)[0]
        return multivariate_normal.cdf(thresholds,mean=np.zeros(len(thresholds)),cov=self.correlation)

def exponential_default_times(df, target_columns, hazards, hazard_column):
    """p.133：常数危险率的逆 CDF；为教材默认时点映射的解析特例。"""
    values=-np.log1p(-df[target_columns].to_numpy())/hazards[hazard_column].to_numpy()
    return pd.DataFrame(values,index=df.index,columns=target_columns)

def map_marginals(df, inverse_cdfs):
    """pp.130–133：每列对应一个单变量逆 CDF；保留 copula 依赖结构。"""
    return pd.DataFrame({column:ppf(df[column]) for column,ppf in inverse_cdfs.items()},index=df.index)

"""第 3 章：Parametric Approaches (II): Extreme Value。
教材 pp. 36–47；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.stats import genextreme, genpareto
from scipy.integrate import quad
from scipy.optimize import least_squares

class GeneralizedExtremeValue:
    """pp.36–39：xi 为教材尾指数；SciPy 的形状参数 c = -xi。"""
    def __init__(self, location, scale, shape):
        self.location, self.scale, self.shape = location, scale, shape

    @classmethod
    def fit(cls, df, target_column):
        c, location, scale = genextreme.fit(df[target_column])
        return cls(location,scale,-c)

    def quantile(self, probability):
        return genextreme.ppf(probability,-self.shape,loc=self.location,scale=self.scale)

    def parent_quantile(self, probability, block_size):
        # F_max(x)=F_parent(x)^block_size；p.38 的母分布分位数。
        return self.quantile(np.asarray(probability)**block_size)

    def expected_shortfall(self, probability, block_size=1):
        """pp.38–39：对母分布尾分位数积分，要求 shape<1。"""
        return quad(lambda p:self.parent_quantile(p,block_size),probability,1)[0]/(1-probability)

    @classmethod
    def fit_gumbel_moments(cls, df, target_column):
        """p.41 Box3.1 的 xi=0 情况：均值=mu+EulerGamma*sigma。"""
        scale=np.sqrt(6*df[target_column].var(ddof=0))/np.pi
        return cls(df[target_column].mean()-np.euler_gamma*scale,scale,0.)

    @classmethod
    def fit_gumbel_regression(cls, df, target_column):
        """p.40，式(3.13,3.16)：排序概率i/(n+1)与Gumbel分位数回归。"""
        values=np.sort(df[target_column].to_numpy())
        probabilities=np.arange(1,len(values)+1)/(len(values)+1)
        x=-np.log(-np.log(probabilities))
        location,scale=np.linalg.lstsq(np.column_stack([np.ones(len(x)),x]),values,rcond=None)[0]
        return cls(location,scale,0.)

    @classmethod
    def fit_quantile_regression(cls, df, target_column, initial_parameters, bounds):
        """p.40：GEV排序分位数非线性最小二乘；参数顺序mu,sigma,xi。"""
        values=np.sort(df[target_column].to_numpy())
        probabilities=np.arange(1,len(values)+1)/(len(values)+1)
        fit=least_squares(lambda parameters:cls(*parameters).quantile(probabilities)-values,
                          initial_parameters,bounds=bounds)
        return cls(*fit.x),fit

def block_maxima(df, target_column, block_column):
    """pp.36–40：按调用方定义的等长区块提取最大损失。"""
    return df.groupby(block_column)[target_column].max().to_frame()

def hill_index(df, target_column, tail_count):
    """pp.40–42：最大 k 个正损失相对第 k+1 个的平均对数比。"""
    x = np.sort(df[target_column].to_numpy())[::-1]
    return np.log(x[:tail_count]/x[tail_count]).mean()


def pickands_index(df, target_column, tail_count):
    """p.40脚注8提及的Pickands估计：k,2k,4k阶下降统计量，要求4k<=样本数。"""
    x=np.sort(df[target_column].to_numpy())[::-1]
    k=tail_count
    return np.log((x[k-1]-x[2*k-1])/(x[2*k-1]-x[4*k-1]))/np.log(2)

def tail_extrapolation(threshold, tail_probability, probability, shape):
    """p.39，式(3.9)：Pareto 尾外推。"""
    return threshold*(tail_probability/(1-probability))**shape

class PeaksOverThreshold:
    """pp.43–45：GPD 超额损失；tail_probability = N_u/n；ES 要求 xi<1。"""
    def __init__(self, threshold, scale, shape, tail_probability):
        self.threshold, self.scale = threshold, scale
        self.shape, self.tail_probability = shape, tail_probability

    @classmethod
    def fit(cls, df, target_column, threshold):
        x = df[target_column].to_numpy()
        excess = x[x>threshold]-threshold
        shape, _, scale = genpareto.fit(excess,floc=0)
        return cls(threshold,scale,shape,len(excess)/len(x))

    @classmethod
    def fit_moments(cls, df, target_column, threshold):
        """p.45脚注12：GPD均值/方差矩估计，需要总体二阶矩存在。"""
        x=df[target_column].to_numpy()
        excess=x[x>threshold]-threshold
        mean,variance=excess.mean(),excess.var(ddof=0)
        shape=.5*(1-mean*mean/variance)
        return cls(threshold,mean*(1-shape),shape,len(excess)/len(x))

    def quantile(self, probability):
        ratio = self.tail_probability/(1-probability)
        if self.shape == 0:
            return self.threshold+self.scale*np.log(ratio)
        return self.threshold+self.scale/self.shape*(ratio**self.shape-1)

    def expected_shortfall(self, probability):
        q = self.quantile(probability)
        return (q+self.scale-self.shape*self.threshold)/(1-self.shape)

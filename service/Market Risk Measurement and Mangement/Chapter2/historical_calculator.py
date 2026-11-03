"""第 2 章：Non-Parametric Approaches。
教材 pp. 18–34；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde, binom
from scipy.optimize import brentq
from scipy.integrate import quad
from scipy.optimize import minimize


def historical_scenarios(df, target_columns, current_levels):
    """p.18 / PDF29：将历史相对因子变动施加于当前水平；输入已有变动率。"""
    return pd.DataFrame((1+df[target_columns].to_numpy())*current_levels.iloc[0].to_numpy(),
                        index=df.index,columns=target_columns)


class AsymmetricGARCH:
    """p.27 / PDF38，式(2.6)：h_t=omega+alpha*(epsilon_(t-1)+gamma)^2+beta*h_(t-1)。"""
    def __init__(self, omega, alpha, beta, gamma=0., mean=0.):
        self.omega,self.alpha,self.beta,self.gamma,self.mean=omega,alpha,beta,gamma,mean

    def filter(self, df, target_column, initial_variance):
        result=df.copy()
        residual=df[target_column].to_numpy()-self.mean
        variance=np.empty(len(df))
        variance[0]=initial_variance
        for t in range(1,len(df)):
            variance[t]=self.omega+self.alpha*(residual[t-1]+self.gamma)**2+self.beta*variance[t-1]
        result['variance']=variance
        result['standardized_residual']=residual/np.sqrt(variance)
        return result

    @classmethod
    def fit(cls, df, target_column, initial_parameters, initial_variance, bounds):
        """高斯准最大似然；参数顺序 omega,alpha,beta,gamma,mean；约束由调用方提供。"""
        def objective(parameters):
            model=cls(*parameters)
            filtered=model.filter(df,target_column,initial_variance)
            return .5*np.sum(np.log(filtered.variance)+(df[target_column]-model.mean)**2/filtered.variance)
        result=minimize(objective,initial_parameters,bounds=bounds,
                        constraints=[{'type':'ineq','fun':lambda p:1-p[1]-p[2]}],method='SLSQP')
        return cls(*result.x),result

    def filtered_paths(self, df, residual_column, initial_variance, horizon, n_paths, rng):
        """p.27：每日重抽标准化残差，并用生成的冲击递推下一期方差。"""
        residuals=df[residual_column].to_numpy()
        variance=np.full(n_paths,initial_variance,dtype=float)
        returns=np.empty((horizon,n_paths))
        for t in range(horizon):
            shock=rng.choice(residuals,n_paths)*np.sqrt(variance)
            returns[t]=self.mean+shock
            variance=self.omega+self.alpha*(shock+self.gamma)**2+self.beta*variance
        return pd.DataFrame(returns,index=pd.RangeIndex(1,horizon+1,name='step'))

class HistoricalDistribution:
    """pp.19,23–26：输入已是损失，正值表示亏损；可传入概率权重列。"""
    def __init__(self, df, target_column, weight_column=None):
        ordered = df.sort_values(target_column)
        self.values = ordered[target_column].to_numpy()
        weights = (np.ones(len(df)) if weight_column is None
                   else ordered[weight_column].to_numpy())
        self.weights = weights / weights.sum()
        self.cumulative = np.cumsum(self.weights)

    def quantile(self, probability):
        index = np.searchsorted(self.cumulative, probability, side='left')
        return self.values[index]

    def expected_shortfall(self, probability):
        # 每个观测的概率区间与尾部区间求交，处理边界上的部分概率。
        left = self.cumulative - self.weights
        mass = np.maximum(self.cumulative - np.maximum(left, probability), 0)
        return self.values @ mass / (1-probability)

def age_weights(df, decay):
    """p.24，式(2.1)：行按时间升序；最新观测获得最大权重。"""
    result = df.copy()
    powers = np.arange(len(df)-1, -1, -1)
    result['weight'] = (1-decay)*decay**powers/(1-decay**len(df))
    return result

def volatility_scale(df, target_column, volatility_column, forecast_volatility):
    """p.25：历史收益除以当时波动率，再乘当前预测波动率。"""
    result = df.copy()
    result['scaled'] = df[target_column]/df[volatility_column]*forecast_volatility
    return result

def correlation_scale(df, target_columns, historical_covariance, forecast_covariance):
    """p.26：先用历史 Cholesky 白化，再施加预测协方差；输入均值为零。"""
    old = np.linalg.cholesky(historical_covariance.to_numpy())
    new = np.linalg.cholesky(forecast_covariance.to_numpy())
    transformed = np.linalg.solve(old, df[target_columns].to_numpy().T).T @ new.T
    return pd.DataFrame(transformed, index=df.index, columns=target_columns)

def filtered_scenarios(df, target_column, volatility_column, forecast_volatility,
                       n_scenarios, rng):
    """pp.26–27：单期 filtered HS；标准化残差有放回抽样。"""
    residuals = (df[target_column]/df[volatility_column]).to_numpy()
    return pd.DataFrame({'scenario':rng.choice(residuals,n_scenarios)*forecast_volatility})

def bootstrap_estimates(df, estimator, n_resamples, rng, block_size=1):
    """pp.31–34：IID 或 circular moving-block bootstrap；整行同步抽样。"""
    n = len(df)
    values = []
    for _ in range(n_resamples):
        starts = rng.integers(0,n,size=int(np.ceil(n/block_size)))
        indices = ((starts[:,None]+np.arange(block_size)) % n).ravel()[:n]
        values.append(estimator(df.iloc[indices]))
    return pd.DataFrame({'estimate':values})

def quantile_interval(df, target_column, probability, confidence_level=.95):
    """pp.22,29–30：二项分布顺序统计量区间；0/n+1 阶定义为无穷端点。"""
    values = np.r_[-np.inf, np.sort(df[target_column]), np.inf]
    tail = (1-confidence_level)/2
    lower = int(binom.ppf(tail,len(df),probability))
    upper = int(binom.ppf(1-tail,len(df),probability))+1
    return pd.Series({'lower':values[lower], 'upper':values[upper]})

class KernelDistribution:
    """pp.19–21：高斯核损失分布；bandwidth 为 scipy KDE 的带宽参数。"""
    def __init__(self, df, target_column, bandwidth=None):
        self.kde = gaussian_kde(df[target_column],bw_method=bandwidth)

    def cdf(self, value):
        return self.kde.integrate_box_1d(-np.inf,value)

    def quantile(self, probability, bracket):
        return brentq(lambda x:self.cdf(x)-probability,*bracket)

    def expected_shortfall(self, probability, bracket):
        q = self.quantile(probability,bracket)
        return quad(lambda x:x*self.kde([x])[0],q,np.inf)[0]/(1-probability)

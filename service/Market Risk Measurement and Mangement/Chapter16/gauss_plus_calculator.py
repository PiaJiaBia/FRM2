"""第 16 章：The Vasicek and Gauss+ Models。
教材 pp. 184–191；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.linalg import expm
from scipy.optimize import least_squares
from Chapter14.short_rate_calculator import Vasicek

def vasicek_half_life(speed):
    """p.184，式(16.8)。"""
    return np.log(2)/speed

class GaussPlus:
    """pp.186–189，式(16.9–12)：r->m->l->mu，r 没有直接扩散项。
    模型使用风险中性参数；所有利率为小数，sigma 为每根号年的绝对利率波动。
    """
    def __init__(self, short_speed, medium_speed, long_speed,
                 medium_volatility, long_volatility, correlation, long_run_mean):
        ar,am,al=short_speed,medium_speed,long_speed
        self.matrix=np.array([[-ar,ar,0.],[0.,-am,am],[0.,0.,-al]])
        self.offset=np.array([0.,0.,al*long_run_mean])
        sm,sl,rho=medium_volatility,long_volatility,correlation
        self.diffusion=np.array([[0.,0.],[sm*rho,sm*np.sqrt(1-rho*rho)],[sl,0.]])

    def _transition(self, maturity, integrated=False):
        n=4 if integrated else 3
        a=np.zeros((n,n)); a[:3,:3]=self.matrix
        if integrated: a[3,0]=1
        b=np.zeros(n); b[:3]=self.offset
        q=np.zeros((n,n)); q[:3,:3]=self.diffusion@self.diffusion.T
        affine=np.zeros((n+1,n+1)); affine[:n,:n]=a; affine[:n,n]=b
        mean_transition=expm(affine*maturity)
        # Van Loan 矩阵指数精确积分线性高斯协方差；避免时间离散误差。
        block=np.block([[a,q],[np.zeros_like(a),-a.T]])
        exponential=expm(block*maturity)
        covariance=exponential[:n,n:]@exponential[:n,:n].T
        return mean_transition[:n,:n],mean_transition[:n,n],(covariance+covariance.T)/2

    def moments(self, state, horizon):
        """state 为一行、三列 DataFrame，顺序 r,m,l。"""
        transition,offset,covariance=self._transition(horizon)
        mean=transition@state.iloc[0].to_numpy()+offset
        return pd.Series(mean,index=state.columns),pd.DataFrame(covariance,index=state.columns,columns=state.columns)

    def discount(self, state, maturity):
        transition,offset,covariance=self._transition(maturity,integrated=True)
        initial=np.r_[state.iloc[0].to_numpy(),0.]
        mean=(transition@initial+offset)[3]
        return np.exp(-mean+.5*covariance[3,3])

    def yield_loadings(self, maturity):
        transition,offset,covariance=self._transition(maturity,integrated=True)
        return transition[3,:3]/maturity,(offset[3]-.5*covariance[3,3])/maturity

    def yield_volatility(self, maturity):
        loadings,_=self.yield_loadings(maturity)
        return np.linalg.norm(loadings@self.diffusion)

    def regression_loadings(self, maturity, reference_maturities):
        """p.188：短率瞬时无扩散；用两个参考期限解释中/长两个随机因子。"""
        references=np.array([self.yield_loadings(t)[0][1:] for t in reference_maturities])
        target=self.yield_loadings(maturity)[0][1:]
        return np.linalg.solve(references.T,target)

    @classmethod
    def fit_speeds(cls, df, maturity_column, coefficient_columns, reference_maturities,
                   initial_speeds, bounds):
        """p.188：第一阶段按跨期限回归系数拟合三均值回复速度。"""
        def residual(parameters):
            model=cls(*parameters,0.,0.,0.,0.)
            implied=np.array([model.regression_loadings(t,reference_maturities) for t in df[maturity_column]])
            return (implied-df[coefficient_columns].to_numpy()).ravel()
        return least_squares(residual,initial_speeds,bounds=bounds)

    @classmethod
    def fit_volatilities(cls, df, maturity_column, volatility_column, speeds,
                         initial_parameters, bounds):
        """p.189：第二阶段拟合 sigma_m,sigma_l,rho；先给定三速度。"""
        def residual(parameters):
            model=cls(*speeds,*parameters,0.)
            return np.array([model.yield_volatility(t) for t in df[maturity_column]])-df[volatility_column].to_numpy()
        return least_squares(residual,initial_parameters,bounds=bounds)

    def fit_long_run_mean(self, df, maturity_column, yield_column, short_rate_column,
                          reference_yield_columns, reference_maturities):
        """p.189：给定r及两个参考零息收益率，联合拟合跨日期/期限的mu。
        每行包含一个目标期限及对应日期的r、两条参考收益率；先反解m,l。
        """
        # 模型截距对mu线性；以mu=0与1构造精确线性最小二乘。
        speed=-np.diag(self.matrix)
        sm=np.linalg.norm(self.diffusion[1]); sl=self.diffusion[2,0]
        rho=self.diffusion[1,0]/sm
        predictions=[]
        for mu in (0.,1.):
            model=type(self)(*speed,sm,sl,rho,mu)
            refs=[model.yield_loadings(t) for t in reference_maturities]
            values=[]
            for _,row in df.iterrows():
                r=row[short_rate_column]
                rhs=row[list(reference_yield_columns)].to_numpy(dtype=float)-np.array([a[0][0]*r+a[1] for a in refs])
                ml=np.linalg.solve(np.array([a[0][1:] for a in refs]),rhs)
                loading,intercept=model.yield_loadings(row[maturity_column])
                values.append(loading@np.r_[r,ml]+intercept)
            predictions.append(np.array(values))
        base,difference=predictions[0],predictions[1]-predictions[0]
        return difference@(df[yield_column].to_numpy()-base)/(difference@difference)

    def fit_state(self, curve, maturity_column, yield_column):
        """pp.188–190：给定模型参数，由多个期限连续零息收益率反解三个状态。"""
        pairs=[self.yield_loadings(t) for t in curve[maturity_column]]
        loadings=np.array([x[0] for x in pairs])
        intercepts=np.array([x[1] for x in pairs])
        state=np.linalg.lstsq(loadings,curve[yield_column].to_numpy()-intercepts,rcond=None)[0]
        return pd.DataFrame([state],columns=['r','m','l'])

    def hedge_positions(self, target, hedges):
        """pp.190–191：按三个状态的美元敏感度求解相对价值交易的对冲数量。"""
        return pd.Series(np.linalg.solve(hedges.to_numpy().T,-target.iloc[0].to_numpy()),index=hedges.index)

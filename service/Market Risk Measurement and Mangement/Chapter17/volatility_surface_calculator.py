"""第 17 章：Volatility Smiles and Volatility Surfaces。
教材 pp. 194–204；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq
from scipy.interpolate import RegularGridInterpolator

class EuropeanOption:
    """pp.194–199：BSM 为反解隐含波动率的报价模型；q 可表示股息率或外币利率。"""
    def __init__(self, spot, rate, dividend_yield=0.):
        self.spot,self.rate,self.dividend_yield=spot,rate,dividend_yield

    def price(self, strike, maturity, volatility, option_sign=1):
        # option_sign=+1 为 call，-1 为 put；T>0,sigma>0。
        s,r,q=self.spot,self.rate,self.dividend_yield
        d1=(np.log(s/strike)+(r-q+.5*volatility**2)*maturity)/(volatility*np.sqrt(maturity))
        d2=d1-volatility*np.sqrt(maturity)
        return option_sign*(s*np.exp(-q*maturity)*norm.cdf(option_sign*d1)
                            -strike*np.exp(-r*maturity)*norm.cdf(option_sign*d2))

    def greeks(self, strike, maturity, volatility, option_sign=1):
        s,r,q=self.spot,self.rate,self.dividend_yield
        d1=(np.log(s/strike)+(r-q+.5*volatility**2)*maturity)/(volatility*np.sqrt(maturity))
        return pd.Series({'delta':option_sign*np.exp(-q*maturity)*norm.cdf(option_sign*d1),
                          'vega':s*np.exp(-q*maturity)*norm.pdf(d1)*np.sqrt(maturity),
                          'gamma':np.exp(-q*maturity)*norm.pdf(d1)/(s*volatility*np.sqrt(maturity))})

    def implied_volatility(self, price, strike, maturity, bracket, option_sign=1):
        return brentq(lambda sigma:self.price(strike,maturity,sigma,option_sign)-price,*bracket)

    def quotes(self, df, strike_column, maturity_column, volatility_column, option_sign=1):
        result=df.copy()
        result['price']=self.price(df[strike_column],df[maturity_column],df[volatility_column],option_sign)
        return result

class VolatilitySurface:
    """pp.198–199：输入完整矩形网格；行是期限、列是 moneyness，双线性插值。"""
    def __init__(self, grid):
        self.interpolator=RegularGridInterpolator((grid.index.to_numpy(),grid.columns.to_numpy()),grid.to_numpy())

    def evaluate(self, df, maturity_column, moneyness_column):
        result=df.copy()
        result['volatility']=self.interpolator(df[[maturity_column,moneyness_column]].to_numpy())
        return result

def minimum_variance_delta(delta, vega, volatility_spot_slope):
    """p.199：delta_MV = delta_BSM + vega_BSM*dE[sigma]/dS。"""
    return delta+vega*volatility_spot_slope

def risk_neutral_density(df, strike_column, call_price_column, rate, maturity):
    """pp.203–204：相邻非等距执行价的二阶差分，仅返回内部点。"""
    strikes=df[strike_column].to_numpy()
    prices=df[call_price_column].to_numpy()
    slopes=np.diff(prices)/np.diff(strikes)
    second=2*np.diff(slopes)/(strikes[2:]-strikes[:-2])
    return pd.DataFrame({strike_column:strikes[1:-1],'density':np.exp(rate*maturity)*second})

def jump_mixture_price(df, terminal_column, probability_column, strike, rate, maturity, option_sign=1):
    """pp.199–200：离散跳跃状态的风险中性期权价格，概率由调用层给定。"""
    payoff=np.maximum(option_sign*(df[terminal_column]-strike),0)
    return np.exp(-rate*maturity)*(df[probability_column]*payoff).sum()

"""第 12 章：Arbitrage Pricing with Term Structure Models。
教材 pp. 148–156；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.optimize import brentq

def risk_neutral_probability(price, up_value, down_value, rate, dt):
    """p.150，式(12.7)：单期简单复利。"""
    return (price*(1+rate*dt)-down_value)/(up_value-down_value)

def replicating_portfolio(payoffs, payoff_columns, target_column, prices, price_column):
    """pp.149–150：行=状态，列=交易资产；方阵满秩时解复制头寸。"""
    positions=np.linalg.solve(payoffs[payoff_columns].to_numpy(),payoffs[target_column].to_numpy())
    return pd.Series({'price':positions@prices[price_column].to_numpy(),
                      **dict(zip(payoff_columns,positions))})

class BinomialRateTree:
    """pp.148–156：每列一个时间步，每行 j 为累计向上次数；无效节点为 NaN。
    rate/probability 均为 DataFrame，p 是向上概率；贴现 1/(1+(r+OAS)*dt)。
    """
    def __init__(self, rates, probabilities, dt):
        self.rates=rates.to_numpy()
        self.probabilities=probabilities.to_numpy()
        self.dt=dt

    def rollback(self, terminal, target_column, spread=0., cashflows=None, exercise=None):
        values=terminal[target_column].to_numpy().copy()
        levels={len(values)-1:values.copy()}
        for t in range(len(values)-2,-1,-1):
            p=self.probabilities[:t+1,t]
            values=((1-p)*values[:-1]+p*values[1:])/(1+(self.rates[:t+1,t]+spread)*self.dt)
            if cashflows is not None:
                values=values+cashflows.iloc[:t+1,t].to_numpy()
            if exercise is not None:
                values=exercise(t,values)
            levels[t]=values.copy()
        return pd.DataFrame({t:pd.Series(v) for t,v in sorted(levels.items())})

    def price(self, terminal, target_column, **kwargs):
        return self.rollback(terminal,target_column,**kwargs).iloc[0,0]

    def option_adjusted_spread(self, terminal, target_column, market_price, bracket, **kwargs):
        """p.154：求使模型价格等于市价的固定利差。"""
        return brentq(lambda s:self.price(terminal,target_column,spread=s,**kwargs)-market_price,*bracket)

    @classmethod
    def calibrate_probabilities(cls, rates, curve, discount_column, dt, bracket=(0.,1.)):
        """pp.151–153：每个时间层共享向上概率，依次匹配零息价格。
        curve行是dt,2dt,...；首个短率已匹配首个折现因子；最后层概率不影响末期债。
        """
        n=len(rates.columns)
        probabilities=pd.DataFrame(np.full(rates.shape,.5),index=rates.index,columns=rates.columns)
        for step in range(n-1):
            maturity_steps=step+2
            target=curve[discount_column].iloc[maturity_steps-1]
            terminal=pd.DataFrame({'payoff':np.ones(maturity_steps+1)})
            def objective(p):
                trial=probabilities.copy()
                trial.iloc[:step+1,step]=p
                model=cls(rates.iloc[:,:maturity_steps],trial.iloc[:,:maturity_steps],dt)
                return model.price(terminal,'payoff')-target
            probabilities.iloc[:step+1,step]=brentq(objective,*bracket)
        return cls(rates,probabilities,dt)

def cmt_payments(df, yield_column, notional, fixed_rate, accrual):
    """pp.153–154：CMT 每次结算现金流。"""
    result=df.copy()
    result['payment']=notional*accrual*(df[yield_column]-fixed_rate)
    return result

def pnl_attribution(start_price, rolled_price, curve_price, final_price, payments=0.):
    """p.155：顺序重估的 carry/roll、曲线、OAS 归因；路径由调用方指定。"""
    return pd.Series({'carry_roll':rolled_price+payments-start_price,
                      'curve':curve_price-rolled_price,'spread':final_price-curve_price,
                      'total':final_price+payments-start_price})

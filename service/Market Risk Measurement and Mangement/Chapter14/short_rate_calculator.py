"""第 14 章：The Art of Term Structure Models: Drift。
教材 pp. 166–175；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
from abc import ABC, abstractmethod
import numpy as np
import pandas as pd
from scipy.integrate import quad

class ShortRateModel(ABC):
    """pp.166–173：单位是年；simulate 的每列为一个路径的标准正态冲击。"""
    @abstractmethod
    def drift(self, time, rate):
        pass

    @abstractmethod
    def diffusion(self, time, rate):
        pass

    def simulate(self, shocks, initial_rate, dt):
        rates=np.empty((len(shocks)+1,len(shocks.columns)))
        rates[0]=initial_rate
        for i,z in enumerate(shocks.to_numpy()):
            r=rates[i]
            rates[i+1]=r+self.drift(i*dt,r)*dt+self.diffusion(i*dt,r)*np.sqrt(dt)*z
        return pd.DataFrame(rates,index=np.arange(len(rates))*dt,columns=shocks.columns)

class GaussianDrift(ShortRateModel):
    """pp.166–169：Model 1 取 drift_rate=0；Model 2 取常数风险中性漂移。"""
    def __init__(self, drift_rate, volatility):
        self.drift_rate, self.volatility=drift_rate,volatility

    def drift(self,time,rate):
        return self.drift_rate

    def diffusion(self,time,rate):
        return self.volatility

    def discount(self, initial_rate, maturity):
        # p.182 式(15.24–25)；积分短率为正态，E[e^-I]=e^(-E[I]+Var[I]/2)。
        return np.exp(-initial_rate*maturity-.5*self.drift_rate*maturity**2+self.volatility**2*maturity**3/6)

class HoLee(ShortRateModel):
    """pp.169–170：时间相关漂移由调用方函数提供。"""
    def __init__(self, drift_function, volatility):
        self.drift_function,self.volatility=drift_function,volatility

    def drift(self,time,rate):
        return self.drift_function(time)

    def diffusion(self,time,rate):
        return self.volatility

    def discount(self, initial_rate, maturity):
        mean=initial_rate*maturity+quad(lambda t:(maturity-t)*self.drift_function(t),0,maturity)[0]
        return np.exp(-mean+self.volatility**2*maturity**3/6)

    @classmethod
    def from_forward_derivative(cls, derivative, volatility):
        # theta(t)=d f(0,t)/dt + sigma² t，可精确匹配初始连续远期曲线。
        return cls(lambda t:derivative(t)+volatility**2*t,volatility)

class Vasicek(ShortRateModel):
    """pp.171–175、184：风险中性 dr=k(theta-r)dt+sigma dW。"""
    def __init__(self, speed, long_run_mean, volatility):
        self.speed,self.long_run_mean,self.volatility=speed,long_run_mean,volatility

    def drift(self,time,rate):
        return self.speed*(self.long_run_mean-rate)

    def diffusion(self,time,rate):
        return self.volatility

    def moments(self, initial_rate, horizon):
        decay=np.exp(-self.speed*horizon)
        return pd.Series({'mean':self.long_run_mean+(initial_rate-self.long_run_mean)*decay,
                          'variance':self.volatility**2*(1-decay**2)/(2*self.speed)})

    def simulate_exact(self, shocks, initial_rate, dt):
        rates=np.empty((len(shocks)+1,len(shocks.columns)))
        rates[0]=initial_rate
        decay=np.exp(-self.speed*dt)
        std=self.volatility*np.sqrt((1-decay**2)/(2*self.speed))
        for i,z in enumerate(shocks.to_numpy()):
            rates[i+1]=self.long_run_mean+(rates[i]-self.long_run_mean)*decay+std*z
        return pd.DataFrame(rates,index=np.arange(len(rates))*dt,columns=shocks.columns)

    def discount(self, initial_rate, maturity):
        k,theta,sigma=self.speed,self.long_run_mean,self.volatility
        b=-np.expm1(-k*maturity)/k
        log_a=(theta-sigma**2/(2*k*k))*(b-maturity)-sigma**2*b*b/(4*k)
        return np.exp(log_a-b*initial_rate)

    def forward(self, initial_rate, maturity):
        decay=np.exp(-self.speed*maturity)
        return self.long_run_mean+(initial_rate-self.long_run_mean)*decay-self.volatility**2/(2*self.speed**2)*(1-decay)**2

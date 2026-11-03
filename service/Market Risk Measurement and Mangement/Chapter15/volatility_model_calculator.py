"""第 15 章：Term Structure Models: Volatility and Distribution。
教材 pp. 178–182；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.stats import ncx2
from Chapter14.short_rate_calculator import ShortRateModel

class TimeDependentGaussian(ShortRateModel):
    """p.178，式(15.1)：漂移和波动率均为时间函数。"""
    def __init__(self, drift_function, volatility_function):
        self.drift_function,self.volatility_function=drift_function,volatility_function

    def drift(self,time,rate):
        return self.drift_function(time)

    def diffusion(self,time,rate):
        return self.volatility_function(time)

    def moments(self, initial_rate, maturity):
        return pd.Series({'mean':initial_rate+quad(self.drift_function,0,maturity)[0],
                          'variance':quad(lambda t:self.volatility_function(t)**2,0,maturity)[0]})

    def discount(self, initial_rate, maturity):
        mean=initial_rate*maturity+quad(lambda t:(maturity-t)*self.drift_function(t),0,maturity)[0]
        variance=quad(lambda t:((maturity-t)*self.volatility_function(t))**2,0,maturity)[0]
        return np.exp(-mean+.5*variance)

class CIR(ShortRateModel):
    """pp.179,182：平方根扩散；模拟采用精确非中心卡方转换，避免 Euler 负利率。"""
    def __init__(self, speed, long_run_mean, volatility):
        self.speed,self.long_run_mean,self.volatility=speed,long_run_mean,volatility

    def drift(self,time,rate):
        return self.speed*(self.long_run_mean-rate)

    def diffusion(self,time,rate):
        return self.volatility*np.sqrt(rate)

    def simulate_uniforms(self, uniforms, initial_rate, dt):
        k,theta,sigma=self.speed,self.long_run_mean,self.volatility
        decay=np.exp(-k*dt)
        scale=sigma*sigma*(1-decay)/(4*k)
        degrees=4*k*theta/(sigma*sigma)
        values=np.empty((len(uniforms)+1,len(uniforms.columns)))
        values[0]=initial_rate
        for i,u in enumerate(uniforms.to_numpy()):
            values[i+1]=scale*ncx2.ppf(u,degrees,values[i]*decay/scale)
        return pd.DataFrame(values,index=np.arange(len(values))*dt,columns=uniforms.columns)

    def discount(self, initial_rate, maturity):
        k,theta,sigma=self.speed,self.long_run_mean,self.volatility
        h=np.sqrt(k*k+2*sigma*sigma)
        exp=np.exp(h*maturity)
        denominator=2*h+(k+h)*(exp-1)
        b=2*(exp-1)/denominator
        a=(2*h*np.exp((k+h)*maturity/2)/denominator)**(2*k*theta/sigma**2)
        return a*np.exp(-b*initial_rate)


class Courtadon(ShortRateModel):
    """p.179，式(15.4)：线性均值回复漂移，扩散 sigma*r；继承Euler模拟。"""
    def __init__(self, speed, long_run_mean, volatility):
        self.speed,self.long_run_mean,self.volatility=speed,long_run_mean,volatility

    def drift(self,time,rate):
        return self.speed*(self.long_run_mean-rate)

    def diffusion(self,time,rate):
        return self.volatility*rate

class LognormalRate:
    """pp.179–180：d ln r = log_drift dt + sigma dW；输入为正短率。"""
    def __init__(self, log_drift, volatility):
        self.log_drift,self.volatility=log_drift,volatility

    def simulate(self, shocks, initial_rate, dt):
        increments=self.log_drift*dt+self.volatility*np.sqrt(dt)*shocks.to_numpy()
        values=initial_rate*np.exp(np.vstack([np.zeros(shocks.shape[1]),np.cumsum(increments,axis=0)]))
        return pd.DataFrame(values,index=np.arange(len(values))*dt,columns=shocks.columns)

    def binomial_tree(self, initial_rate, n_steps, dt):
        """p.180：恒定参数的重组对数利率树。"""
        return pd.DataFrame({i:pd.Series(initial_rate*np.exp(self.log_drift*i*dt+
                             (2*np.arange(i+1)-i)*self.volatility*np.sqrt(dt))) for i in range(n_steps+1)})

class BlackKarasinski:
    """p.181，式(15.15)：常数参数 ln(r) 的 OU 精确转换。"""
    def __init__(self, speed, long_run_rate, volatility):
        self.speed,self.long_run_rate,self.volatility=speed,long_run_rate,volatility

    def simulate(self, shocks, initial_rate, dt):
        from Chapter14.short_rate_calculator import Vasicek
        process=Vasicek(self.speed,np.log(self.long_run_rate),self.volatility)
        return np.exp(process.simulate_exact(shocks,np.log(initial_rate),dt))


class TimeDependentBlackKarasinski:
    """p.181：时间变化的k、theta、sigma，在log(r)上Euler离散。"""
    def __init__(self, speed_function, central_rate_function, volatility_function):
        self.speed_function=speed_function
        self.central_rate_function=central_rate_function
        self.volatility_function=volatility_function

    def simulate(self, shocks, initial_rate, dt):
        logs=np.empty((len(shocks)+1,len(shocks.columns)))
        logs[0]=np.log(initial_rate)
        for i,z in enumerate(shocks.to_numpy()):
            t=i*dt
            logs[i+1]=logs[i]+self.speed_function(t)*(np.log(self.central_rate_function(t))-logs[i])*dt+self.volatility_function(t)*np.sqrt(dt)*z
        return pd.DataFrame(np.exp(logs),index=np.arange(len(logs))*dt,columns=shocks.columns)

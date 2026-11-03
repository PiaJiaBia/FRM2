"""第 5 章：VaR Mapping。
教材 pp. 60–72；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

class LinearRiskMapping:
    """pp.62–65：exposures 与协方差矩阵行列按相同风险因子排序。"""
    def __init__(self, exposures, exposure_column, covariance):
        self.index = exposures.index
        self.exposure = exposures[exposure_column].to_numpy()
        self.covariance = covariance.to_numpy()

    def var(self, confidence_level=.95):
        x = self.exposure
        return norm.ppf(confidence_level)*np.sqrt(x @ self.covariance @ x)

    def components(self, confidence_level=.95):
        x = self.exposure
        sigma = np.sqrt(x @ self.covariance @ x)
        marginal = norm.ppf(confidence_level)*(self.covariance @ x)/sigma
        return pd.DataFrame({'marginal_var':marginal,'component_var':x*marginal},index=self.index)

    def tracking_var(self, benchmark, target_column, confidence_level=.95):
        x = self.exposure-benchmark[target_column].to_numpy()
        return norm.ppf(confidence_level)*np.sqrt(x @ self.covariance @ x)

def cashflow_present_values(df, cashflow_column, rate_column, maturity_column, frequency=1):
    """pp.63–64：按每年 frequency 次复利折现；金额和利率单位由调用方统一。"""
    result = df.copy()
    result['present_value'] = df[cashflow_column]/(1+df[rate_column]/frequency)**(frequency*df[maturity_column])
    return result

def duration_map(df, value_column, duration_column, lower_duration, upper_duration):
    """p.63：两个节点保持现值和久期；不能保证高阶风险一致。"""
    result = df.copy()
    weight = (upper_duration-df[duration_column])/(upper_duration-lower_duration)
    result['lower_exposure'] = df[value_column]*weight
    result['upper_exposure'] = df[value_column]*(1-weight)
    return result

def forward_exposures(spot, strike, domestic_rate, foreign_rate, maturity, quantity=1):
    """pp.66–67：外汇远期 = 外币零息资产 - 本币零息负债；连续复利。"""
    return pd.DataFrame({'exposure':[quantity*spot*np.exp(-foreign_rate*maturity),
                                     -quantity*strike*np.exp(-domestic_rate*maturity)]},
                        index=['foreign_asset','domestic_liability'])

def fra_value(notional, forward_rate, contract_rate, accrual, payment_discount):
    """p.68：到期末支付的 FRA 现值；正号为收浮动付固定。"""
    return notional*accrual*(forward_rate-contract_rate)*payment_discount

def swap_cashflows(df, accrual_column, notional, fixed_rate):
    """pp.69–70：重置日收浮动付固定分解；df 按未来付款时间排序。"""
    result = df.copy()
    result['fixed_payment'] = -notional*fixed_rate*df[accrual_column]
    result.iloc[-1,result.columns.get_loc('fixed_payment')] -= notional
    # 另在时点0计入浮息债价值 +notional；未来列为固定债负现金流。
    return result

def delta_gamma_pnl(df, change_column, delta, gamma):
    """pp.70–72：标的价格绝对变动下的二阶 Taylor 近似。"""
    result = df.copy()
    change = df[change_column]
    result['pnl'] = delta*change+.5*gamma*change**2
    return result

"""第 18 章：Fundamental Review of the Trading Book。
教材 pp. 206–212；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd

def sensitivity_charge(df, sensitivity_column, weight_column, correlation):
    """pp.207–208：加权敏感度二次型的平方根（金额量纲）。
    教材式(18.1)印刷呈二次型；按紧接的“标准差”解释取平方根。
    """
    weighted=(df[sensitivity_column]*df[weight_column]).to_numpy()
    return np.sqrt(weighted@correlation.to_numpy()@weighted)


def correlation_scenarios(df, sensitivity_column, weight_column, correlation,
                          multipliers=(.75,1.,1.25)):
    """p.207脚注5：低/中/高相关情景，保持对角线1；相关系数限制于[-1,1]。"""
    charges=[]
    for multiplier in multipliers:
        scenario=np.clip(correlation.to_numpy()*multiplier,-1,1)
        np.fill_diagonal(scenario,1)
        charges.append(sensitivity_charge(df,sensitivity_column,weight_column,pd.DataFrame(scenario)))
    return pd.Series(charges,index=multipliers,name='charge')

def curvature_charge(df, delta_column, shock_column, up_pnl_column, down_pnl_column):
    """pp.208–209：两侧重估损失减掉线性贡献，较大者且不小于0。"""
    result=df.copy()
    linear=df[delta_column]*df[shock_column]
    result['curvature_charge']=np.maximum.reduce([linear-df[up_pnl_column],-linear-df[down_pnl_column],np.zeros(len(df))])
    return result

def default_charge(df, exposure_column, lgd_column, weight_column):
    """p.209：教材单项 exposure*LGD*RW；净额规则在调用层落实。"""
    result=df.copy()
    result['default_charge']=df[exposure_column]*df[lgd_column]*df[weight_column]
    return result

def residual_add_on(df, notional_column, weight_column):
    """p.209：名义本金乘残余风险权重后加总。"""
    return (df[notional_column]*df[weight_column]).sum()

def liquidity_adjusted_es(df, es_column, horizon_column, base_horizon=10):
    """p.210，式(18.2)：行按10/20/40/60/120天升序；ES_j 为嵌套因子子集。"""
    horizons=df[horizon_column].to_numpy()
    increments=np.diff(np.r_[0,horizons])/base_horizon
    return np.sqrt(np.sum(df[es_column].to_numpy()**2*increments))

def stress_scaled_es(stressed_reduced, current_full, current_reduced):
    """p.210：压力期精简因子 ES 按当前 full/reduced 比率缩放。"""
    return stressed_reduced*current_full/current_reduced

def weighted_es(total_es, partial_es, target_column, aggregation_weight=.5):
    """p.210：全组合和独立风险类别 ES 加总的加权平均。"""
    return aggregation_weight*total_es+(1-aggregation_weight)*partial_es[target_column].sum()

def capital_requirement(previous_es, previous_nonmodellable, average_es, average_nonmodellable, multiplier=1.5):
    """p.211：教材定义，均值窗口由调用层准备。"""
    return max(previous_es+previous_nonmodellable,multiplier*average_es+average_nonmodellable)

def pnl_attribution_ratios(df, actual_column, model_column):
    """p.211：复现教材旧 PLA 比率，不作为现行监管合规判断。"""
    difference=df[actual_column]-df[model_column]
    return pd.Series({'mean_ratio':difference.mean()/df[actual_column].std(ddof=1),
                      'variance_ratio':difference.var(ddof=1)/df[actual_column].var(ddof=1)})

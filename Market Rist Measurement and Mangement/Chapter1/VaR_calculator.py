import math
import numpy as np
from scipy.stats import norm

def cal_historical_var(df, confidence_level=0.95, target_column="pnl"):
    losses = (-df[target_column]).sort_values()
    rank = math.ceil(confidence_level * len(losses))
    return losses.iloc[rank - 1]


"""
参数法的头寸待定
"""
def cal_normal_var(df, confidence_level=0.95, target_column="arithmetic_return"):
    mean = df[target_column].mean()
    std = df[target_column].std(ddof=1)
    z = norm.ppf(confidence_level)

    return -mean + std * z


def cal_lognormal_var(
    df,
    confidence_level=0.95,
    target_column="geometric_return",
):
    mean = df[target_column].mean()
    std = df[target_column].std(ddof=1)
    z = norm.ppf(confidence_level)
    return 1 - np.exp(mean - std * z)
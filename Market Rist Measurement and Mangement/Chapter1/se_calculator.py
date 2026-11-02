from statistics import NormalDist

import numpy as np
import pandas as pd


def quantile_standard_error(
    data: pd.DataFrame,
    quantile_column: str,
    probability_column: str,
    density_column: str,
    sample_size: int,
    confidence_level: float = 0.90,
) -> pd.DataFrame:
    """
    每行提供 q、p=F(q)、概率密度 f(q)。
    假设样本独立同分布，且分位点处密度连续、为正。
    q 与标准误同单位，密度单位为 q 单位的倒数。
    """
    result = data.copy()

    q = result[quantile_column]
    p = result[probability_column]
    density = result[density_column]

    variance = p * (1.0 - p) / (sample_size * density**2)
    standard_error = np.sqrt(variance)
    z = NormalDist().inv_cdf((1.0 + confidence_level) / 2.0)

    result["variance"] = variance
    result["standard_error"] = standard_error
    result["ci_lower"] = q - z * standard_error
    result["ci_upper"] = q + z * standard_error

    return result


def bin_density(
    data: pd.DataFrame,
    lower_cdf_column: str,
    upper_cdf_column: str,
    bin_width_column: str,
) -> pd.DataFrame:
    """
    每行提供 F(q-h/2)、F(q+h/2)、h。
    h 与被估计分位数同单位。
    """
    result = data.copy()
    result["density"] = (
        result[upper_cdf_column] - result[lower_cdf_column]
    ) / result[bin_width_column]
    return result


def spectral_standard_error(
    data: pd.DataFrame,
    probability_column: str,
    quantile_column: str,
    density_column: str,
    spectrum_column: str,
    integration_weight_column: str,
    sample_size: int,
    confidence_level: float = 0.90,
) -> pd.Series:
    """
    每行是一个数值积分节点：
    p_i、q_i=F^{-1}(p_i)、f(q_i)、谱权重 phi(p_i)、积分权重 w_i。

    w_i 表示 dp 的数值积分权重，不是谱权重。
    损失口径的相干谱风险度量要求 phi 非负、非递减且积分为 1。
    节点位于 (0, 1)，且节点密度为正。
    """
    p = data[probability_column].to_numpy()
    q = data[quantile_column].to_numpy()
    density = data[density_column].to_numpy()
    spectrum = data[spectrum_column].to_numpy()
    weights = data[integration_weight_column].to_numpy()

    estimate = np.sum(weights * spectrum * q)

    kernel = np.minimum(p[:, None], p[None, :]) - np.outer(p, p)
    coefficients = weights * spectrum / density

    variance = coefficients @ kernel @ coefficients / sample_size
    standard_error = np.sqrt(variance)
    z = NormalDist().inv_cdf((1.0 + confidence_level) / 2.0)

    return pd.Series({
        "estimate": estimate,
        "variance": variance,
        "standard_error": standard_error,
        "ci_lower": estimate - z * standard_error,
        "ci_upper": estimate + z * standard_error,
    })


def empirical_expected_shortfall(
    data: pd.DataFrame,
    target_column: str,
    probability: float,
) -> float:
    """
    经验分布上尾 ES = integral_p^1 Q(u) du / (1-p)。
    对分位点处的观测使用部分权重，适用于 0 < p < 1。
    排序是顺序统计量定义的一部分。
    """
    values = np.sort(data[target_column].to_numpy())
    n = len(values)

    left = np.arange(n) / n
    right = np.arange(1, n + 1) / n

    tail_weights = np.maximum(
        right - np.maximum(left, probability),
        0.0,
    )

    return np.sum(tail_weights * values) / (1.0 - probability)


def bootstrap_standard_error(
    data: pd.DataFrame,
    estimator,
    n_resamples: int,
    rng: np.random.Generator,
    confidence_level: float = 0.90,
) -> pd.Series:
    """
    非参数 IID Bootstrap：整行有放回抽样。
    estimator 接收 DataFrame，返回一个标量，且不修改输入。
    """
    estimate = estimator(data)
    n = len(data)
    estimates = np.empty(n_resamples)

    for i in range(n_resamples):
        indices = rng.integers(0, n, size=n)
        sample = data.iloc[indices]
        estimates[i] = estimator(sample)

    standard_error = estimates.std(ddof=1)
    tail_probability = (1.0 - confidence_level) / 2.0
    z = NormalDist().inv_cdf(1.0 - tail_probability)

    percentile_lower, percentile_upper = np.quantile(
        estimates,
        [tail_probability, 1.0 - tail_probability],
    )

    return pd.Series({
        "estimate": estimate,
        "bootstrap_mean": estimates.mean(),
        "bootstrap_bias": estimates.mean() - estimate,
        "standard_error": standard_error,
        "normal_ci_lower": estimate - z * standard_error,
        "normal_ci_upper": estimate + z * standard_error,
        "percentile_ci_lower": percentile_lower,
        "percentile_ci_upper": percentile_upper,
    })
import numpy as np
import pandas as pd
from scipy import stats


def histogram_table(
    data: pd.DataFrame,
    target_column: str,
    bin_edges,
) -> pd.DataFrame:
    """
    bin_edges 为调用方给定的严格递增边界，覆盖全部观测。
    返回频数、概率及概率密度；密度单位为原数据单位的倒数。
    """
    values = data[target_column].to_numpy()
    counts, edges = np.histogram(values, bins=bin_edges)

    widths = np.diff(edges)
    probabilities = counts / len(values)

    return pd.DataFrame({
        "bin_left": edges[:-1],
        "bin_right": edges[1:],
        "bin_midpoint": (edges[:-1] + edges[1:]) / 2.0,
        "bin_width": widths,
        "count": counts,
        "probability": probabilities,
        "density": probabilities / widths,
    })


def summary_statistics(
    data: pd.DataFrame,
    target_column: str,
    mode_bin_edges,
) -> pd.Series:
    """
    样本标准差使用 ddof=1。
    偏度和峰度使用 SciPy 的偏差修正口径。
    众数近似使用等宽直方图最高频区间的中点；
    并列时取最左区间。输入至少 4 个观测且方差为正。
    """
    values = data[target_column].to_numpy()

    histogram = histogram_table(
        data,
        target_column=target_column,
        bin_edges=mode_bin_edges,
    )
    mode_index = histogram["count"].idxmax()

    excess_kurtosis = stats.kurtosis(
        values,
        fisher=True,
        bias=False,
    )

    return pd.Series({
        "n": len(values),
        "mean": np.mean(values),
        "median": np.median(values),
        "histogram_mode": histogram.loc[mode_index, "bin_midpoint"],
        "standard_deviation": np.std(values, ddof=1),
        "skewness": stats.skew(values, bias=False),
        "kurtosis": excess_kurtosis + 3.0,
        "excess_kurtosis": excess_kurtosis,
        "minimum": np.min(values),
        "maximum": np.max(values),
    })


def qq_coordinates(
    data: pd.DataFrame,
    target_column: str,
    reference_distribution,
) -> pd.DataFrame:
    """
    reference_distribution 为具有 ppf 方法的 SciPy 分布对象。
    使用 p_i=(i-0.5)/n；排序属于 QQ 图的数学定义。
    返回按样本值递增排列的坐标，不保留原时间顺序。
    """
    empirical = np.sort(data[target_column].to_numpy())
    n = len(empirical)

    probabilities = (np.arange(1, n + 1) - 0.5) / n
    theoretical = reference_distribution.ppf(probabilities)

    # 用 25%、75% 分位点确定参考线，减少极端点的影响。
    theoretical_quartiles = reference_distribution.ppf([0.25, 0.75])
    empirical_quartiles = np.quantile(empirical, [0.25, 0.75])

    slope = (
        (empirical_quartiles[1] - empirical_quartiles[0])
        / (theoretical_quartiles[1] - theoretical_quartiles[0])
    )
    intercept = (
        empirical_quartiles[0] - slope * theoretical_quartiles[0]
    )
    reference_line = intercept + slope * theoretical

    return pd.DataFrame({
        "probability": probabilities,
        "theoretical_quantile": theoretical,
        "empirical_quantile": empirical,
        "reference_line": reference_line,
        "deviation": empirical - reference_line,
        "line_intercept": intercept,
        "line_slope": slope,
    })
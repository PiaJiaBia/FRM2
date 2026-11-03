"""第1章：Estimating Market Risk Measures。
教材pp.2–16 / PDF13–27。
统一计算模块；数据准备、清洗、展示与验证在Chapter1_test.ipynb中进行。
"""

import numpy as np
import math
from scipy.stats import norm
from abc import ABC, abstractmethod
from scipy.integrate import quad
from statistics import NormalDist
import pandas as pd
from scipy import stats


# 教材p.2 / PDF 13，式(1.1–1.4)：金额P&L；兼容原有默认列名。

def cal_pnl(df, value_column="book_value", payment_column="interim_payments"):
    result = df.copy()
    result["pnl"] = (
        result[value_column]
        + result[payment_column]
        - result[value_column].shift(1)
    )
    return result


def cal_pvpnl(df, value_column="book_value", payment_column="interim_payments",
              rate_column="discount_rate", periods_per_year=252):
    result = df.copy()
    daily_rate = result[rate_column] / periods_per_year

    result["pvpnl"] = (
        (result[value_column] + result[payment_column])
        / (1 + daily_rate)
        - result[value_column].shift(1)
    )
    return result


def cal_fvpnl(df, value_column="book_value", payment_column="interim_payments",
              rate_column="discount_rate", periods_per_year=252):
    result = df.copy()
    daily_rate = result[rate_column] / periods_per_year

    result["fvpnl"] = (
        result[value_column]
        + result[payment_column]
        - result[value_column].shift(1) * (1 + daily_rate)
    )
    return result


# 教材pp.2–3 / PDF 13–14，式(1.5–1.7)：收益率均为小数。

def cal_arithmetic_return(df, value_column="book_value", payment_column="interim_payments"):
    result = df.copy()
    result["arithmetic_return"] = (
        (result[value_column] + result[payment_column])
        / result[value_column].shift(1)
        - 1
    )
    return result


def cal_geometric_return(df, value_column="book_value", payment_column="interim_payments"):
    result = df.copy()
    result["geometric_return"] = np.log(
        (result[value_column] + result[payment_column])
        / result[value_column].shift(1)
    )
    return result


# 教材pp.3–7 / PDF 14–18：输入盈利为正；参数法收益率口径不乘头寸。

def cal_historical_var(df, confidence_level=0.95, target_column="pnl"):
    """p.3：经验损失分位数，不插值；调用前处理缺值。"""
    losses = (-df[target_column]).sort_values()
    rank = math.ceil(confidence_level * len(losses))
    return losses.iloc[rank - 1]


def cal_normal_var(df, confidence_level=0.95, target_column="arithmetic_return"):
    """pp.4–5：-mean + std*z，输出量纲与输入相同。"""
    mean = df[target_column].mean()
    std = df[target_column].std(ddof=1)
    z = norm.ppf(confidence_level)

    return -mean + std * z


def cal_lognormal_var(
    df,
    confidence_level=0.95,
    target_column="geometric_return",
):
    """pp.6–7：输入对数收益率，输出普通损失比例。"""
    mean = df[target_column].mean()
    std = df[target_column].std(ddof=1)
    z = norm.ppf(confidence_level)
    return 1 - np.exp(mean - std * z)


# 教材第1章 pp.7–10（PDF 18–21）：损失分位数与谱权重的组合。

class LossQuantile(ABC):
    @abstractmethod
    def __call__(self, p):
        pass

    @property
    def integration_points(self):
        """连续分位数默认没有内部跳点；历史分位数覆盖此接口。"""
        return []


class WeightFunction(ABC):
    @abstractmethod
    def __call__(self, p):
        pass

    @property
    def integration_points(self):
        return []


class SpectralRisk:
    def __init__(self, loss_quantile, weight_function):
        self.loss_quantile = loss_quantile
        self.weight_function = weight_function

    def calculate(self):
        points = np.unique([
            *self.loss_quantile.integration_points,
            *self.weight_function.integration_points,
        ])

        value, _ = quad(
            lambda p: self.loss_quantile(p) * self.weight_function(p),
            0,
            1,
            points=points,
            limit=len(points) + 50,
        )
        return value

    def calculate_slices(self, n_slices):
        """pp.9–10 / PDF20–21：教材内部网格近似，n-1个点乘积的算术均值。"""
        probabilities = np.arange(1, n_slices) / n_slices
        return np.mean([self.loss_quantile(p) * self.weight_function(p) for p in probabilities])


class NormalLossQuantile(LossQuantile):
    """输入为盈利为正的收益率或 P&L，输出为损失分位数。"""

    def __init__(self, df, target_column):
        self.mean = df[target_column].mean()
        self.std = df[target_column].std(ddof=1)

    def __call__(self, p):
        return -self.mean + self.std * norm.ppf(p)


class LognormalLossQuantile(NormalLossQuantile):
    """p.6 / PDF 17：输入对数收益率，返回普通损失比例。"""

    def __call__(self, p):
        return 1 - np.exp(self.mean - self.std * norm.ppf(p))

class HistoricalLossQuantile(LossQuantile):
    """输入为盈利为正的收益率或 P&L，输出为损失分位数。"""

    def __init__(self, df, target_column):
        self.losses = (-df[target_column]).sort_values().to_numpy()
        self.n = len(self.losses)

    def __call__(self, p):
        if p == 0:
            return self.losses[0]

        rank = math.ceil(p * self.n)
        return self.losses[rank - 1]

    @property
    def integration_points(self):
        return np.arange(1, self.n) / self.n

class ESWeight(WeightFunction):
    def __init__(self, confidence_level=0.95):
        self.confidence_level = confidence_level

    def __call__(self, p):
        if p < self.confidence_level:
            return 0.0

        return 1 / (1 - self.confidence_level)

    @property
    def integration_points(self):
        return [self.confidence_level]


class ExponentialWeight(WeightFunction):
    """p.9 / PDF 20，式(1.19)：权重积分为1且随损失概率递增。"""

    def __init__(self, gamma=0.05):
        self.gamma = gamma

    def __call__(self, p):
        return np.exp(-(1-p)/self.gamma)/(self.gamma*(-np.expm1(-1/self.gamma)))


class ExpectedShortfall(SpectralRisk):
    def __init__(self, loss_quantile, confidence_level=0.95):
        super().__init__(
            loss_quantile=loss_quantile,
            weight_function=ESWeight(confidence_level),
        )

    def calculate_slices(self, n_slices):
        """pp.7–8 / PDF18–19：只在ES尾部均匀切片，复现表1.1–1.2。"""
        alpha = self.weight_function.confidence_level
        probabilities = alpha + (1-alpha)*np.arange(1,n_slices)/n_slices
        return np.mean([self.loss_quantile(p) for p in probabilities])


# 教材pp.10–13 / PDF 21–24：风险估计量标准误与置信区间。
# 经验ES和bootstrap实现亦对应第2章pp.19,31–34。

class StandardError:
    """风险估计量的标准误与置信区间。

    教材第1章pp.10–13 / PDF21–24；Bootstrap另见第2章pp.31–34。
    confidence_level控制估计量的置信区间，不是VaR/ES的尾部置信水平。
    quantile/spectral接收公式节点；bootstrap接收原始样本与标量估计器。
    """

    def __init__(self, confidence_level=0.90):
        self.confidence_level = confidence_level
        self.z = NormalDist().inv_cdf((1.0 + confidence_level) / 2.0)

    def quantile(
        self,
        data: pd.DataFrame,
        quantile_column: str,
        probability_column: str,
        density_column: str,
        sample_size: int,
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
        z = self.z

        result["variance"] = variance
        result["standard_error"] = standard_error
        result["ci_lower"] = q - z * standard_error
        result["ci_upper"] = q + z * standard_error

        return result

    def spectral(
        self,
        data: pd.DataFrame,
        probability_column: str,
        quantile_column: str,
        density_column: str,
        spectrum_column: str,
        integration_weight_column: str,
        sample_size: int,
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
        z = self.z

        return pd.Series({
            "estimate": estimate,
            "variance": variance,
            "standard_error": standard_error,
            "ci_lower": estimate - z * standard_error,
            "ci_upper": estimate + z * standard_error,
        })

    def bootstrap(
        self,
        data: pd.DataFrame,
        estimator,
        n_resamples: int,
        rng: np.random.Generator,
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
        tail_probability = (1.0 - self.confidence_level) / 2.0
        z = self.z

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




# 教材pp.13–16 / PDF 24–27：描述统计、直方图、QQ与mean-excess。

def mean_excess(data, target_column, thresholds, threshold_column):
    """p.16 / PDF 27，脚注9：经验右尾平均超额，空尾部自然返回NaN。"""
    result = thresholds.copy()
    values = data[target_column]
    tails = [values[values > u] - u for u in thresholds[threshold_column]]
    result["exceedance_count"] = [len(tail) for tail in tails]
    result["mean_excess"] = [tail.mean() for tail in tails]
    return result


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

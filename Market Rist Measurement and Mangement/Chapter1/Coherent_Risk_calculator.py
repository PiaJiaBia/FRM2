from abc import ABC, abstractmethod
import numpy as np
from scipy.integrate import quad
from scipy.stats import norm
import math

class LossQuantile(ABC):
    @abstractmethod
    def __call__(self, p):
        pass


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


class NormalLossQuantile(LossQuantile):
    """输入为盈利为正的收益率或 P&L，输出为损失分位数。"""

    def __init__(self, df, target_column):
        self.mean = df[target_column].mean()
        self.std = df[target_column].std(ddof=1)

    def __call__(self, p):
        return -self.mean + self.std * norm.ppf(p)

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


class ExpectedShortfall(SpectralRisk):
    def __init__(self, loss_quantile, confidence_level=0.95):
        super().__init__(
            loss_quantile=loss_quantile,
            weight_function=ESWeight(confidence_level),
        )
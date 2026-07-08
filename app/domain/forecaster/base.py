"""Forecaster ABC (SPEC §3.4).

接口即 demo 主要交付物之一. forecast(history, horizon) -> np.ndarray; name 属性.
所有预测器零差分: 缺依赖则工厂回退 Persistence 并 log warn.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class Forecaster(ABC):
    """价格预测器抽象. 输入历史价序列, 输出 horizon 长预测数组."""

    name: str = "base"

    @abstractmethod
    def forecast(self, history: np.ndarray, horizon: int) -> np.ndarray:
        """对给定历史 LMP 序列预测未来 horizon 步. 返回 1D float 数组, len==horizon."""

    def __repr__(self) -> str:  # pragma: no cover - 仅为调试
        return f"{self.__class__.__name__}(name={self.name})"
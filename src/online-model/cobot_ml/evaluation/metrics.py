import abc
import math
from dataclasses import dataclass

import numpy as np

from cobot_ml import decorators
from cobot_ml import utilities
from cobot_ml.utilities import get_windows_limits_idxs


class BaseMetric(abc.ABC):
    """
    Base class for metrics, other metrics should subclass this base class
    and implement __call__() method
    """

    @abc.abstractmethod
    @decorators.accepts_one_dimensional_input(input_index=1)
    @decorators.accepts_one_dimensional_input(input_index=2)
    @decorators.inputs_have_equal_shapes(1, 2)
    def __call__(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        Call method should take labels and predictions in a form of 1d numpy arrays
        and return float corresponding to detector performance.
        """
        pass

    def __str__(self):
        return type(self).__name__.lower()


class NABScore(BaseMetric):
    """
    Our implementation of metric used in NAB benchmark.
    (https://arxiv.org/pdf/1510.03336.pdf)
    :param weight_tp: Weight for true positives
    :param weight_fp: Weight for false positives
    :param weight_fn: Weight for false negatives
    :param probationary_percent: percent of timesteps not accounted in score
    (note that if x * probationary percent > 750, 750 timestamps would not be accounted)
    """

    MAX_PROBATIONARY_LENGTH = 750

    @staticmethod
    @decorators.accepts_binary_array(input_index=0)
    @decorators.accepts_binary_array(input_index=1)
    @decorators.inputs_have_equal_shapes(0, 1)
    @decorators.returns_binary_array
    def get_true_positives(y_true: np.ndarray, y_pred: np.ndarray):
        """
        Returns the binary array like y_pred shape with 1s marking true positives
        :param y_true: Array with labels
        :param y_pred: Array with predictions
        """
        true_positives = np.zeros_like(y_pred)
        windows_starts_idxs, windows_stop_idxs = get_windows_limits_idxs(y_true)
        for window_start, window_stop in zip(windows_starts_idxs, windows_stop_idxs):
            detections = np.where(y_pred[window_start: window_stop + 1] == 1)
            if len(detections[0]) > 0:
                true_positives[window_start + detections[0][0]] = 1
        return true_positives

    def __init__(
            self,
            weight_tp: float = 1,
            weight_fp: float = 0.11,
            weight_fn: float = 1,
            probationary_percent: float = 0.15,
    ):
        self.weight_tp = weight_tp
        self.weight_fp = weight_fp
        self.weight_fn = weight_fn
        self.probationary_percent = probationary_percent

    def __call__(self, y_true: np.ndarray, y_pred: np.ndarray):
        return self.calculate_score(y_true, y_pred)

    @decorators.accepts_binary_array(input_index=1)
    @decorators.accepts_binary_array(input_index=2)
    def calculate_score(self, y_true: np.ndarray, y_pred: np.ndarray):
        """
        Returns nab score for given labels and predictions.
        :param y_true: Array with labels
        :param y_pred: Array with predictions
        """
        position_weights = self.calculate_position_weights(y_true)

        true_positives = self.get_true_positives(y_true, y_pred)
        false_positives = self.get_false_positives(y_true, y_pred)
        false_negatives = self.get_false_negatives(y_true, y_pred)

        scores = np.zeros_like(y_pred, dtype=np.float64)
        scores += true_positives * position_weights * self.weight_tp
        scores += false_positives * position_weights * self.weight_fp
        scores -= false_negatives * self.weight_fn

        probationary_length = min(
            math.floor(self.probationary_percent * len(y_true)),
            self.MAX_PROBATIONARY_LENGTH,
        )
        scores = scores[probationary_length:]
        score = scores.sum()

        return score

    @staticmethod
    @decorators.accepts_binary_array(input_index=0)
    @decorators.accepts_binary_array(input_index=1)
    @decorators.inputs_have_equal_shapes(0, 1)
    @decorators.returns_binary_array
    def get_false_positives(y_true: np.ndarray, y_pred: np.ndarray):
        """
        Returns the binary array like y_pred shape with 1s marking false positives
        :param y_true: Array with labels
        :param y_pred: Array with predictions
        """
        false_positives = y_pred.copy()
        windows_starts_idxs, windows_stop_idxs = get_windows_limits_idxs(y_true)
        for window_start, window_stop in zip(windows_starts_idxs, windows_stop_idxs):
            false_positives[window_start: window_stop + 1] = 0
        return false_positives

    @staticmethod
    @decorators.accepts_binary_array(input_index=0)
    @decorators.accepts_binary_array(input_index=1)
    @decorators.inputs_have_equal_shapes(0, 1)
    @decorators.returns_binary_array
    def get_false_negatives(y_true: np.ndarray, y_pred: np.ndarray):
        """
        Returns the binary array like y_pred shape with 1s marking false negatives
        :param y_true: Array with labels
        :param y_pred: Array with predictions
        """
        false_negatives = np.zeros_like(y_pred)
        windows_starts_idxs, windows_stop_idxs = get_windows_limits_idxs(y_true)
        for window_start, window_stop in zip(windows_starts_idxs, windows_stop_idxs):
            detections = np.where(y_pred[window_start: window_stop + 1] == 1)
            if len(detections[0]) == 0:
                false_negatives[(window_start + window_stop) // 2] = 1
        return false_negatives

    @staticmethod
    def position_weight(position: float):
        """
        Returns weight for a given relative position
        :param position: Relative position in anomaly window (in -3, 3 range)
        """
        if -3.0 <= position <= 3.0:
            return 2 / (1.0 + np.exp(5.0 * position)) - 1.0
        else:
            return -1.0

    @staticmethod
    def calculate_relative_position(
            idx_in_series: int, window_length: int, window_start: int
    ):
        """
        Returns position relative to anomaly window for a given time step in sequence.
        :param idx_in_series: Index of time step in sequence
        :param window_length: Number of time steps in anomaly window
        :param window_start: Index where anomaly window begins
        """
        return -3.0 + 3.0 * ((idx_in_series - window_start) / window_length)

    def calculate_position_weights(self, y_true: np.ndarray):
        """
        Returns array with position weights for all time steps in sequence.
        :param y_true: Array with labels
        """
        position_weights = np.array([-1.0 for _ in y_true])
        windows_starts_idxs, windows_stop_idxs = utilities.get_windows_limits_idxs(
            y_true
        )
        for window_start, window_stop in zip(windows_starts_idxs, windows_stop_idxs):
            window_length = window_stop - window_start
            window_influence_range = window_stop + 3 * window_length
            if window_influence_range > len(y_true):
                window_influence_range = len(y_true)
            for idx_in_series in range(window_start, window_influence_range):
                relative_position = self.calculate_relative_position(
                    idx_in_series, window_length, window_start
                )
                position_w = self.position_weight(relative_position)
                position_weights[idx_in_series] = position_w
        return position_weights


class DiceScore(BaseMetric):
    def __init__(self, epsilon: float = 1e-6):
        """
        Calculates Dice score for y_true and y_pred.
        Parameters:
            epsilon: Used to prevent division by zero.
        """
        self.epsilon = epsilon

    def __call__(self, y_true: np.ndarray, y_pred: np.ndarray) -> int:
        intersection = (y_true * y_pred).sum()
        union = y_true.sum() + y_pred.sum()
        score = 2.0 * intersection / (union + self.epsilon)
        return score


@decorators.accepts_binary_array(input_index=0)
@decorators.accepts_binary_array(input_index=1)
@decorators.inputs_have_equal_shapes(0, 1)
def get_group_true_positives(y_true: np.ndarray, y_pred: np.ndarray):
    """
    Returns a number of correctly detected anomalies.
    It treats anomaly as a group instead of calculating it for each time step.
    :param y_true: Array with labels
    :param y_pred: Array with predictions
    """
    begs, ends = get_windows_limits_idxs(y_true)
    tp = 0
    for start, stop in zip(begs, ends):
        if start == stop:
            if y_pred[start] == 1:
                tp += 1
        elif 1 in y_pred[start: stop + 1]:
            tp += 1
    return tp


@decorators.accepts_binary_array(input_index=0)
@decorators.accepts_binary_array(input_index=1)
@decorators.inputs_have_equal_shapes(0, 1)
def get_group_false_positives(y_true: np.ndarray, y_pred: np.ndarray) -> int:
    """
    Returns a number of incorrectly detected anomalies.
    It treats anomaly as a group instead of calculating it for each time step.
    :param y_true: Array with labels
    :param y_pred: Array with predictions
    """
    begs, ends = get_windows_limits_idxs(y_pred)
    fp = 0
    for start, stop in zip(begs, ends):
        if start == stop:
            if y_true[start] == 0:
                fp += 1
        elif 1 not in y_true[start: stop + 1]:
            fp += 1
    return fp


@decorators.accepts_binary_array(input_index=0)
@decorators.accepts_binary_array(input_index=1)
@decorators.inputs_have_equal_shapes(0, 1)
def get_group_false_negatives(y_true: np.ndarray, y_pred: np.ndarray) -> int:
    """
    Returns a number of undetected anomalies.
    It treats anomaly as a group instead of calculating it for each time step.
    :param y_true: Array with labels
    :param y_pred: Array with predictions
    """
    begs, ends = get_windows_limits_idxs(y_true)
    fn = 0
    for start, stop in zip(begs, ends):
        if start == stop:
            if y_pred[start] == 0:
                fn += 1
        elif 1 not in y_pred[start: stop + 1]:
            fn += 1
    return fn


@dataclass
class ConfusionMatrix:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0


@decorators.accepts_binary_array(input_index=0)
@decorators.accepts_binary_array(input_index=1)
@decorators.inputs_have_equal_shapes(0, 1)
def calculateConfusionMatrix(y_true: np.ndarray, y_pred: np.ndarray) -> ConfusionMatrix:
    confusion_matrix = ConfusionMatrix()
    confusion_matrix.true_positives = get_group_true_positives(y_true, y_pred)
    confusion_matrix.false_positives = get_group_false_positives(y_true, y_pred)
    confusion_matrix.false_negatives = get_group_false_negatives(y_true, y_pred)
    return confusion_matrix


class Recall(BaseMetric):
    """
    Calculates Recall score for y_true and y_pred.
    Parameters:
        epsilon: Used to prevent division by zero.
    """

    def __init__(self, epsilon: float = 1e-6):
        self.epsilon = epsilon

    def __call__(self, y_true: np.ndarray, y_pred: np.ndarray):
        confusion_matrix = calculateConfusionMatrix(y_true, y_pred)
        return confusion_matrix.true_positives / (
                confusion_matrix.true_positives
                + confusion_matrix.false_negatives
                + self.epsilon
        )


class Precision(BaseMetric):
    """
    Calculates Precision score for y_true and y_pred.
    Parameters:
        epsilon: Used to prevent division by zero.
    """

    def __init__(self, epsilon: float = 1e-6):
        self.epsilon = epsilon

    def __call__(self, y_true: np.ndarray, y_pred: np.ndarray):
        confusion_matrix = calculateConfusionMatrix(y_true, y_pred)
        return confusion_matrix.true_positives / (
                confusion_matrix.true_positives
                + confusion_matrix.false_positives
                + self.epsilon
        )


class FScore(BaseMetric):
    """
    Calculates FScore score for y_true and y_pred.
    Parameters:
        beta: Weight parameter between precision and recall
        epsilon: Used to prevent division by zero.
    """

    def __init__(self, beta: float = 1.0, epsilon: float = 1e-6):
        self.recall = Recall()
        self.precision = Precision()
        self.beta = beta
        self.epsilon = epsilon

    def __call__(self, y_true: np.ndarray, y_pred: np.ndarray):
        precision = self.precision(y_true, y_pred)
        recall = self.recall(y_true, y_pred)
        score = (1 + self.beta ** 2) * (
                (precision * recall) / (self.beta ** 2 * precision + recall + self.epsilon)
        )
        return score

    def __str__(self):
        return f"f{int(self.beta)}_score"


class Weigths:
    def _weight_const(self, ignored1: float, ignored2: float, const: float) -> float:
        return const

    def _weight_bell(self, expected: float, actual: float, std: float) -> float:
        return np.exp(-((expected - actual) ** 2) / (2 * std ** 2))

    def _weight_triangle(self, expected: float, actual: float, width: float) -> float:
        return max(0, 1 - abs(expected - actual) / width)

    def __init__(self, type: str, width: float):
        _weights = {
            "bell": self._weight_bell,
            "triangle": self._weight_triangle,
            "const": self._weight_const,
        }
        if type in _weights:
            self._weight = _weights[type]
        else:
            raise ValueError(f"Cannot handle [{type}]")
        self._width = width

    def __call__(self, expected: float, actual: float) -> float:
        return self._weight(expected, actual, self._width)


class KPBeginDifferencesForTP(BaseMetric):
    def __init__(self, weight_type: str = "const", weight_param: float = 1.0):
        self.weight = Weigths(weight_type, weight_param)

    """
    Calculates difference between beginnings of True Positives (in a sense of overlapping anomaly
    windows). When more than one detected anomalies overlaps the expected anomaly, only the first
    is considered.
    Example:
        y_true: ------AAAAAA---AAAAAAAAAAAAAAAAA--------
        y_pred: ----AAA--AAAA-A-----AAA--AAAAAAAAA---AA-
                     +               +

    Optionally weighted as suggested in http://www.acta.sapientia.ro/acta-info/C11-2/info11-2-1.pdf
    weight_type could be one of: "bell", "triangle" with weight_param
    set to Gaussian std or triangle-half width.
    """

    def __call__(self, y_true: np.ndarray, y_pred: np.ndarray):
        yt_beg, yt_end = get_windows_limits_idxs(y_true)
        yp_beg, yp_end = get_windows_limits_idxs(y_pred)

        at_least_one_TP = False
        result = 0
        for t_beg, t_end in zip(yt_beg, yt_end):
            for p_beg, p_end in zip(yp_beg, yp_end):
                overlap = range(max(t_beg, p_beg), min(t_end, p_end) + 1)
                if len(overlap) > 0:
                    result += self.weight(t_beg, p_beg) * abs(t_beg - p_beg)
                    at_least_one_TP = True
                    break
        if not at_least_one_TP:
            return len(y_true)

        return result

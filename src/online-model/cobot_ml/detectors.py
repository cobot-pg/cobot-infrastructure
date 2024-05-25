"""
Module contains implementations of anomaly detectors.
"""
import abc

import numpy as np
import pandas as pd
import torch
from torch.utils import data

from cobot_ml import decorators
from cobot_ml.data import patchers
from cobot_ml.observer import Observable
from cobot_ml.training.runners import run_prediction


class BaseDetector(abc.ABC, Observable):

    @abc.abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Method used to predict data in scikit-learn manner of data organisation.
        :param X: Input data for detection in shape (n_samples, n_features)
        :return: 1D array with predictions
        """
        pass


class BinaryDetector(BaseDetector, abc.ABC):
    @decorators.returns_binary_array
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Method used to predict data in scikit-learn manner of data organisation.
        :param X: Input data for detection in shape (n_samples, n_features)
        :return: 1D array with predictions (int)
        """
        predictions = np.array([self._predict_sample(sample) for sample in X])
        return predictions

    @abc.abstractmethod
    @decorators.accepts_one_dimensional_input(input_index=1)
    @decorators.returns_binary
    def _predict_sample(self, X: np.ndarray) -> int:
        """
        Method used to predict simple sample from data. In anomaly detection,
        the detector should not have the access to the future samples so this is an additional
        precaution to separate future data from detection process.
        :param X: Input sample for detection in shape (n_features)
        :return: Prediction in the form of int number (0,1)
        """
        pass


class ProbabilityDetector(BaseDetector, abc.ABC):
    @decorators.returns_probability_array
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Method used to predict data in scikit-learn manner of data organisation.
        :param X: Input data for detection in shape (n_samples, n_features)
        :return: 1D array with predictions (float)
        """
        predictions = np.array([self._predict_sample(sample) for sample in X])
        return predictions

    @abc.abstractmethod
    @decorators.accepts_one_dimensional_input(input_index=1)
    @decorators.returns_probability
    def _predict_sample(self, X: np.ndarray) -> float:
        """
        Method used to predict simple sample from data. In anomaly detection,
        the detector should not have the access to the future samples so this is an additional
        precaution to separate future data from detection process.
        :param X: Input sample for detection in shape (n_features)
        :return: Prediction in the form of float number (0-1)
        """
        pass


class Thresholded(BinaryDetector):
    """
    Used to convert probability detections of ProbabilityDetector to binary detections
    as in BinaryDetector by thresholding probability with a given value.
    """

    def __init__(self, probability_detector: ProbabilityDetector, threshold: float):
        super().__init__()
        self.detector = probability_detector
        self.threshold = threshold

    def _predict_sample(self, X: np.ndarray) -> int:
        """
        Method passes input to detector and thresholds returned probability
        to obtain binary prediction.
        :param X: Input sample for detection
        :return: Prediction in the form of int number (0,1)
        """

        probability = self.detector._predict_sample(X)
        prediction = 1 if self.threshold >= probability else 0
        return prediction


class MinMaxDetector(BaseDetector):
    """
    Standard detection for over the limit values.
    :param min: Lower bound of correct values range.
    :param max: Upper bound of correct values range.
    """

    class PublishedEvents:
        publish_detections = "Publish detections"

    def __init__(self, min: float, max: float):
        super().__init__()

        assert min < max, "Lower bound cannot be higher than upper"
        self.min = min
        self.max = max

    @decorators.accepts_single_feature(input_index=1)
    def predict(self, X: np.ndarray):
        """
        Method checks if a sample is within a given range.
        :param X: Input for detection
        :return: Prediction in the form of int number (0,1)
        """
        detections = np.zeros_like(X, dtype=np.int)
        detections[X < self.min] = 1
        detections[X > self.max] = 1
        detections = detections.flatten()
        self.publish(self.PublishedEvents.publish_detections, detections=detections)
        return detections


class MovingStdDetector(BaseDetector):
    """
    Detector detect an anomaly if moving standard deviation
    is not in a given range
    :param min: Lower bound of correct moving standard deviation range.
    :param max: Upper bound of correct moving standard deviation  range.
    """

    class PublishedEvents:
        publish_detections = "Publish detections"
        publish_stds = "Publish stds"

    def __init__(self, window_size: int, min: float, max: float):
        super().__init__()
        self.window_size = window_size
        self.min = min
        self.max = max
        self.min_max_detector = MinMaxDetector(min, max)

    @decorators.accepts_single_feature(input_index=1)
    def predict(self, X: np.ndarray):
        stds = pd.Series(X.flatten()).rolling(self.window_size).std().values
        stds = np.expand_dims(stds, 1)
        detections = self.min_max_detector.predict(stds)
        self.publish(self.PublishedEvents.publish_detections, detections=detections)
        self.publish(self.PublishedEvents.publish_stds, stds=stds)
        return detections


class Predictor:
    def __init__(self, model: torch.nn.Module, input_window_size: int):
        self.model = model
        self.input_window_size = input_window_size

    def predict_signal_with_model(
            self, signal: np.ndarray, batch_size: int = 256
    ) -> np.ndarray:
        """
        Use the model to predict the signal, based on the provided signal
        :param signal: True signal fed into the model.
        :param batch_size: Size of a batch.
        :return: Predicted signal.
        """
        tensors = self._preprocess_input_tensors(signal)
        data_loader = data.DataLoader(tensors, batch_size=batch_size)
        model_predictions = run_prediction(self.model, data_loader)
        return self._postprocess_network_predictions(model_predictions)

    def _preprocess_input_tensors(self, X: np.ndarray) -> torch.Tensor:
        """
        Pads, patches and converts arrays to float tensors.
        :param X: Array to preprocess. Should be two dimensional.
        :return: Padded, and patched tensors.
        """
        X_padded = pad_beginning(X, self.input_window_size)
        patches = patchers.patch_with_stride(X_padded, self.input_window_size, stride=1)
        tensors = (
            torch.from_numpy(np.array(patches))
            .to(next(self.model.parameters()).device)
            .float()
        )
        return tensors

    @staticmethod
    def _postprocess_network_predictions(predictions: torch.Tensor) -> np.ndarray:
        """
        Detaches and converts predictions to numpy arrays.
        It removes last detection (as it is a prediction of a value outside of a given data).
        """
        postprocessed = predictions.detach().cpu().numpy()
        postprocessed = postprocessed[:-1]
        return postprocessed




def pad_beginning(X: np.ndarray, padding: int):
    return np.pad(X, ((padding, 0), (0, 0)), mode="edge")

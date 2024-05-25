import typing

import pandas as pd

import numpy as np


class TimeSeriesSplit:
    """
    Splits time series sequences with temporal ordering preserved.
    :param n_splits: Number of splits to create,
        note that number of folds is n_splits+1
    :param extend_train: Whether include all samples
        preceding test set in train set
    :param extend_test: Whether include all samples
        following train set in test set
    """

    def __init__(
        self, n_splits: int = 10, extend_train: bool = True, extend_test: bool = False
    ):
        self.n_splits = n_splits
        self.extend_train = extend_train
        self.extend_test = extend_test

    def split(self, X: typing.Union[list, np.ndarray, pd.DataFrame]):
        """
        Generate indices to split data into training and test set.
        :param X: Data to split, must have __len__() implemented,
            usually it is list, np.ndarray or pd.DataFrame.
        """
        n_samples = len(X)
        n_folds = self.n_splits + 1
        assert (
            self.n_splits < n_samples
        ), "Number of folds exceeds the number of samples"
        indices = np.arange(n_samples)
        fold_size = n_samples // n_folds
        test_starts = range(fold_size, n_samples, fold_size)
        test_starts = [
            test_start for test_start in test_starts if len(X) - test_start > fold_size
        ]
        for test_start in test_starts:
            train = (
                indices[:test_start]
                if self.extend_train
                else indices[test_start - fold_size : test_start]
            )
            test = (
                indices[test_start:]
                if self.extend_test
                else indices[test_start : test_start + fold_size]
            )
            yield (train, test)

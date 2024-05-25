import typing

import numpy as np


def patch_with_stride(
        arr: np.ndarray, patch_len: int, stride: int
) -> typing.List[np.ndarray]:
    """
    Function returns patches created with given stride.
    :param arr: Array to patch
    :param patch_len: Length of patch
    :param stride: Step for patches
    """
    assert stride > 0, "Stride should be positive"
    patches = [
        arr[idx: idx + patch_len] for idx in range(0, len(arr) - patch_len + 1, stride)
    ]
    return patches


def patch(arr: np.ndarray, patch_len: int, step: int) -> typing.Iterator[np.ndarray]:
    """
    Function returns patches created with given stride in a form of Iterator
    :param arr: Array to patch
    :param patch_len: Length of patch
    :param step: Step for patches
    """
    assert step > 0, "Stride should be positive"
    for idx in range(0, len(arr) - patch_len + 1, step):
        yield arr[idx: idx + patch_len]

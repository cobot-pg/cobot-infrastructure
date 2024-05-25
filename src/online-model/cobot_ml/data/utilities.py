import typing
from enum import Enum
from random import sample

import numpy as np
import pandas as pd
import torch

from cobot_ml import detectors
from cobot_ml.data import datasets as dss, patchers


class DsMode(Enum):
    UNIVARIATE = 1
    WITH_MPC = 2
    WITHOUT_MPC = 3


def prepare_dataset(
        channel_values: typing.Union[pd.DataFrame, np.ndarray],
        input_steps: int,
        output_steps: int,
        ds_mode: DsMode,
        pad_beginning: bool = False,
) -> dss.TensorPairsDataset:
    if pad_beginning:
        channel_values = detectors.pad_beginning(channel_values, input_steps)

    patches = patchers.patch_with_stride(
        channel_values, input_steps + output_steps, stride=1
    )

    patches = [torch.from_numpy(patch.astype(np.float32)) for patch in patches]
    if ds_mode == DsMode.UNIVARIATE:
        X = [patch[:input_steps, [0]] for patch in patches]
    elif ds_mode == DsMode.WITH_MPC:
        X = [patch[:input_steps, :] for patch in patches]
    else:
        X = [patch[:input_steps, 1:] for patch in patches]
    y = [patch[input_steps:, 0] for patch in patches]
    # y = [patch[input_steps:, :] for patch in patches]
    return dss.TensorPairsDataset(X, y)


def prepare_dataset_with_original(
        dataset: dss.DatasetInputData,
        channel_name: str,
        input_steps: int,
        output_steps: int,
        ds_mode: DsMode,
        pad_beginning: bool = False,
) -> dss.TensorPairsDataset:
    _, columns, values, original_values = dataset.channel(channel_name)
    if pad_beginning:
        values = detectors.pad_beginning(values, input_steps)
        original_values = detectors.pad_beginning(original_values, input_steps)

    patches = patchers.patch_with_stride(values, input_steps + output_steps, stride=1)
    original_patches = patchers.patch_with_stride(original_values, input_steps + output_steps, stride=1)

    def to_torch(x: np.ndarray):
        return torch.from_numpy(x.astype(np.float32))

    if ds_mode == DsMode.UNIVARIATE:
        X = [to_torch(patch[:input_steps, [0]]) for patch in patches]
    elif ds_mode == DsMode.WITH_MPC:
        X = [to_torch(patch[:input_steps, :]) for patch in patches]
    else:
        X = [to_torch(patch[:input_steps, 1:]) for patch in patches]

    y = [to_torch(original_patch[input_steps:, 0]) for original_patch in original_patches]
    return dss.TensorPairsDataset(X, y)

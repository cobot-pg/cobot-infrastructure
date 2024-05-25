import glob
import os
import typing
import warnings

import natsort
import numpy as np
import pandas as pd
import torch
from torch.utils import data

import cobot_ml.data.patchers as patchers


class TensorPairsDataset(data.Dataset):
    """
    Dataset holding pairs of input and target tensors.
    :param inputs: List of input tensors
    :param targets: List of target tensors
    """

    def __init__(
            self, inputs: typing.List[torch.Tensor], targets: typing.List[torch.Tensor]
    ):
        assert len(inputs) == len(
            targets
        ), "Sequences and targets should have the same length"
        if len(inputs) == 0:
            warnings.warn("Empty input provided, add data to dataset!")

        self.inputs = inputs
        self.targets = targets

    def __len__(self):
        return len(self.inputs)

    def __getitem__(self, idx):
        X = self.inputs[idx]
        y = self.targets[idx]
        return X, y

    def get_unraveled_targets(self) -> torch.Tensor:
        """
        Return first value from each sample (but all values from the last
        sample). Used to build 1D vector of real values.
        """
        real_values = [self.targets[idx][0] for idx in range(len(self.targets) - 1)]
        return torch.hstack([torch.tensor(real_values), self.targets[-1]])


class DatasetInputData:
    implementations = {}

    @staticmethod
    def create(dataset: str, *args, **kwargs):
        assert dataset in DatasetInputData.implementations, f"Unknown dataset {dataset}"
        impl = DatasetInputData.implementations[dataset]
        ds_path = impl[1] if len(args) == 0 else args[0]
        return impl[0](ds_path, kwargs)

    def channel_names(self):
        raise NotImplementedError()

    def channel(self, channel_name):
        raise NotImplementedError()


def _files_as_pattern(path: str, pattern: str):
    files = glob.glob(os.path.join(path, pattern))
    return natsort.natsorted(files, key=lambda f: os.path.basename(f))


def _vector_length(df: pd.DataFrame, vector_name: str) -> pd.Series:
    return np.sqrt(
        df[f"{vector_name}_x"] ** 2 +
        df[f"{vector_name}_y"] ** 2 +
        df[f"{vector_name}_z"] ** 2
    )


class Datasets:
    CoBot202210 = "CoBot202210"
    CoBot20230708 = "CoBot20230708"


################################

base_path_datasets_ = "c:\\datasets\\"


class CoBot20230708Data:
    def __init__(self):
        base_dir = 'c:\\projekty\\cobot_july_august\\'
        sciezka_csv = base_dir + 'concatenated_with_wheels_change_changing_columns.csv'

        ignored_columns = [
            'timestamp', 'isoTimestamp', 'FH.6000.[TS] TIME STAMP.Time stamp',
            "FH.6000.[ENS] - Energy Signals.State Of Charge",
            "FH.6000.[NNS] - Natural Navigation Signals.Difference heading average correction",
            "FH.6000.[NNS] - Natural Navigation Signals.Distance average correction",
            "FH.6000.[ENS] - Energy Signals.Battery cell voltage",
            "FH.6000.[ODS] - Odometry Signals.Cumulative distance right",
            "FH.6000.[ENS] - Energy Signals.Momentary current consuption mA",
            "FH.6000.[ODS] - Odometry Signals.Cumulative distance left",
            "FH.6000.[ENS] - Energy Signals.Cumulative energy consumption Wh",
        ]

        all_the_data = pd.read_csv(sciezka_csv).iloc[2:]
        all_the_data = all_the_data.drop(columns=ignored_columns)

        # move the label column to 0-th index
        self.columns = all_the_data.columns.tolist()
        self.columns.remove(CoBot20230708.LABEL_COLUMN)
        self.columns.insert(0, CoBot20230708.LABEL_COLUMN)
        self.all_the_data = all_the_data[self.columns]

        self.column_stats = {}
        for column in self.all_the_data.columns:
            column_data = self.all_the_data[column]
            if column_data.dtype != bool:
                self.column_stats[column] = {
                    'mean': column_data.mean(),
                    'std': column_data.std(),
                    'min': column_data.min(),
                    'max': column_data.max(),
                }


class CoBot20230708(DatasetInputData):
    LABEL_COLUMN = "WHEEL_CHANGE"

    def __init__(self, path, kwargs):
        self.the_data = CoBot20230708Data()
        all_the_data = self.the_data.all_the_data.copy(deep=True)
        for col, stats in self.the_data.column_stats.items():
            _range = stats['max'] - stats['min']
            if _range != 0:
                all_the_data[col] = (all_the_data[col] - stats['min']) / _range

        slice_length = 3000
        begin_indices = [3000, 12000, 21000, 30000, 39000, 48000, 57000, 66000]

        # Inicjalizuj puste DataFrame na dane testowe
        test_data = pd.DataFrame()

        # Iteruj przez indeksy początków przedziałów
        for begin_index in begin_indices:
            # Wyciągnij fragment danych o długości slice_length i dołącz go do test_data
            test_data = pd.concat([test_data, all_the_data.loc[begin_index:begin_index + slice_length - 1]])

        # Usuń wiersze z test_data z all_the_data
        train_data = all_the_data.drop(test_data.index)

        self.train_data = train_data
        self.test_data = test_data
        print(f"Loaded Cobot20230708: len(train)={len(self.train_data)}, len(test)={len(self.test_data)}")

    def channel_names(self):
        return ["train", "test"]

    def channel(self, channel_name):
        if channel_name == "train":
            return channel_name, self.the_data.columns, self.train_data.to_numpy()
        elif channel_name == "test":
            return channel_name, self.the_data.columns, self.test_data.to_numpy()
        else:
            raise f"Invalid channel name {channel_name}. Only 'train' and 'test' allowed"


DatasetInputData.implementations[Datasets.CoBot20230708] = (CoBot20230708, "nope")


######
def prepare_dataset(
        channel_values: np.ndarray,
        input_steps: int,
        output_steps: int,
) -> TensorPairsDataset:
    def tensor_from(input: np.ndarray):
        return torch.from_numpy(input.astype(np.float32))

    patches = patchers.patch(channel_values, input_steps + output_steps, step=1)
    X, y = [(tensor_from(patch[:input_steps, 1:]), tensor_from(patch[input_steps:, 0])) for patch in patches]
    return TensorPairsDataset(X, y)


if __name__ == "__main__":
    dd = CoBot20230708(None, None)
    print('f')

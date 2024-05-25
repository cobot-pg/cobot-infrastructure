import json
import time
import typing

# import evaluation.forecasting_metrics as fm
import numpy as np
import pandas as pd
import torch
from torch.utils import data

from cobot_ml import detectors
from cobot_ml.data import datasets, patchers
from cobot_ml.data.datasets import DatasetInputData
from cobot_ml.training import runners


def dumps_file(path, _object):
    with open(path, "w") as params_file:
        json.dump(_object, params_file, indent=4)


def plot_results(
        title: str,
        real_values: np.ndarray,
        predictions: np.ndarray,
) -> None:
    import plotly.express as px
    fig = px.line(pd.DataFrame(dict(
        real=real_values,
        predictions=predictions,
        error=np.abs(predictions - real_values))))
    fig.show()


def unravel_vector(vector: torch.Tensor) -> np.ndarray:
    return torch.cat([vector[:-1, 0], vector[-1, :]]).detach().cpu().numpy()


def prepare_dataset(
        channel_values: typing.Union[pd.DataFrame, np.ndarray],
        input_steps: int,
        output_steps: int,
) -> datasets.TensorPairsDataset:
    channel_values = detectors.pad_beginning(channel_values, input_steps)
    patches = patchers.patch_with_stride(
        channel_values, input_steps + output_steps, stride=1
    )
    patches = [torch.from_numpy(patch.astype(np.float32)) for patch in patches]
    X = [patch[:input_steps, 1:] for patch in patches]
    y = [patch[input_steps:, 0] for patch in patches]
    return datasets.TensorPairsDataset(X, y)


def run_prediction(model_path: str,
                   input_steps: int,
                   output_steps: int,
                   dataset_name: str,
                   channel_name: str,
                   batch_size: int):
    device = torch.device("cpu")
    model = torch.load(model_path, map_location=device)

    dataset_ = DatasetInputData.create(dataset_name)

    metrics = dict()

    name, cols, chdata = dataset_.channel(channel_name)
    ds = prepare_dataset(chdata, input_steps, output_steps)

    beg = time.time()
    predictions = runners.run_inference(
        model,
        data.DataLoader(ds, batch_size=batch_size),
        device=device,
    )
    fin = time.time()

    y_pred = unravel_vector(predictions)[input_steps:]
    real_values = np.array(ds.get_unraveled_targets())[input_steps:]

    plot_results(
        channel_name,
        real_values,
        y_pred,
    )
    if channel_name not in metrics:
        metrics[channel_name] = dict()

    # metrics[channel_name]["mse"] = float(fm.mse(real_values, y_pred))
    # metrics[channel_name]["mae"] = float(fm.mae(real_values, y_pred))
    # metrics[channel_name]["mape"] = float(fm.mape(real_values, y_pred))
    # metrics[channel_name]["smape"] = float(fm.smape(real_values, y_pred))
    # metrics[channel_name]["timing"] = float(fin - beg)

    return metrics
    # dumps_file(os.path.join(output_path, f"metrics.json"), metrics)


from typing import List, Callable


class StepByStepPredictor:

    def __init__(self,
                 model_file: str, device: str,
                 columns: List[str],
                 preprocessing: Callable[[np.ndarray], np.ndarray],
                 ):
        self.model = torch.load(model_file, map_location=device)
        self.model.to(device)
        self.model.eval()

        self.columns = columns
        self.preprocessing = preprocessing
        self.device = device

        self.feature_count = len(columns)

        print(f"Model loaded from {model_file} to device {device}.")
        print(f"Feature count: {self.feature_count}.")

    def get_columns(self):
        """
        Intended for calling code to validate and / or adjust list of features passed to step()
        """
        return self.columns

    def step(self, input_data: np.ndarray) -> np.ndarray:
        """
        input_data should be a 3D array [B, H, F], where:
          B is for batching (can be 1)
          H is history window size
          F stands for features.

        returns an array of size [B, output_size], where:
          B is same as in input_data
          output_size is a length of an output sequence defined in the model
        """
        assert len(input_data.shape) == 3, "Input data should be a 2D array [B, H, F]."
        _, _, F = input_data.shape
        assert F == self.feature_count, f"Expected {self.feature_count} features, got {F}."

        preprocessed_data = self.preprocessing(input_data)

        input_tensor = torch.from_numpy(preprocessed_data).float().to(self.device)
        with torch.no_grad():
            output_tensor = self.model(input_tensor)

        return output_tensor.cpu().numpy()

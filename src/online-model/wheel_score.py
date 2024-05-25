# 20240310_wheel_problems_july_august_2023.py

import os
from typing import List, Callable
import json
from inference_schema.schema_decorators import input_schema, output_schema
from inference_schema.parameter_types.standard_py_parameter_type import StandardPythonParameterType

import joblib
import numpy as np

class Preprocessor:
    def __init__(self, preprocessing_path):
        self.scaler = joblib.load(preprocessing_path)

    def preprocessing(self, input_data):
        B, H, F = input_data.shape
        reshaped = input_data.reshape(-1, F)
        scaled_data = self.scaler.transform(reshaped)
        scaled_data = scaled_data.reshape(B, H, F)
        return scaled_data

class ClassifierStepByStepPredictor:

    def __init__(self,
                 model_file: str,
                 columns: List[str],
                 preprocessing: Callable[[np.ndarray], np.ndarray],
                 ):
        self.model = joblib.load(model_file)
        self.columns = columns
        self.preprocessing = preprocessing
        self.feature_count = len(columns)

        print(f"Model loaded from {model_file}.")
        print(f"Feature count: {self.feature_count}.")

    def get_columns(self):
        """
        Intended for calling code to validate and / or adjust list of features passed to step()
        """
        return self.columns

    def step(self, input_data: np.ndarray) -> np.ndarray:
        """
        input_data should be a 3D array [B, 1, F], where:
          B is for batching (can be 1)
          F stands for features.

        returns an array of size [B,] where B is same as in input_data
        """
        assert len(input_data.shape) == 3, "Input data should be a 2D array [B, H, F]."
        N, D, F = input_data.shape
        assert F == self.feature_count, f"Expected {self.feature_count} features, got {F}."
        assert D == 1, f"No history expected here, got {D} elements of history."

        preprocessed_data = self.preprocessing(input_data)
        output = self.model.predict(preprocessed_data.reshape(N, F))
        return output


selected_columns = [
    'FH.6000.[NNS] - Natural Navigation Signals.Difference heading average correction',
    'FH.6000.[NNS] - Natural Navigation Signals.Distance average correction',
]


def init():
    global model_wrapper
    preprocessing_file_path = os.path.join(str(os.getenv("AZUREML_MODEL_DIR")), "model/20240310_wheel_problems_july_august_2023.scaler.dump")
    preprocess = Preprocessor(preprocessing_file_path)
    preprocessing = preprocess.preprocessing

    model_file_path = os.path.join(str(os.getenv("AZUREML_MODEL_DIR")), "model/20240310_wheel_problems_july_august_2023.RF.dump")
    model_wrapper = ClassifierStepByStepPredictor(model_file_path, selected_columns, preprocessing)

    print("Init completed")

standard_sample_input = StandardPythonParameterType({
    'nn_diff_heading_avg_correction': 1.0,
    'nn_distance_avg_correction': 1.0,
})
sample_input = StandardPythonParameterType({
    'record': [standard_sample_input],
})

sample_output = StandardPythonParameterType([1.0])

@input_schema('Inputs', sample_input)
@output_schema(sample_output)
def run(Inputs):
    print("Received request")
    print("Received raw data")
    print(Inputs)
    input_data = np.zeros((1, 1, 2))
    input_data[0] = np.array([[Inputs["record"][0]["nn_diff_heading_avg_correction"], Inputs["record"][0]["nn_distance_avg_correction"]]])

    print("Input data")
    print(input_data)
    output_data = model_wrapper.step(input_data)
    print(output_data[0])
    print("Finished")
    return output_data.tolist()



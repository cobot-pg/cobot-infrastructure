# 20240306_overload_prediction_october_2022.py

from inference_schema.schema_decorators import input_schema, output_schema
from inference_schema.parameter_types.standard_py_parameter_type import StandardPythonParameterType

import os
import numpy as np
import torch
import json

from cobot_ml.inference_utilities import StepByStepPredictor
from sklearn.preprocessing import StandardScaler

selected_columns = [
    "FH.6000.[ENS] - Energy Signals.Momentary power consumption",
    "FH.6000.[ENS] - Energy Signals.Battery cell voltage",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - safety interlock",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - automatic permission",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - manual permission",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - command on",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - executed",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - in progress",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.ActualSpeed_L",
    "FH.6000.[G2PAS] GROUP 2 - PIN ACTUATOR SIGNALS.Pin Up - safety interlock",
    "FH.6000.[G2PAS] GROUP 2 - PIN ACTUATOR SIGNALS.Pin Up - automatic permission",
    "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - safety interlock",
    "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - automatic permission",
    "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - manual permission",
    "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - command on",
    "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.ActualSpeed_R",
    "FH.6000.[GS] GENERAL SIGNALS.Manual Mode active",
    "FH.6000.[GS] GENERAL SIGNALS.Automatic Mode active",
    "FH.6000.[GS] GENERAL SIGNALS.PLC fault active",
    "FH.6000.[GS] GENERAL SIGNALS.PLC warning Active",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 1 left - R",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 2 right - R",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 1 left - G",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 2 right - G",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 1 left - B",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 2 right - B",
    "FH.6000.[LED] LED STATUS.LED status - active mode",
    "FH.6000.[NNCF]3105 - Go to destination result.Destination ID",
    "FH.6000.[NNCF]3105 - Go to destination result.Go to result",
    "FH.6000.[NNCF]3106 - Pause drive result.Pause result",
    "FH.6000.[NNCF]3107 - Resume drive result.Destination ID",
    "FH.6000.[NNCF]3107 - Resume drive result.Resume result",
    "FH.6000.[NNCF]3108 - Abort drive result.Abort result",
    "FH.6000.[NNS] - Natural Navigation Signals.Natural Navigation status",
    "FH.6000.[NNS] - Natural Navigation Signals.Error status",
    "FH.6000.[NNS] - Natural Navigation Signals.Natural Navigation state",
    "FH.6000.[NNS] - Natural Navigation Signals.X-coordinate",
    "FH.6000.[NNS] - Natural Navigation Signals.Y-coordinate",
    "FH.6000.[NNS] - Natural Navigation Signals.Heading",
    "FH.6000.[NNS] - Natural Navigation Signals.Position confidence",
    "FH.6000.[NNS] - Natural Navigation Signals.Speed",
    "FH.6000.[NNS] - Natural Navigation Signals.Going to ID",
    "FH.6000.[NNS] - Natural Navigation Signals.Target reached",
    "FH.6000.[NNS] - Natural Navigation Signals.Current segment",
    "FH.6000.[ODS] - Odometry Signals.Momentary frequency of left encoder pulses",
    "FH.6000.[ODS] - Odometry Signals.Momentary frequency of right encoder pulses",
    "FH.6000.[ODS] - Odometry Signals.Cumulative distance left",
    "FH.6000.[ODS] - Odometry Signals.Cumulative distance right",
    "FH.6000.[SS] SAFETY SIGNALS.Safety circuit closed",
    "FH.6000.[SS] SAFETY SIGNALS.Scanners muted",
    "FH.6000.[SS] SAFETY SIGNALS.Front bumper triggered",
    "FH.6000.[SS] SAFETY SIGNALS.Front scanner safety zone violated",
    "FH.6000.[SS] SAFETY SIGNALS.Rear scanner safety zone violated",
    "FH.6000.[SS] SAFETY SIGNALS.Front scanner warning zone violated",
    "FH.6000.[SS] SAFETY SIGNALS.Rear scanner warning zone violated",
    "FH.6000.[SS] SAFETY SIGNALS.Scanners active zones",
]


class Preprocessor:
    def __init__(self):
        ds_mean = [3.31105838e+02, 4.65558587e+04, 9.86886105e-01, 9.99959712e-01, 4.02884654e-05, 8.12396761e-01,
                   8.12396761e-01, 8.12396761e-01, -1.11133717e+00, 9.99979856e-01, 9.99979856e-01, 9.86886105e-01,
                   9.99979856e-01, 4.02884654e-05, 9.99979856e-01, -1.04385399e+00, 4.02884654e-05, 9.99959712e-01,
                   1.80290883e-02, 4.63720237e-02, 1.39236936e-01, 5.88413037e-02, 1.29607993e-01, 4.92123605e-02,
                   5.65992506e-01, 6.47334918e-01, 1.10134161e+01, 2.42615124e+00, 1.44857177e-01, 2.42615124e+00,
                   2.42615124e+00, 1.44857177e-01, 2.42615124e+00, 9.99939567e-01, 2.01442327e-05, 2.97353048e+00,
                   3.59695176e+01, 2.15484972e+01, 3.10005953e-01, 9.49589058e+01, -1.49215925e-03, 2.42615124e+00,
                   1.44857177e-01, 3.58947867e+01, 5.52664820e+02, -2.16881673e+01, 1.31313718e+03, 1.41154400e+03,
                   9.86886105e-01, 4.02884654e-05, 9.98025865e-01, 9.92123605e-01, 9.95850288e-01, 9.73006728e-01,
                   9.69300189e-01, 1.00036260e+00]

        ds_scale = [7.36188028e+01, 1.76534683e+03, 1.13762565e-01, 6.34719168e-03, 6.34719168e-03, 3.90395010e-01,
                    3.90395010e-01, 3.90395010e-01, 1.58810218e+02, 4.48818749e-03, 4.48818749e-03, 1.13762565e-01,
                    4.48818749e-03, 6.34719168e-03, 4.48818749e-03, 1.70070154e+02, 6.34719168e-03, 6.34719168e-03,
                    1.33056530e-01, 2.10289465e-01, 3.46193605e-01, 2.35327441e-01, 3.35871644e-01, 2.16311128e-01,
                    4.95625856e-01, 4.77799563e-01, 4.67716683e+01, 1.13597312e+00, 3.51956781e-01, 1.13597312e+00,
                    1.13597312e+00, 3.51956781e-01, 1.13597312e+00, 7.77361216e-03, 4.48818749e-03, 8.99095282e-01,
                    6.72389880e+00, 3.93929876e+00, 1.72140102e+00, 4.32073508e+00, 2.09424149e-01, 1.13597312e+00,
                    3.51956781e-01, 2.02493508e+01, 1.83045140e+04, 1.80255817e+04, 7.25428908e+02, 7.82406606e+02,
                    1.13762565e-01, 6.34719168e-03, 4.43873585e-02, 8.83988540e-02, 6.42844602e-02, 1.62063676e-01,
                    1.72503137e-01, 5.71247251e-02]

        ds_var = [5.41972813e+03, 3.11644942e+06, 1.29419212e-02, 4.02868423e-05, 4.02868423e-05, 1.52408264e-01,
                  1.52408264e-01, 1.52408264e-01, 2.52206853e+04, 2.01438269e-05, 2.01438269e-05, 1.29419212e-02,
                  2.01438269e-05, 4.02868423e-05, 2.01438269e-05, 2.89238573e+04, 4.02868423e-05, 4.02868423e-05,
                  1.77040402e-02, 4.42216591e-02, 1.19850012e-01, 5.53790047e-02, 1.12809761e-01, 4.67905041e-02,
                  2.45644989e-01, 2.28292422e-01, 2.18758896e+03, 1.29043492e+00, 1.23873576e-01, 1.29043492e+00,
                  1.29043492e+00, 1.23873576e-01, 1.29043492e+00, 6.04290460e-05, 2.01438269e-05, 8.08372327e-01,
                  4.52108151e+01, 1.55180747e+01, 2.96322148e+00, 1.86687516e+01, 4.38584744e-02, 1.29043492e+00,
                  1.23873576e-01, 4.10036209e+02, 3.35055234e+08, 3.24921596e+08, 5.26247101e+05, 6.12160097e+05,
                  1.29419212e-02, 4.02868423e-05, 1.97023760e-03, 7.81435739e-03, 4.13249183e-03, 2.62646351e-02,
                  2.97573323e-02, 3.26323422e-03]

        self.weights = [
            0.94434573, 1.05775119, 0.98145535, 0.88252097, 1.59831661, 0.20711831, 1.82091174,
            0.62167594, 0.70944001, 1.56842617, 0.92145948, 0.80771739, 0.21285017, -1.75739862,
            2.88456252, 0.21929224, -0.46961886, 0.82098079, 1.27824626, 0.30006528, 0.23129348,
            0.67005413, 0.51058337, 0.77160606, -1.43119529, 0.93059645, 1.49700404, 0.80177857,
            0.50795383, 0.97205259, 1.97306834, 0.90645151, 1.14622803, 0.92498906, 0.580554,
            0.62725778, 1.10432259, 0.0972941, 0.02687283, 0.56381115, -1.19465716, 0.56049716,
            0.19689367, 0.79387506, -1.77186096, 0.10502172, 0.08165884, 0.26459102, 0.22519161,
            0.81502814, 0.13262141, 1.001232, 0.83051719, 1.84447032, 0.36032435, 0.43090188
        ]

        self.scaler = StandardScaler()
        self.scaler.mean_ = np.array(ds_mean)
        self.scaler.scale_ = np.array(ds_scale)
        self.scaler.var_ = np.array(ds_var)

    def preprocessing(self, input_data):
        B, H, F = input_data.shape
        reshaped = input_data.reshape(-1, F)
        scaled_data = self.scaler.transform(reshaped)
        scaled_data = scaled_data.reshape(B, H, F)
        return scaled_data * self.weights


def init():
    global model_wrapper
    preprocess = Preprocessor()
    preprocessing = preprocess.preprocessing
    model_file_path = os.path.join(str(os.getenv("AZUREML_MODEL_DIR")), "model/mpc_200_model.pt")

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    model_wrapper = StepByStepPredictor(model_file_path, device=device,
                                    columns=selected_columns,
                                    preprocessing=preprocessing)
    print("Init completed")


standard_sample_input = StandardPythonParameterType({
    'data': 's',
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

    input_data = np.zeros((1, 50, 56))
    try:
        input_data[0] = np.array(json.loads(Inputs["record"][0]["data"]))
    except Exception as e:
        print('Encountered error, fallback to 0', e)
        # TODO: Address this hack
        return [0.0]

    print("Input data")
    print(input_data)
    output_data = model_wrapper.step(input_data)
    print(output_data[0])
    print("Finished")
    return [(float(output_data[0][0]) * 73.6188028) + 331.105838]



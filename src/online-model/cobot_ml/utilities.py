import json

import numpy as np


def get_windows_limits_idxs(y: np.ndarray):
    """
    Returns tuple containing indices of windows beginning and end
    :param y: Array with labels
    :return tuple with 2 lists, first one containing indices of windows start
    and the second one with indices of windows stop.
    """
    anomalies_start = []
    anomalies_stop = []
    previous = False
    for idx, is_anomaly in enumerate(y):
        if not previous and is_anomaly:  # 0 --> 1
            anomalies_start.append(idx)
        elif previous and not is_anomaly:  # 1 --> 0
            anomalies_stop.append(idx - 1)
        previous = is_anomaly
    if previous:
        anomalies_stop.append(len(y) - 1)
    return anomalies_start, anomalies_stop


def create_01_mask_in_ranges(desired_mask_length: int, ranges):
    """
    Creates a 1D 0-1 mask with 1-s in ranges and 0 elsewhere.
    :param desired_mask_length: length of mask to be created
    :param ranges: pairs of range boundaries
    :return 1D int ndarray
    """
    result = np.zeros(shape=(desired_mask_length,), dtype=int)
    for _range in ranges:
        result[_range[0]: _range[1]] = 1
    return result


class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """

    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32,
                              np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def dumps_file(path, _object):
    with open(path, "w") as params_file:
        json.dump(_object, params_file, indent=4, cls=NumpyEncoder)

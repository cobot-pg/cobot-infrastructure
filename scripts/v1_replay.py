import csv
import json
import time
from azure.iot.device import IoTHubDeviceClient, Message


def read_csv_to_list_of_dicts(csv_file, columns_mapping):
    data = []
    with open(csv_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            filtered_row = {newcol: row[col] for col, newcol in columns_mapping.items()}
            data.append(filtered_row)
    return data

def cast_dictionary_values(input_dict, target_types):
    return {key: target_types[key](value) for key, value in input_dict.items()}


csv_file = 'data/v1_replay.csv'

def bool_to_int(value):
    return 1 if value == 'true' else 0

AGV_ID = 'AGV_1'
AGV_TYPE = 'v1'
CONNECTION_STRING = "<CONNECTION_STRING>"

# Map columns to shorter names to save on payload size
columns_mapping = {
    "isoTimestamp": "ts",
    "FH.6000.[ENS] - Energy Signals.Momentary power consumption": "momentary_power_consumption",
    "FH.6000.[ENS] - Energy Signals.Battery cell voltage": "battery_cell_voltage",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - safety interlock": "left_safety_interlock",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - automatic permission": "left_auto_permission",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - manual permission": "left_manual_permission",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - command on": "left_command_on",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - executed": "left_executed",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - in progress": "left_in_progress",
    "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.ActualSpeed_L": "left_actual_speed",
    "FH.6000.[G2PAS] GROUP 2 - PIN ACTUATOR SIGNALS.Pin Up - safety interlock": "pin_up_safety_interlock",
    "FH.6000.[G2PAS] GROUP 2 - PIN ACTUATOR SIGNALS.Pin Up - automatic permission": "pin_up_auto_permission",
    "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - safety interlock": "right_safety_interlock",
    "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - automatic permission": "right_auto_permission",
    "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - manual permission": "right_manual_permission",
    "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - command on": "right_command_on",
    "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.ActualSpeed_R": "right_actual_speed",
    "FH.6000.[GS] GENERAL SIGNALS.Manual Mode active": "manual_mode_active",
    "FH.6000.[GS] GENERAL SIGNALS.Automatic Mode active": "auto_mode_active",
    "FH.6000.[GS] GENERAL SIGNALS.PLC fault active": "plc_fault_active",
    "FH.6000.[GS] GENERAL SIGNALS.PLC warning Active": "plc_warning_active",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 1 left - R": "led_rgb_strip_1_left_r",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 2 right - R": "led_rgb_strip_2_right_r",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 1 left - G": "led_rgb_strip_1_left_g",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 2 right - G": "led_rgb_strip_2_right_g",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 1 left - B": "led_rgb_strip_1_left_b",
    "FH.6000.[LED] LED STATUS.LED RGB Strip 2 right - B": "led_rgb_strip_2_right_b",
    "FH.6000.[LED] LED STATUS.LED status - active mode": "led_status_active_mode",
    "FH.6000.[NNCF]3105 - Go to destination result.Destination ID": "go_to_destination_id",
    "FH.6000.[NNCF]3105 - Go to destination result.Go to result": "go_to_result",
    "FH.6000.[NNCF]3106 - Pause drive result.Pause result": "pause_result",
    "FH.6000.[NNCF]3107 - Resume drive result.Destination ID": "resume_destination_id",
    "FH.6000.[NNCF]3107 - Resume drive result.Resume result": "resume_result",
    "FH.6000.[NNCF]3108 - Abort drive result.Abort result": "abort_result",
    "FH.6000.[NNS] - Natural Navigation Signals.Natural Navigation status": "natural_navigation_status",
    "FH.6000.[NNS] - Natural Navigation Signals.Error status": "error_status",
    "FH.6000.[NNS] - Natural Navigation Signals.Natural Navigation state": "natural_navigation_state",
    "FH.6000.[NNS] - Natural Navigation Signals.X-coordinate": "nn_x_coordinate",
    "FH.6000.[NNS] - Natural Navigation Signals.Y-coordinate": "nn_y_coordinate",
    "FH.6000.[NNS] - Natural Navigation Signals.Heading": "nn_heading",
    "FH.6000.[NNS] - Natural Navigation Signals.Position confidence": "nn_position_confidence",
    "FH.6000.[NNS] - Natural Navigation Signals.Speed": "nn_speed",
    "FH.6000.[NNS] - Natural Navigation Signals.Going to ID": "nn_going_to_id",
    "FH.6000.[NNS] - Natural Navigation Signals.Target reached": "nn_target_reached",
    "FH.6000.[NNS] - Natural Navigation Signals.Current segment": "nn_current_segment",
    "FH.6000.[ODS] - Odometry Signals.Momentary frequency of left encoder pulses": "momentary_freq_left_encoder",
    "FH.6000.[ODS] - Odometry Signals.Momentary frequency of right encoder pulses": "momentary_freq_right_encoder",
    "FH.6000.[ODS] - Odometry Signals.Cumulative distance left": "cumulative_distance_left",
    "FH.6000.[ODS] - Odometry Signals.Cumulative distance right": "cumulative_distance_right",
    "FH.6000.[SS] SAFETY SIGNALS.Safety circuit closed": "safety_circuit_closed",
    "FH.6000.[SS] SAFETY SIGNALS.Scanners muted": "scanners_muted",
    "FH.6000.[SS] SAFETY SIGNALS.Front bumper triggered": "front_bumper_triggered",
    "FH.6000.[SS] SAFETY SIGNALS.Front scanner safety zone violated": "front_scanner_safety_zone_violated",
    "FH.6000.[SS] SAFETY SIGNALS.Rear scanner safety zone violated": "rear_scanner_safety_zone_violated",
    "FH.6000.[SS] SAFETY SIGNALS.Front scanner warning zone violated": "front_scanner_warning_zone_violated",
    "FH.6000.[SS] SAFETY SIGNALS.Rear scanner warning zone violated": "rear_scanner_warning_zone_violated",
    "FH.6000.[SS] SAFETY SIGNALS.Scanners active zones": "scanners_active_zones",
}

csv_result = read_csv_to_list_of_dicts(csv_file, columns_mapping)

casting_mapping = {
    "ts": str,
    "momentary_power_consumption": float,
    "battery_cell_voltage": float,
    "left_safety_interlock": bool_to_int,
    "left_auto_permission": bool_to_int,
    "left_manual_permission": bool_to_int,
    "left_command_on": bool_to_int,
    "left_executed": bool_to_int,
    "left_in_progress": bool_to_int,
    "left_actual_speed": float,
    "pin_up_safety_interlock": bool_to_int,
    "pin_up_auto_permission": bool_to_int,
    "right_safety_interlock": bool_to_int,
    "right_auto_permission": bool_to_int,
    "right_manual_permission": bool_to_int,
    "right_command_on": bool_to_int,
    "right_actual_speed": float,
    "manual_mode_active": bool_to_int,
    "auto_mode_active": bool_to_int,
    "plc_fault_active": bool_to_int,
    "plc_warning_active": bool_to_int,
    "led_rgb_strip_1_left_r": bool_to_int,
    "led_rgb_strip_2_right_r": bool_to_int,
    "led_rgb_strip_1_left_g": bool_to_int,
    "led_rgb_strip_2_right_g": bool_to_int,
    "led_rgb_strip_1_left_b": bool_to_int,
    "led_rgb_strip_2_right_b": bool_to_int,
    "led_status_active_mode": bool_to_int,
    "go_to_destination_id": int,
    "go_to_result": int,
    "pause_result": int,
    "resume_destination_id": int,
    "resume_result": int,
    "abort_result": int,
    "natural_navigation_status": bool_to_int,
    "error_status": bool_to_int,
    "natural_navigation_state": int,
    "nn_x_coordinate": float,
    "nn_y_coordinate": float,
    "nn_heading": float,
    "nn_position_confidence": float,
    "nn_speed": float,
    "nn_going_to_id": int,
    "nn_target_reached": int,
    "nn_current_segment": int,
    "momentary_freq_left_encoder": float,
    "momentary_freq_right_encoder": float,
    "cumulative_distance_left": float,
    "cumulative_distance_right": float,
    "safety_circuit_closed": bool_to_int,
    "scanners_muted": bool_to_int,
    "front_bumper_triggered": bool_to_int,
    "front_scanner_safety_zone_violated": bool_to_int,
    "rear_scanner_safety_zone_violated": bool_to_int,
    "front_scanner_warning_zone_violated": bool_to_int,
    "rear_scanner_warning_zone_violated": bool_to_int,
    "scanners_active_zones": float,
}


mapped_results = [cast_dictionary_values(row, casting_mapping) for row in csv_result]

azure_iot_client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
azure_iot_client.connect()

prev_row_ts = None
for row in mapped_results:
    if row['ts'] == prev_row_ts:
        print('Skipped duplicate record')
        continue

    message = Message(json.dumps({
        "agv_id": AGV_ID,
        "agv_type": AGV_TYPE,
        **row,
    }))

    time.sleep(1)
    prev_row_ts = row['ts']
    azure_iot_client.send_message(message)
    print(f"Message sent: {message}")

azure_iot_client.disconnect()


CREATE TABLE agv_data (
    id SERIAL PRIMARY KEY,
    agv_id VARCHAR(50),
    agv_type VARCHAR(50),
    ts TIMESTAMP WITH TIME ZONE,
    momentary_power_consumption NUMERIC,
    battery_cell_voltage NUMERIC,
    left_safety_interlock NUMERIC,
    left_auto_permission NUMERIC,
    left_manual_permission NUMERIC,
    left_command_on NUMERIC,
    left_executed NUMERIC,
    left_in_progress NUMERIC,
    left_actual_speed NUMERIC,
    pin_up_safety_interlock NUMERIC,
    pin_up_auto_permission NUMERIC,
    right_safety_interlock NUMERIC,
    right_auto_permission NUMERIC,
    right_manual_permission NUMERIC,
    right_command_on NUMERIC,
    right_actual_speed NUMERIC,
    manual_mode_active NUMERIC,
    auto_mode_active NUMERIC,
    plc_fault_active NUMERIC,
    plc_warning_active NUMERIC,
    led_rgb_strip_1_left_r NUMERIC,
    led_rgb_strip_2_right_r NUMERIC,
    led_rgb_strip_1_left_g NUMERIC,
    led_rgb_strip_2_right_g NUMERIC,
    led_rgb_strip_1_left_b NUMERIC,
    led_rgb_strip_2_right_b NUMERIC,
    led_status_active_mode NUMERIC,
    go_to_destination_id NUMERIC,
    go_to_result NUMERIC,
    pause_result NUMERIC,
    resume_destination_id NUMERIC,
    resume_result NUMERIC,
    abort_result NUMERIC,
    natural_navigation_status NUMERIC,
    error_status NUMERIC,
    natural_navigation_state NUMERIC,
    nn_x_coordinate NUMERIC,
    nn_y_coordinate NUMERIC,
    nn_heading NUMERIC,
    nn_position_confidence NUMERIC,
    nn_speed NUMERIC,
    nn_going_to_id NUMERIC,
    nn_target_reached NUMERIC,
    nn_current_segment NUMERIC,
    momentary_freq_left_encoder NUMERIC,
    momentary_freq_right_encoder NUMERIC,
    cumulative_distance_left NUMERIC,
    cumulative_distance_right NUMERIC,
    safety_circuit_closed NUMERIC,
    scanners_muted NUMERIC,
    front_bumper_triggered NUMERIC,
    front_scanner_safety_zone_violated NUMERIC,
    rear_scanner_safety_zone_violated NUMERIC,
    front_scanner_warning_zone_violated NUMERIC,
    rear_scanner_warning_zone_violated NUMERIC,
    scanners_active_zones NUMERIC,
    nn_diff_heading_avg_correction NUMERIC,
    nn_distance_avg_correction NUMERIC
);

CREATE INDEX idx_agv_id ON agv_data (agv_id);
CREATE INDEX idx_ts ON agv_data (ts);

CREATE TABLE agv_wheel_anomaly (
    id SERIAL PRIMARY KEY,
    agv_id VARCHAR(50),
    ts TIMESTAMP WITH TIME ZONE,
    wheel_anomaly NUMERIC
);

CREATE INDEX idx_wheel_agv_id ON agv_wheel_anomaly (agv_id);
CREATE INDEX idx_wheel_ts ON agv_wheel_anomaly (ts);


CREATE TABLE agv_predicted_mpc (
  id SERIAL PRIMARY KEY,
  agv_id VARCHAR(50),
  ts TIMESTAMP WITH TIME ZONE,
  predicted_momentary_power_consumption NUMERIC
);

CREATE INDEX idx_mpc_agv_id ON agv_predicted_mpc (agv_id);
CREATE INDEX idx_mpc_ts ON agv_predicted_mpc (ts);


CREATE TABLE agv_segment_anomaly (
  id SERIAL PRIMARY KEY,
  agv_id VARCHAR(50),
  ts TIMESTAMP WITH TIME ZONE,
  segment_anomaly NUMERIC
);

CREATE INDEX idx_segment_agv_id ON agv_segment_anomaly (agv_id);
CREATE INDEX idx_segment_ts ON agv_segment_anomaly (ts);


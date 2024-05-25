"use strict";

const {
  OPCUAClient,
  MessageSecurityMode,
  SecurityPolicy,
  AttributeIds,
  DataType,
  VariantArrayType,
} = require("node-opcua");
const Protocol = require("azure-iot-device-mqtt").Mqtt;
const Client = require("azure-iot-device").Client;
const Message = require("azure-iot-device").Message;

const connectionStrategy = {
  initialDelay: 1000,
  maxRetry: 1,
};

const opcuaClient = OPCUAClient.create({
  applicationName: "TestClient",
  connectionStrategy,
  securityMode: MessageSecurityMode.None,
  securityPolicy: SecurityPolicy.None,
  endpoint_must_exist: false,
});

const deviceConnectionString = process.env.DEVICE_CONNECTION_STRING;
const endpointUrl = process.env.ENDPOINT_URL;
const AGV_ID = process.env.AGV_ID || "AGV_1";
const AGV_TYPE = process.env.AGV_TYPE || "v2";

const iothubClient = Client.fromConnectionString(
  deviceConnectionString,
  Protocol,
);

const zipArrays = (a, b) => a.map((k, i) => [k, b[i]]);

const getChildrenNodeList = async (session, rootNodeId) => {
  const rootNodeReferences = await session.browse({
    nodeId: rootNodeId,
  });

  return rootNodeReferences.references.map((item) => item.nodeId);
};

// Helper function for waiting before iterations
async function timeout(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Parse the result into a single object with all the values
// fetched from the OPC UA server
const parseResult = (item) => {
  const obj = {
    timestamp: item[0].sourceTimestamp.getTime(),
    isoTimestamp: item[0].sourceTimestamp.toISOString(),
    agv_id: AGV_ID,
    agv_type: AGV_TYPE,
  };

  for (const entry of item) {
    // Filter out an invalid node
    if (entry.name !== 61) {
      try {
        if (entry.value != null) {
          obj[entry.name] = entry.value.toString();
        } else {
          obj[entry.name] = "null";
        }
      } catch (e) {
        console.log("ENTRY", entry);
        // Continue with processing as it might be an intermittent error
      }
    }
  }

  return obj;
};

function boolToInt(value) {
  return value ? 1 : 0;
}

const castingMapping = {
  ts: String,
  momentary_power_consumption: parseFloat,
  battery_cell_voltage: parseFloat,
  left_safety_interlock: boolToInt,
  left_auto_permission: boolToInt,
  left_manual_permission: boolToInt,
  left_command_on: boolToInt,
  left_executed: boolToInt,
  left_in_progress: boolToInt,
  left_actual_speed: parseFloat,
  pin_up_safety_interlock: boolToInt,
  pin_up_auto_permission: boolToInt,
  right_safety_interlock: boolToInt,
  right_auto_permission: boolToInt,
  right_manual_permission: boolToInt,
  right_command_on: boolToInt,
  right_actual_speed: parseFloat,
  manual_mode_active: boolToInt,
  auto_mode_active: boolToInt,
  plc_fault_active: boolToInt,
  plc_warning_active: boolToInt,
  led_rgb_strip_1_left_r: boolToInt,
  led_rgb_strip_2_right_r: boolToInt,
  led_rgb_strip_1_left_g: boolToInt,
  led_rgb_strip_2_right_g: boolToInt,
  led_rgb_strip_1_left_b: boolToInt,
  led_rgb_strip_2_right_b: boolToInt,
  led_status_active_mode: boolToInt,
  go_to_destination_id: parseInt,
  go_to_result: parseInt,
  pause_result: parseInt,
  resume_destination_id: parseInt,
  resume_result: parseInt,
  abort_result: parseInt,
  natural_navigation_status: boolToInt,
  error_status: boolToInt,
  natural_navigation_state: parseInt,
  nn_x_coordinate: parseFloat,
  nn_y_coordinate: parseFloat,
  nn_heading: parseFloat,
  nn_position_confidence: parseFloat,
  nn_speed: parseFloat,
  nn_going_to_id: parseInt,
  nn_target_reached: parseInt,
  nn_current_segment: parseInt,
  momentary_freq_left_encoder: parseFloat,
  momentary_freq_right_encoder: parseFloat,
  cumulative_distance_left: parseFloat,
  cumulative_distance_right: parseFloat,
  safety_circuit_closed: boolToInt,
  scanners_muted: boolToInt,
  front_bumper_triggered: boolToInt,
  front_scanner_safety_zone_violated: boolToInt,
  rear_scanner_safety_zone_violated: boolToInt,
  front_scanner_warning_zone_violated: boolToInt,
  rear_scanner_warning_zone_violated: boolToInt,
  scanners_active_zones: parseFloat,
  nn_diff_heading_avg_correction: parseFloat,
  nn_distance_avg_correction: parseFloat,
};

const COLUMNS_MAPPING = {
  isoTimestamp: "ts",
  "FH.6000.[ENS] - Energy Signals.Momentary power consumption W":
    "momentary_power_consumption",
  "FH.6000.[ENS] - Energy Signals.Battery cell voltage": "battery_cell_voltage",
  "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - safety interlock":
    "left_safety_interlock",
  "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - automatic permission (#)":
    "left_auto_permission",
  "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - manual permission":
    "left_manual_permission",
  "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - command on":
    "left_command_on",
  "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - executed":
    "left_executed",
  "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.Left drive activate - in progress (#)":
    "left_in_progress",
  "FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS.ActualSpeed_L":
    "left_actual_speed",
  "FH.6000.[G2PAS] GROUP 2 - PIN ACTUATOR SIGNALS.Pin Up - safety interlock":
    "pin_up_safety_interlock",
  "FH.6000.[G2PAS] GROUP 2 - PIN ACTUATOR SIGNALS.Pin Up - automatic permission (#)":
    "pin_up_auto_permission",
  "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - safety interlock":
    "right_safety_interlock",
  "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - automatic permission (#)":
    "right_auto_permission",
  "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - manual permission":
    "right_manual_permission",
  "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.Right drive activate - command on":
    "right_command_on",
  "FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS.ActualSpeed_R":
    "right_actual_speed",
  "FH.6000.[GS] GENERAL SIGNALS.Manual Mode active": "manual_mode_active",
  "FH.6000.[GS] GENERAL SIGNALS.Automatic Mode active": "auto_mode_active",
  "FH.6000.[GS] GENERAL SIGNALS.PLC fault active": "plc_fault_active",
  "FH.6000.[GS] GENERAL SIGNALS.PLC warning Active": "plc_warning_active",
  "FH.6000.[LED] LED STATUS.LED RGB Strip 1 (left) - Red":
    "led_rgb_strip_1_left_r",
  "FH.6000.[LED] LED STATUS.LED RGB Strip 2 (right) – Red":
    "led_rgb_strip_2_right_r",
  "FH.6000.[LED] LED STATUS.LED RGB Strip 1 (left) – Green":
    "led_rgb_strip_1_left_g",
  "FH.6000.[LED] LED STATUS.LED RGB Strip 2 (right) – Green":
    "led_rgb_strip_2_right_g",
  "FH.6000.[LED] LED STATUS.LED RGB Strip 1 (left) – Blue":
    "led_rgb_strip_1_left_b",
  "FH.6000.[LED] LED STATUS.LED RGB Strip 2 (right) – Blue":
    "led_rgb_strip_2_right_b",
  "FH.6000.[LED] LED STATUS.LED status - active mode": "led_status_active_mode",
  "FH.6000.[NNS] - Natural Navigation Signals.Natural Navigation status":
    "natural_navigation_status",
  "FH.6000.[NNS] - Natural Navigation Signals.Error status": "error_status",
  "FH.6000.[NNS] - Natural Navigation Signals.Natural Navigation state":
    "natural_navigation_state",
  "FH.6000.[NNS] - Natural Navigation Signals.X-coordinate": "nn_x_coordinate",
  "FH.6000.[NNS] - Natural Navigation Signals.Y-coordinate": "nn_y_coordinate",
  "FH.6000.[NNS] - Natural Navigation Signals.Heading": "nn_heading",
  "FH.6000.[NNS] - Natural Navigation Signals.Position confidence":
    "nn_position_confidence",
  "FH.6000.[NNS] - Natural Navigation Signals.Speed": "nn_speed",
  "FH.6000.[NNS] - Natural Navigation Signals.Going to ID": "nn_going_to_id",
  "FH.6000.[NNS] - Natural Navigation Signals.Target reached":
    "nn_target_reached",
  "FH.6000.[NNS] - Natural Navigation Signals.Current segment":
    "nn_current_segment",
  "FH.6000.[ODS] - Odometry Signals.Momentary frequency of left encoder pulses":
    "momentary_freq_left_encoder",
  "FH.6000.[ODS] - Odometry Signals.Momentary frequency of right encoder pulses":
    "momentary_freq_right_encoder",
  "FH.6000.[ODS] - Odometry Signals.Cumulative distance left":
    "cumulative_distance_left",
  "FH.6000.[ODS] - Odometry Signals.Cumulative distance right":
    "cumulative_distance_right",
  "FH.6000.[SS] SAFETY SIGNALS.Safety circuit closed": "safety_circuit_closed",
  "FH.6000.[SS] SAFETY SIGNALS.Scanners muted": "scanners_muted",
  "FH.6000.[NNS] - Natural Navigation Signals.Difference heading average correction":
    "nn_diff_heading_avg_correction",
  "FH.6000.[NNS] - Natural Navigation Signals.Distance average correction":
    "nn_distance_avg_correction",
};

// Map object to a new result with simplified, established structure
const mapResult = (result) => {
  const mappedData = {};
  for (const [key, value] of Object.entries(result)) {
    const newKey = COLUMNS_MAPPING[key] || key;
    const castFunction = castingMapping[newKey];
    mappedData[newKey] = castFunction(value);
  }
  return mappedData;
};

// Process the result - send to Azure IoT Hub
const processResult = async (iothubClient, result) => {
  const message = new Message(JSON.stringify(result));
  iothubClient.sendEvent(message);
};

async function main() {
  try {
    console.log("Connecting to: ", endpointUrl);
    opcuaClient.connect(endpointUrl);
    const session = await opcuaClient.createSession();
    console.log("Connected to: ", endpointUrl);

    console.log("Connecting to Azure IoT Hub");
    await iothubClient.open();
    console.log("Connecting to Azure IoT Hub");

    // List of root nodes to read - all the data is stored under these nodes
    const rootNodeIds = [
      "ns=4;s=FH.6000.[AI] - ALARM INFORMATION",
      "ns=4;s=FH.6000.[CRENS] - Collaborative Robot Energy Signals",
      "ns=4;s=FH.6000.[CRF] - Collaborative Robot Feedback",
      "ns=4;s=FH.6000.[ENS] - Energy Signals",
      "ns=4;s=FH.6000.[ES] EXCLUSIONS STATUSES",
      "ns=4;s=FH.6000.[G1BS] GROUP 1 - BRAKES SIGNALS",
      "ns=4;s=FH.6000.[G1LDS] GROUP 1 - LEFT DRIVE SIGNALS",
      "ns=4;s=FH.6000.[G2PAS] GROUP 2 - PIN ACTUATOR SIGNALS",
      "ns=4;s=FH.6000.[G2RDS] GROUP 2 - RIGHT DRIVE SIGNALS",
      "ns=4;s=FH.6000.[G3LPS] GROUP 3 - LIGTING PLATE SIGNALS",
      "ns=4;s=FH.6000.[GS] GENERAL SIGNALS",
      "ns=4;s=FH.6000.[IS] - Inclination Signals",
      "ns=4;s=FH.6000.[LED] LED STATUS",
      "ns=4;s=FH.6000.[MI] - MESSAGE INFORMATION",
      "ns=4;s=FH.6000.[NNCF] - Natural Navigation Command Feedback",
      "ns=4;s=FH.6000.[NNS] - Natural Navigation Signals",
      "ns=4;s=FH.6000.[ODS] - Odometry Signals",
      "ns=4;s=FH.6000.[OS] OTHER STATUSES",
      "ns=4;s=FH.6000.[SS] SAFETY SIGNALS",
      "ns=4;s=FH.6000.[TS] TIME STAMP",
      "ns=4;s=FH.6000.[WI] - WARNING INFORMATION",
      "ns=4;s=FH.6000.[WS] WEIGHT STATUSES",
      "ns=4;s=FH.6100.[BC] BRAKES CONTROL",
      "ns=4;s=FH.6100.[EC] EXCLUSIONS CONTROL",
      "ns=4;s=FH.6100.[GSC] GENERAL SIGNALS CONTROL",
      "ns=4;s=FH.6100.[LEDC] LED CONTROL",
      "ns=4;s=FH.6100.[LPC] LIFTING PLATE CONTROL",
      "ns=4;s=FH.6100.[MC] - Manual Control",
      "ns=4;s=FH.6100.[NNC] - Natural Navigation Command",
      "ns=4;s=FH.6100.[NNC]3005 - Go to destination",
      "ns=4;s=FH.6100.[PAC] PIN ACTUATOR CONTROL",
      "ns=4;s=FH.6100.[SDC] - Single Drive Control",
      "ns=4;s=FH.6100.[SSC] SAFETY SIGNALS CONTROL",
      "ns=4;s=FH.6100.[TS] TIME STAMP",
    ];

    const nodeIds = [];
    for (const nodeId of rootNodeIds) {
      nodeIds.push(...(await getChildrenNodeList(session, nodeId)));
    }

    while (true) {
      const valuesResponse = await session.read(nodeValueRequestList);
      const result = zipArrays(nodeIds, valuesResponse).map(
        ([nodeId, valueResponse]) => ({
          name: nodeId.value,
          value: valueResponse.value.value,
          sourceTimestamp: valueResponse.sourceTimestamp,
        }),
      );

      const parsedResult = parseResult(result);
      const mappedResult = mapResult(parsedResult);

      // Just start a promise, the sending can be done in the background
      processResult(mappedResult);

      // The data is read every 500 ms - the update on OPC UA server should be either 500 ms or 1 s
      await timeout(500);
    }

    const nodeValueRequestList = nodeIds.map((nodeId) => ({
      nodeId,
      attributeId: AttributeIds.Value,
    }));

    await session.close();

    await opcuaClient.disconnect();
    console.log("Disconnected from: ", endpointUrl);
  } catch (err) {
    console.log("An error has occured : ", err);
  }
}

main();

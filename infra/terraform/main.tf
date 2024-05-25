terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0.2"
    }
  }
  required_version = ">= 1.1.0"
}

provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "azurerm_application_insights" "ml_workspace_insights" {
  name                = "cobotmlworkspaceinsights"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
}

resource "azurerm_key_vault" "ml_workspace_keyvault" {
  name                = "cobotmlworkspacekeyvault"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"
}

resource "azurerm_storage_account" "ml_workspace_storage_account" {
  name                     = "cobotmlworkspacestorage"
  location                 = azurerm_resource_group.rg.location
  resource_group_name      = azurerm_resource_group.rg.name
  account_tier             = "Standard"
  account_replication_type = "GRS"
}

resource "azurerm_machine_learning_workspace" "ml_workspace" {
  name                    = "cobotmlworkspace"
  location                = azurerm_resource_group.rg.location
  resource_group_name     = azurerm_resource_group.rg.name
  application_insights_id = azurerm_application_insights.ml_workspace_insights.id
  key_vault_id            = azurerm_key_vault.ml_workspace_keyvault.id
  storage_account_id      = azurerm_storage_account.ml_workspace_storage_account.id

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_iothub" "iothub" {
  name                          = var.iothub_name
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  event_hub_partition_count     = "2"
  event_hub_retention_in_days   = "1"
  public_network_access_enabled = true

  sku {
    name     = "B1"
    capacity = "1"
  }

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "azurerm_storage_account" "storage_account" {
  name                = var.storage_account_name
  resource_group_name = azurerm_resource_group.rg.name
  location = azurerm_resource_group.rg.location

  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled = true

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "azurerm_storage_container" "storage_container" {
  name                  = var.storage_container_name
  storage_account_name  = azurerm_storage_account.storage_account.name
}


resource "azurerm_eventhub_namespace" "eventhub_namespace" {
  name                = var.eventhub_namespace_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "Standard"
  capacity            = 1

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "azurerm_eventhub" "eventhub" {
  name                = var.eventhub_name
  namespace_name      = azurerm_eventhub_namespace.eventhub_namespace.name
  resource_group_name = azurerm_resource_group.rg.name
  partition_count     = 1
  message_retention   = 1

  capture_description {
    enabled = true
    encoding = "Avro"
    interval_in_seconds = 300
    destination  {
      name = "EventHubArchive.AzureBlockBlob"
      blob_container_name = azurerm_storage_container.storage_container.name
      storage_account_id = azurerm_storage_account.storage_account.id
      archive_name_format = "{Namespace}/{EventHub}/{PartitionId}/{Year}/{Month}/{Day}/{Hour}/{Minute}/{Second}"
    }
  }
}

// Forward Stream Job and related resources

resource "azurerm_stream_analytics_job" "forward_stream_job" {
  name                                     = "cobotForwardStreamJob"
  resource_group_name                      = azurerm_resource_group.rg.name
  location                                 = azurerm_resource_group.rg.location
  data_locale                              = "en-US"
  events_late_arrival_max_delay_in_seconds = 60
  events_out_of_order_max_delay_in_seconds = 60
  events_out_of_order_policy               = "Adjust"
  output_error_policy                      = "Drop"
  streaming_units                          = 1

  transformation_query = <<QUERY
WITH FilteredInput AS
(
SELECT
    udf.dropColumns(${var.forward_stream_input_iothub_name}) AS FilteredJSON
FROM
    [${var.forward_stream_input_iothub_name}]
)
SELECT
    FilteredJSON.*
INTO
    [${var.forward_stream_output_postgres_name}]
FROM
    FilteredInput

SELECT
    FilteredJSON.*
INTO
    [${var.forward_stream_output_eventhub_name}]
FROM
    FilteredInput
QUERY

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "azurerm_stream_analytics_function_javascript_udf" "forward_stream_job_drop_columns_udf" {
  name                      = "dropColumns"
  stream_analytics_job_name = azurerm_stream_analytics_job.forward_stream_job.name
  resource_group_name       = azurerm_stream_analytics_job.forward_stream_job.resource_group_name

  script = <<SCRIPT
function main(input) {
  delete input['EventProcessedUtcTime'];
  delete input['PartitionId'];
  delete input['EventEnqueuedUtcTime'];
  delete input['IoTHub'];
  return input;
}
SCRIPT

  input {
    type = "any"
  }

  output {
    type = "any"
  }
}

resource "azurerm_stream_analytics_stream_input_iothub" "forward_stream_input_iothub" {
  name                         = var.forward_stream_input_iothub_name
  stream_analytics_job_name    = azurerm_stream_analytics_job.forward_stream_job.name
  resource_group_name          = azurerm_resource_group.rg.name
  endpoint                     = "messages/events"
  eventhub_consumer_group_name = "$Default"
  iothub_namespace             = azurerm_iothub.iothub.name
  shared_access_policy_key     = azurerm_iothub.iothub.shared_access_policy[0].primary_key
  shared_access_policy_name    = "iothubowner"

  serialization {
    type     = "Json"
    encoding = "UTF8"
  }
}

resource "azurerm_stream_analytics_output_eventhub" "forward_stream_output_eventhub" {
  name                      = var.forward_stream_output_eventhub_name
  stream_analytics_job_name = azurerm_stream_analytics_job.forward_stream_job.name
  resource_group_name       = azurerm_resource_group.rg.name
  eventhub_name             = azurerm_eventhub.eventhub.name
  servicebus_namespace      = azurerm_eventhub_namespace.eventhub_namespace.name
  shared_access_policy_key  = azurerm_eventhub_namespace.eventhub_namespace.default_primary_key
  shared_access_policy_name = "RootManageSharedAccessKey"

  serialization {
    type     = "Json"
    encoding = "UTF8"
  }
}


// MPC Stream Job and related resources

resource "azurerm_stream_analytics_job" "mpc_stream_job" {
  name                                     = "cobotMPCPredictionStreamJob"
  resource_group_name                      = azurerm_resource_group.rg.name
  location                                 = azurerm_resource_group.rg.location
  data_locale                              = "en-US"
  events_late_arrival_max_delay_in_seconds = 60
  events_out_of_order_max_delay_in_seconds = 60
  events_out_of_order_policy               = "Adjust"
  output_error_policy                      = "Drop"
  streaming_units                          = 1

  transformation_query = <<QUERY
SELECT
    agv_id,
    DATEADD(second, 1, udf.getTs(CollectTop(50) OVER (ORDER BY CAST(${var.mpc_stream_input_iothub_name}.ts AS DATETIME) DESC))) as ts,
    udf.predictMPC(udf.formatPredictionPayload(CollectTop(50) OVER (ORDER BY CAST(${var.mpc_stream_input_iothub_name}.ts AS DATETIME) DESC))) as predicted_momentary_power_consumption
INTO ${var.mpc_stream_output_postgres_name}
FROM ${var.mpc_stream_input_iothub_name} TIMESTAMP BY ${var.mpc_stream_input_iothub_name}.ts
WHERE ${var.mpc_stream_input_iothub_name}.agv_type = 'v1'
GROUP BY HoppingWindow(second, 300, 1), agv_id
QUERY

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "azurerm_stream_analytics_stream_input_iothub" "mpc_stream_input_iothub" {
  name                         = var.mpc_stream_input_iothub_name
  stream_analytics_job_name    = azurerm_stream_analytics_job.mpc_stream_job.name
  resource_group_name          = azurerm_resource_group.rg.name
  endpoint                     = "messages/events"
  eventhub_consumer_group_name = "$Default"
  iothub_namespace             = azurerm_iothub.iothub.name
  shared_access_policy_key     = azurerm_iothub.iothub.shared_access_policy[0].primary_key
  shared_access_policy_name    = "iothubowner"

  serialization {
    type     = "Json"
    encoding = "UTF8"
  }
}

resource "azurerm_stream_analytics_function_javascript_udf" "mpc_stream_job_format_prediction_payload_udf" {
  name                      = "formatPredictionPayload"
  stream_analytics_job_name = azurerm_stream_analytics_job.mpc_stream_job.name
  resource_group_name       = azurerm_stream_analytics_job.mpc_stream_job.resource_group_name

  script = <<SCRIPT
function main(vals) {
    data = JSON.stringify(vals.map(val => {
        return [
            val['value']['momentary_power_consumption'],
            val['value']['battery_cell_voltage'],
            val['value']['left_safety_interlock'],
            val['value']['left_auto_permission'],
            val['value']['left_manual_permission'],
            val['value']['left_command_on'],
            val['value']['left_executed'],
            val['value']['left_in_progress'],
            val['value']['left_actual_speed'],
            val['value']['pin_up_safety_interlock'],
            val['value']['pin_up_auto_permission'],
            val['value']['right_safety_interlock'],
            val['value']['right_auto_permission'],
            val['value']['right_manual_permission'],
            val['value']['right_command_on'],
            val['value']['right_actual_speed'],
            val['value']['manual_mode_active'],
            val['value']['auto_mode_active'],
            val['value']['plc_fault_active'],
            val['value']['plc_warning_active'],
            val['value']['led_rgb_strip_1_left_r'],
            val['value']['led_rgb_strip_2_right_r'],
            val['value']['led_rgb_strip_1_left_g'],
            val['value']['led_rgb_strip_2_right_g'],
            val['value']['led_rgb_strip_1_left_b'],
            val['value']['led_rgb_strip_2_right_b'],
            val['value']['led_status_active_mode'],
            val['value']['go_to_destination_id'],
            val['value']['go_to_result'],
            val['value']['pause_result'],
            val['value']['resume_destination_id'],
            val['value']['resume_result'],
            val['value']['abort_result'],
            val['value']['natural_navigation_status'],
            val['value']['error_status'],
            val['value']['natural_navigation_state'],
            val['value']['nn_x_coordinate'],
            val['value']['nn_y_coordinate'],
            val['value']['nn_heading'],
            val['value']['nn_position_confidence'],
            val['value']['nn_speed'],
            val['value']['nn_going_to_id'],
            val['value']['nn_target_reached'],
            val['value']['nn_current_segment'],
            val['value']['momentary_freq_left_encoder'],
            val['value']['momentary_freq_right_encoder'],
            val['value']['cumulative_distance_left'],
            val['value']['cumulative_distance_right'],
            val['value']['safety_circuit_closed'],
            val['value']['scanners_muted'],
            val['value']['front_bumper_triggered'],
            val['value']['front_scanner_safety_zone_violated'],
            val['value']['rear_scanner_safety_zone_violated'],
            val['value']['front_scanner_warning_zone_violated'],
            val['value']['rear_scanner_warning_zone_violated'],
            val['value']['scanners_active_zones']
        ]
    }))

    return { "data": data }
}
SCRIPT

  input {
    type = "any"
  }

  output {
    type = "any"
  }
}

resource "azurerm_stream_analytics_function_javascript_udf" "mpc_stream_job_get_ts_payload_udf" {
  name                      = "getTs"
  stream_analytics_job_name = azurerm_stream_analytics_job.mpc_stream_job.name
  resource_group_name       = azurerm_stream_analytics_job.mpc_stream_job.resource_group_name

  script = <<SCRIPT
function main(vals) {
    date = vals[0]['value']['ts']
    //return new Date(date.getTime() + 1000) // Adds 1 second as it's predicting a future date
    return date
}
SCRIPT

  input {
    type = "any"
  }

  output {
    type = "any"
  }
}

// TODO: Wheel Anomaly Stream Job and related resources

resource "azurerm_stream_analytics_job" "wheel_stream_job" {
  name                                     = "cobotWheelPredictionStreamJob"
  resource_group_name                      = azurerm_resource_group.rg.name
  location                                 = azurerm_resource_group.rg.location
  data_locale                              = "en-US"
  events_late_arrival_max_delay_in_seconds = 60
  events_out_of_order_max_delay_in_seconds = 60
  events_out_of_order_policy               = "Adjust"
  output_error_policy                      = "Drop"
  streaming_units                          = 1

  transformation_query = <<QUERY
WITH FilteredInput AS
(
SELECT
    udf.dropColumns(${var.wheel_stream_input_iothub_name}) AS FilteredJSON
FROM
    [${var.wheel_stream_input_iothub_name}]
WHERE
   ${var.wheel_stream_input_iothub_name}.agv_type = 'v2'
)

SELECT
    udf.predictWheel(udf.pickColumns(FilteredJSON)) as wheel_anomaly, FilteredJSON.agv_id as agv_id, FilteredJSON.ts as ts
INTO
    [${var.wheel_stream_output_postgres_name}]
FROM
    FilteredInput
QUERY

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "azurerm_stream_analytics_stream_input_iothub" "wheel_stream_input_iothub" {
  name                         = var.wheel_stream_input_iothub_name
  stream_analytics_job_name    = azurerm_stream_analytics_job.wheel_stream_job.name
  resource_group_name          = azurerm_resource_group.rg.name
  endpoint                     = "messages/events"
  eventhub_consumer_group_name = "$Default"
  iothub_namespace             = azurerm_iothub.iothub.name
  shared_access_policy_key     = azurerm_iothub.iothub.shared_access_policy[0].primary_key
  shared_access_policy_name    = "iothubowner"

  serialization {
    type     = "Json"
    encoding = "UTF8"
  }
}

resource "azurerm_stream_analytics_function_javascript_udf" "wheel_stream_job_pick_columns_udf" {
  name                      = "pickColumns"
  stream_analytics_job_name = azurerm_stream_analytics_job.wheel_stream_job.name
  resource_group_name       = azurerm_stream_analytics_job.wheel_stream_job.resource_group_name

  script = <<SCRIPT
function main(input) {
  return {
      'nn_diff_heading_avg_correction': input['nn_diff_heading_avg_correction'],
      'nn_distance_avg_correction': input['nn_distance_avg_correction']
  }
}
SCRIPT

  input {
    type = "any"
  }

  output {
    type = "any"
  }
}

resource "azurerm_stream_analytics_function_javascript_udf" "wheel_stream_job_drop_columns_udf" {
  name                      = "dropColumns"
  stream_analytics_job_name = azurerm_stream_analytics_job.wheel_stream_job.name
  resource_group_name       = azurerm_stream_analytics_job.wheel_stream_job.resource_group_name

  script = <<SCRIPT
function main(input) {
  delete input['EventProcessedUtcTime'];
  delete input['PartitionId'];
  delete input['EventEnqueuedUtcTime'];
  delete input['IoTHub'];
  return input;
}
SCRIPT

  input {
    type = "any"
  }

  output {
    type = "any"
  }
}

// Segment Anomaly Stream Job and related resources

resource "azurerm_stream_analytics_job" "segment_stream_job" {
  name                                     = "cobotSegmentAnomalyStreamJob"
  resource_group_name                      = azurerm_resource_group.rg.name
  location                                 = azurerm_resource_group.rg.location
  data_locale                              = "en-US"
  events_late_arrival_max_delay_in_seconds = 60
  events_out_of_order_max_delay_in_seconds = 60
  events_out_of_order_policy               = "Adjust"
  output_error_policy                      = "Drop"
  streaming_units                          = 1

  transformation_query = <<QUERY
SELECT
    ${var.segment_stream_input_iothub_name}.agv_id as agv_id, ${var.segment_stream_input_iothub_name}.ts as ts,
    udf.segmentHasAnomaly(${var.segment_stream_input_iothub_name}) as segment_anomaly
INTO
    [${var.wheel_stream_output_postgres_name}]
FROM
    [${var.segment_stream_input_iothub_name}]
WHERE 
    ${var.segment_stream_input_iothub_name}.agv_type = 'v1'
QUERY

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "azurerm_stream_analytics_stream_input_iothub" "segment_stream_input_iothub" {
  name                         = var.segment_stream_input_iothub_name
  stream_analytics_job_name    = azurerm_stream_analytics_job.segment_stream_job.name
  resource_group_name          = azurerm_resource_group.rg.name
  endpoint                     = "messages/events"
  eventhub_consumer_group_name = "$Default"
  iothub_namespace             = azurerm_iothub.iothub.name
  shared_access_policy_key     = azurerm_iothub.iothub.shared_access_policy[0].primary_key
  shared_access_policy_name    = "iothubowner"

  serialization {
    type     = "Json"
    encoding = "UTF8"
  }
}

resource "azurerm_stream_analytics_function_javascript_udf" "segment_stream_job_segment_has_anomaly_udf" {
  name                      = "segmentHasAnomaly"
  stream_analytics_job_name = azurerm_stream_analytics_job.segment_stream_job.name
  resource_group_name       = azurerm_stream_analytics_job.segment_stream_job.resource_group_name

  script = <<SCRIPT
function main(arg1) {
    segment_value = arg['nn_current_segment']
    EXPECTED_SEGMENTS = [
        4, 7, 9, 10, 12, 15, 16, 19, 20, 23, 24,
        27, 36, 39, 41, 42, 44, 47, 48, 51, 52,
        55, 56, 59, 60, 63
    ]
    if (EXPECTED_SEGMENTS.includes(arg1)) {
        return 0;
    }
    return 1;
}
SCRIPT

  input {
    type = "any"
  }

  output {
    type = "any"
  }
}

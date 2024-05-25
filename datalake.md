# Datalake

The Datalake is a part of the whole infrastructure that is setup in the main README file. All Datalake-related resources are provisioned with Terraform as described in main README.md file.

## Datalake components

### Azure Storage Account

Azure Storage Account is required for setting up specific Azure Storage functionalities. Below there is a definition in Terraform that provisions Azure Storage Account for our project:


```
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
```

The `is_hns_enabled` property instructs the Azure Storage Account to support hierarchical namespace which enables Azure Data Lake Gen2 functionalities.

### Azure Storage Container

Next resource that is needed is container that will store all captured files. Below there is a definition in Terraform that provisions this container for our project:

```
resource "azurerm_storage_container" "storage_container" {
  name                  = var.storage_container_name
  storage_account_name  = azurerm_storage_account.storage_account.name
}
```


### Event Hub

The data is captured into the Azure Storage Container thanks to integration with Event Hub and its Capture functionality. Below you can find the definitions for Event Hub namespace and Event Hub with Capture congiured:

```
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

```

## Azure Stream Analytics

As there is no direct integraiton between Azure IoT Hub and Event Hub, the data from Azure IoT Hub needs to be passed through Azure Stream Analytics first. Below you can find definition for the Azure Stream Analytics job and related input/ouput definitions:


```

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
```


## Reading data captured in Datalake

Data captured in Data Lake can be read for further analysis in many ways. One of the simple options to do so, is by downloading the Avro files from Datalake and analysing them locally.

### Prerequisites

Script to read the files is written in Python and requires `avro` library to be installed, e.g. with the following command:

```
pip install avro
```

### Running the script

The Avro files stored in Data Lake are produced by Event Hub Capture feature and they include schemas in their payload. The script `scripts/read_avro_from_datalake.py` can be used to parse such files and read them as JSON records. In order to use it, first download the file(s) from Data Lake to your local environment. Then, replace the `FILENAME` with a path to the downloaded file to be processed. After that run, the script with the following command:

```
python scripts/read_avro_from_datalake.py
```

The script will just read and print out the readings, but can be easily adjusted to do further processing on that data.

variable "location" {
  default = "ukwest"
}

variable "project" {
  default = "CoBotAGV"
}

variable "environment" {
  default = "Testing"
}

variable "resource_group_name" {
  default = "CoBotResourceGroup"
}

variable "iothub_name" {
  default = "cobotIotHub"
}

variable "forward_stream_input_iothub_name" {
  default = "cobotStreamInputIotHub"
}

variable "forward_stream_output_eventhub_name" {
  default = "cobotStreamOutputEventHub"
}

variable "forward_stream_output_postgres_name" {
  default = "cobotStreamOutputPostgres"
}

variable "mpc_stream_input_iothub_name" {
  default = "cobotStreamInputIotHub"
}

variable "mpc_stream_output_postgres_name" {
  default = "cobotStreamOutputPostgres"
}

variable "wheel_stream_input_iothub_name" {
  default = "cobotStreamInputIotHub"
}

variable "wheel_stream_output_postgres_name" {
  default = "cobotStreamOutputPostgres"
}

variable "segment_stream_input_iothub_name" {
  default = "cobotStreamInputIotHub"
}

variable "segment_stream_output_postgres_name" {
  default = "cobotStreamOutputPostgres"
}

variable "eventhub_namespace_name" {
  default = "cobotEventHubNamespace"
}

variable "eventhub_name" {
  default = "cobotEventHub"
}

variable "storage_account_name" {
  default = "cobotstorageaccount"
}

variable "storage_container_name" {
  default = "readings"
}


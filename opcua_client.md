# OPC UA Client

The implementation of an OPC UA Client is available in `opcuaclient` directory. It is the simple version with periodic fetch approach, that forwards data to Azure IoT Hub right before preprocessing it to expected shape.

## Prerequisites

The code is written in Node.js, so it requires Node.js to be installed on the machine. Afterwards, it is needed to install required dependencies by running e.g.:

```
npm install
```

in the project directory. All dependencies are listed in `opcuaclient/package.json` file.


## Running the client

As client is very simple, it should be invoked separately for each of the monitored AGV. Before running, the following environment variables needs to be provided:

- `DEVICE_CONNECTION_STRING` - Azure IoT Hub connection string corresponding to the related Device within Azure IoT Hub
- `ENDPOINT_URL` - URL to the OPC UA server
- `AGV_ID` - ID of the AGV, defaults to `AGV_1`
- `AGV_TYPE` - Type of the monitored AGV, defaults to `v2` which is the latest version of the payload supported. Alternatively, it can be `v1` when processing historical data from 2022


After setting up these environment variables, script can be executed with the following command:

```
node opcuaclient/index.js
```

It should be stopped and started whenever AGV is moving, otherwise it will continue monitoring it even if it does not perform any additional actions.

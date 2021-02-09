# microSDI12
A mini SDI-12 implementation for getting sensor info over UART. Supports simple RS-232 and directional RS-485.

# API

## class SDI12
**\__init__** (pin_txd, pin_rxd, pin_direction, uart_bus_id)
  * TX pin name
  * RX pin name
  * Direction pin name (optional)
  * UART bus id (optional, default = 1)

**is_active** (address)
  * args:
    * SDI-12 sensor address. Typical range: 0-9.
  * returns:
    * Boolean: whether the sensor has send back acknowledgement

**get_sensor_info** (address)
  * args:
    * SDI-12 sensor address. Typical range: 0-9.
  * returns:
    * Tuple (manufacturer, model): The manufacturer and model name as reported by the sensor. If sensor is unreachable, returns `(None, None)`

**get_measurement** (address)

Sends a request for data measurement to the sensor and returns the data provided by the sensor.
  * args:
    * SDI-12 sensor address. Typical range: 0-9.
  * returns:
    * Measurement data: a string line containing a typical measurement. For data format and parsing, please advise sensor manufacturer manuals. If sensor is unreachable, returns `None`


# Example

```python
from microsdi12 import SDI12

sdi12 = None

try:
    sdi12 = SDI12("P3", "P4", "P8", 1)

    manufacturer = None
    model = None
    sensor_response = None
    address = "1"

    if sdi12.is_active(address):
        manufacturer, model = sdi12.get_sensor_info(address)
        sensor_response = sdi12.get_measurement(address)
        response_array = sdi12.measurement_to_array(sensor_response)
except Exception as e:
    print("Exception while reading SDI-12 data")
finally:
    if sdi12:
        sdi12.close()
```


# links
 * https://docs.micropython.org/en/latest/library/machine.UART.html
 * https://docs.pycom.io/firmwareapi/pycom/machine/uart/

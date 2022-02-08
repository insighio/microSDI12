# microSDI12
A mini SDI-12 implementation for getting sensor info over UART using directional RS-485.

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
    * Boolean: whether the sensor has send back acknowledgment

**get_sensor_info** (address)
  * args:
    * SDI-12 sensor address. Typical range: 0-9.
  * returns:
    * Tuple (manufacturer, model): The manufacturer and model name as reported by the sensor. If sensor is unreachable, returns `(None, None)`

**get_measurement** (address, measurement_name="M")

Sends a request for data measurement to the sensor and returns the data provided by the sensor split into an array. Supports parsing all possible values provided through multiple sequential requests on the sensor. Example:
```
  > aM!
  < a1329 (address + max 132 seconds of waiting + 9 expected values )
  > aD0!
  < a+1+2-3+4.1+5 (5 values read so there will be an additional request for extra data)
  > aD1!
  < a+6+7+8+9

  output: [1, 2, -3, 4.1, 5, 6, 7, 8, 9]
```
  * args:
    * SDI-12 sensor address. Typical range: 0-9.
    * measurement_name: Configures the name of the query. Default is "M" as the default query is "aM!".
  * returns:
    * Measurement data array: an array containing all the data collected from the sensor. For details on each data value, please advise sensor manufacturer manuals. If sensor is unreachable, returns `None`

**set_timing_params** (char_wait_duration_us):

Set the time needed for a character to be transmitted over UART. Used to calculate the sleep periods to ensure a character has been fully transmitted (ex. time to keep HIGH/LOW the direction and transmission pins for BREAK or MARK for SDI12). Default: 8333us

**set_wait_after_uart_write** (wait_enabled):

Enable/disable the sleep command after a UART write. For micropython implementations that uart.write calls uart_wait_tx_done, this sleep can be deactivated. If enabled, after UART write, the application sleeps for (char_wait_duration_us) * (number of command characters).

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
        response_array = sdi12.get_measurement(address)
        print(response_array)
except Exception as e:
    print("Exception while reading SDI-12 data")
finally:
    if sdi12:
        sdi12.close()
```


# links
 * https://docs.micropython.org/en/latest/library/machine.UART.html
 * https://docs.pycom.io/firmwareapi/pycom/machine/uart/

from machine import Pin
from machine import UART
import utime


class SDI12:
    def __init__(self, pin_txd, pin_rxd, pin_direction=None, uart_bus_id=1):
        self.pin_txd = pin_txd
        self.pin_rxd = pin_rxd
        self.p_tx = Pin(pin_txd, mode=Pin.OUT)
        if pin_direction:
            self.p_dir = Pin(pin_direction, mode=Pin.OUT)
        self.uart = UART(uart_bus_id)

    def _send(self, cmd):
        self.uart.deinit()
        self.p_tx.value(0)
        if pin_direction:
            self.p_dir.value(1)                                                 # set output dir
        utime.sleep_us(12500)                                                   # send BREAK
        self.p_tx.value(1)
        utime.sleep_us(8333)                                                    # send MARK
        self.uart.init(baudrate=1200, bits=7, parity=UART.EVEN, stop=1, timeout_chars=75, pins=(self.pin_txd, self.pin_rxd))     # init with given parameters
        print("SDI12 > [" + cmd + "]")
        self.uart.write(cmd)                                                    # send command
        utime.sleep_us(8333 * len(cmd))                                         # wait to send command (byte time * command length)
        if pin_direction:
            self.p_dir.value(0)                                                 # output set to read
        line = self.uart.readline()                                             # read data from UART
        if line:
            line = line.decode('utf-8').strip()
            print(" < [" + line + "]")
        return line

    def is_active(self, address):
        ack_act_cmd_resp = self._send(address + '!')
        return (ack_act_cmd_resp == address)

    def get_sensor_info(self, address):
        manufacturer = None
        model = None
        id_cmd_resp = self._send(address + 'I!')
        if id_cmd_resp:
            responseParts = id_cmd_resp.split(' ')
            manufacturer = responseParts[0][3:]
            model = responseParts[1]
        return (manufacturer, model)

    def get_measurement(self, address):
        data_cmd_resp = None
        # Request
        nonconcur_meas_cmd_resp = self._send(address + 'M!')
        if nonconcur_meas_cmd_resp and len(nonconcur_meas_cmd_resp) == 5:
            seconds_to_wait_max = int(nonconcur_meas_cmd_resp[1:3])
            number_of_measurements = int(nonconcur_meas_cmd_resp[4])

            timeout = utime.ticks_ms() + seconds_to_wait_max * 1000
            pending_bytes = self.uart.any()
            while utime.ticks_ms() < timeout and pending_bytes == 0:
                pending_bytes = self.uart.any()
                if pending_bytes > 0:
                    self.uart.readline()
                    break
                utime.sleep_ms(10)

            data_cmd_resp = self._send(address + 'D0!')

        return data_cmd_resp

    def measurement_to_array(self, measurement_response):
        values = []
        try:
            # start from index 1 since response[0] is the address
            i = 1
            while i < len(measurement_response):
                c = measurement_response[i]
                if c == "-":
                    values.append(c)
                elif c == "+":
                    values.append("")
                else:
                    values[-1] += c
                i += 1
        except Exception as e:
            print("Error processing generic sdi response: [{}]".format(measurement_response))
        return values

    def read_sensor(self, address):
        manufacturer = None
        model = None
        sensor_response = None

        if self.is_active(address):
            manufacturer, model = self.get_sensor_info(address)
            sensor_response = self.get_measurement(address)

        return (manufacturer, model, sensor_response)

    def close(self):
        if self.uart:
            self.uart.deinit()

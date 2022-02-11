from machine import Pin
from machine import UART
import utime
import sys


class SDI12:
    def __init__(self, pin_txd, pin_rxd, pin_direction=None, uart_bus_id=1):
        self.pin_txd = pin_txd
        self.pin_rxd = pin_rxd
        self.pin_dir = pin_direction
        self.uart = None
        self.uart_bus_id = uart_bus_id
        self.is_esp32 = (sys.platform.lower() == "esp32")
        self.char_wait_duration_us = 8333
        self.enable_wait_after_uart_write = True

    def set_timing_params(self, char_wait_duration_us):
        self.char_wait_duration_us = char_wait_duration_us

    def set_wait_after_uart_write(self, wait_enabled):
        self.enable_wait_after_uart_write = wait_enabled

    def _send(self, cmd, timeout_ms=2500, termination_line=None):
        if self.uart:
            self.uart.deinit()

        self.p_tx = Pin(self.pin_txd, mode=Pin.OUT)
        self.p_dir = None
        if self.pin_dir:
            self.p_dir = Pin(self.pin_dir, mode=Pin.OUT)

        self.p_tx.value(0)
        if self.p_dir:
            self.p_dir.value(1)                                                 # set output dir
        utime.sleep_us(int(self.char_wait_duration_us * 1.5))                   # send BREAK
        self.p_tx.value(1)
        utime.sleep_us(self.char_wait_duration_us)                              # send MARK
        if self.is_esp32:
            self.uart = UART(self.uart_bus_id, baudrate=1200, bits=7, parity=2, stop=1, tx=self.pin_txd, rx=self.pin_rxd, timeout_char=75)
        else:
            self.uart = UART(self.uart_bus_id, baudrate=1200, bits=7, parity=UART.EVEN, stop=1, timeout_chars=75, pins=(self.pin_txd, self.pin_rxd))
        print("SDI12 > [" + cmd + "]")
        self.uart.write(cmd)                                                    # send command
        if self.enable_wait_after_uart_write:
            utime.sleep_us(8333 * len(cmd))                                     # wait to send command (byte time * command length)
        if self.pin_dir:
            self.p_dir.value(0)                                                 # output set to read

        start_timestamp = utime.ticks_ms()
        timeout_timestamp = start_timestamp + timeout_ms
        line = ""
        while True:
            remaining_bytes = self.uart.any()
            if(utime.ticks_ms() >= timeout_timestamp):
                break

            if remaining_bytes > 0:
                line_cur = self.uart.readline()
                if line_cur:
                    try:
                        line_cur = line_cur.decode('utf-8').strip()
                        line += '\n' + line_cur
                        print(" < [" + line_cur + "]")
                        if termination_line is not None:
                            if line_cur == termination_line:
                                break
                        else:
                            break
                    except:
                        print("! " + str(line))
            utime.sleep_ms(100)
        return line.strip() if line != "" else None

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
            model = ' '.join(responseParts[1:]).strip()
        return (manufacturer, model)

    def get_measurement(self, address, measurement_name="M"):
        values = None
        # Request
        nonconcur_meas_cmd_resp = self._send(address + measurement_name + '!')
        if nonconcur_meas_cmd_resp and len(nonconcur_meas_cmd_resp) == 5:
            seconds_to_wait_max = int(nonconcur_meas_cmd_resp[1:4])
            number_of_measurements = int(nonconcur_meas_cmd_resp[4])

            timeout = utime.ticks_ms() + seconds_to_wait_max * 1000
            pending_bytes = self.uart.any()
            while utime.ticks_ms() < timeout and pending_bytes == 0:
                pending_bytes = self.uart.any()
                if pending_bytes > 0:
                    try:
                        line = self.uart.readline()
                        print(" <~ [" + line.decode('utf-8').strip() + "]")
                    except:
                        print(" <~! [" + str(line) + "]")
                    break
                utime.sleep_ms(10)

            i = 0
            values_read = 0
            values = []
            max_i = 9  # safety measure in case the sensor is unresponsive
            while values_read < number_of_measurements and i < max_i:
                resp = self._send(address + 'D' + str(i) + '!')
                values = values + self._measurement_to_array(resp)
                values_read = len(values)
                i += 1

        return values

    def _measurement_to_array(self, measurement_response):
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

    def close(self):
        if self.uart:
            self.uart.deinit()

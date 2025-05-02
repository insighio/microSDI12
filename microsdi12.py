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
        self.is_esp32 = sys.platform.lower() == "esp32"
        self.char_wait_duration_us = 8333
        self.enable_wait_after_uart_write = True
        self.dual_direction_pins = False
        self.pin_drv = None
        self.pin_rcv = None
        self.pin_drv_tx_val = 1
        self.pin_rcv_tx_val = 1
        self.pin_drv_rx_val = 0
        self.pin_rcv_rx_val = 0
        self.delay_ms_after_send = None

    def set_dual_direction_pins(self, pin_drv, pin_rcv, pin_drv_tx_val=1, pin_rcv_tx_val=1, pin_drv_rx_val=0, pin_rcv_rx_val=0):
        self.pin_drv = pin_drv
        self.pin_rcv = pin_rcv
        self.pin_drv_tx_val = pin_drv_tx_val
        self.pin_rcv_tx_val = pin_rcv_tx_val
        self.pin_drv_rx_val = pin_drv_rx_val
        self.pin_rcv_rx_val = pin_rcv_rx_val
        self.dual_direction_pins = True

    def wait_after_each_send(self, delay_ms):
        self.delay_ms_after_send = delay_ms

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
        elif self.dual_direction_pins:
            self.p_drv = Pin(self.pin_drv, mode=Pin.OUT)
            self.p_rcv = Pin(self.pin_rcv, mode=Pin.OUT)

        self.p_tx.value(0)
        if self.p_dir:
            self.p_dir.value(1)  # set output dir
        elif self.dual_direction_pins:
            self.p_drv.value(self.pin_drv_tx_val)
            self.p_rcv.value(self.pin_rcv_tx_val)
        utime.sleep_us(int(self.char_wait_duration_us * 1.5))  # send BREAK
        self.p_tx.value(1)
        utime.sleep_us(self.char_wait_duration_us)  # send MARK
        if self.is_esp32:
            self.uart = UART(self.uart_bus_id, baudrate=1200, bits=7, parity=2, stop=1, tx=self.pin_txd, rx=self.pin_rxd, timeout_char=75)
            self.uart.init(baudrate=1200, bits=7, parity=2, stop=1, tx=self.pin_txd, rx=self.pin_rxd, timeout_char=75)
        else:
            self.uart = UART(
                self.uart_bus_id, baudrate=1200, bits=7, parity=UART.EVEN, stop=1, timeout_chars=75, pins=(self.pin_txd, self.pin_rxd)
            )
        print("SDI12 > [" + cmd + "]")
        self.uart.write(cmd)  # send command
        if self.enable_wait_after_uart_write:
            utime.sleep_us(8333 * len(cmd))  # wait to send command (byte time * command length)
        if self.pin_dir:
            self.p_dir.value(0)  # output set to read
        elif self.dual_direction_pins:
            self.p_drv.value(self.pin_drv_rx_val)  # set driver pin to receive
            self.p_rcv.value(self.pin_rcv_rx_val)

        start_timestamp = utime.ticks_ms()
        timeout_timestamp = start_timestamp + timeout_ms
        line = ""
        while True:
            remaining_bytes = self.uart.any()
            if utime.ticks_ms() >= timeout_timestamp:
                break

            if remaining_bytes > 0:
                line_cur = self.uart.readline()
                if line_cur:
                    try:
                        line_cur = line_cur.decode("utf-8").strip()
                        line += "\n" + line_cur
                        print(" < [" + line_cur + "]")
                        if termination_line is not None:
                            if line_cur == termination_line:
                                break
                        else:
                            break
                    except:
                        print("! " + str(line))
            utime.sleep_ms(100)

        if self.delay_ms_after_send:
            utime.sleep_ms(self.delay_ms_after_send)

        return line.strip() if line != "" else None

    def is_active(self, address):
        ack_act_cmd_resp = self._send(address + "!")
        return ack_act_cmd_resp == address

    def get_sensor_info(self, address):
        manufacturer = None
        model = None
        id_cmd_resp = self._send(address + "I!")
        if id_cmd_resp and len(id_cmd_resp) >= 17:
            manufacturer = id_cmd_resp[3:11].strip()
            model = id_cmd_resp[11:17].strip()
        return (manufacturer, model)

    def get_sensor_info_ex(self, address):
        manufacturer = None
        model = None
        version = None
        extra_info = None
        id_cmd_resp = self._send(address + "I!")
        if id_cmd_resp and len(id_cmd_resp) > 20:
            manufacturer = id_cmd_resp[3:11].strip()
            model = id_cmd_resp[11:17].strip()
            version = id_cmd_resp[17:20].strip()
            extra_info = id_cmd_resp[20:].strip()
        return (manufacturer, model, version, extra_info)

    def get_measurement(self, address, measurement_name="M", number_of_measurements_digit_count=1, force_wait_period=False):
        values = None
        # Request
        meas_cmd_resp = self._send(address + measurement_name + "!")
        if meas_cmd_resp and len(meas_cmd_resp) == (4 + number_of_measurements_digit_count):
            seconds_to_wait_max = int(meas_cmd_resp[1:4])
            number_of_measurements = int(meas_cmd_resp[4 : 4 + number_of_measurements_digit_count])

            timeout = utime.ticks_ms() + seconds_to_wait_max * 1000
            pending_bytes = self.uart.any()
            while utime.ticks_ms() < timeout and (force_wait_period or pending_bytes == 0):
                pending_bytes = self.uart.any()
                if pending_bytes > 0:
                    try:
                        line = self.uart.readline()
                        print(" <~ [" + line.decode("utf-8").strip() + "]")
                    except:
                        print(" <~! [" + str(line) + "]")
                    if not force_wait_period:
                        break
                utime.sleep_ms(10)

            i = 0
            values_read = 0
            values = []
            max_i = 9  # safety measure in case the sensor is unresponsive
            while values_read < number_of_measurements and i < max_i:
                resp = self._send(address + "D" + str(i) + "!")
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
            print(e)
        return values

    def close(self):
        if self.dual_direction_pins:
            try:
                self.p_drv.value(0)
                self.p_rcv.value(1)
            except:
                pass

        if self.uart:
            self.uart.deinit()

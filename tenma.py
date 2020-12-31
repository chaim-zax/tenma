# -*- coding: utf-8 -*-
#
# Copyright (C) 2020, Chaim Zax <chaim.zax@gmail.com>
#
# version: 0.1
#
import platform
import serial
import time
import threading

FORMAT = '%(asctime)-15s %(levelname)s %(filename)s:%(lineno)d %(message)s'


class Tenma:

    DEFAULT_VERBOSE_LEVEL = 2
    DEFAULT_SERIAL_PORT_WIN = 'COM99'
    DEFAULT_SERIAL_PORT_LINUX = '/dev/ttyACM0'  # try '/dev/ttyACM0' without udev rules
    DEFAULT_BAUD_RATE = 115200
    DEFAULT_SKIP_CHECK = False
    DEFAULT_POWER_SUPPLY_MAX_VOLTAGE = 30
    DEFAULT_POWER_SUPPLY_MAX_CURRENT = 5
    CHANNEL_1 = 1
    CHANNEL_2 = 2

    def __init__(self):
        self.verbose_level = Tenma.DEFAULT_VERBOSE_LEVEL
        if platform.system() == 'Windows':
            self.serial_port = Tenma.DEFAULT_SERIAL_PORT_WIN
        else:
            self.serial_port = Tenma.DEFAULT_SERIAL_PORT_LINUX
        self.baud_rate = Tenma.DEFAULT_BAUD_RATE
        self.skip_check = Tenma.DEFAULT_SKIP_CHECK
        self.device = None
        self.device_id = None
        self.device_type = None
        self.mutex = threading.Lock()

    def _write(self, data):
        res = self.device.write(data.encode('ascii'))
        time.sleep(0.05)
        return res

    def _read(self, length):
        res = self.device.read(length).decode('ascii')
        time.sleep(0.05)
        return res

    def _read_bytes(self, length):
        res = self.device.read(length)
        time.sleep(0.05)
        return res

    def _send_command(self, cmd):
        if self.device is None:
            print('ERROR: no power supply connected')
            return None

        self._write(cmd)

    def _receive_command(self, length=100):
        if self.device is None:
            print('ERROR: no power supply connected')
            return None

        return self._read(length)

    def set_verbose_level(self, verbose_level):
        self.verbose_level = verbose_level

    def open(self, serial_port=None, baud_rate=DEFAULT_BAUD_RATE, skip_check=False, allow_fail=False):
        if serial_port is not None and serial_port != '':
            self.serial_port = serial_port
        if baud_rate is not None and baud_rate != '':
            self.baud_rate = baud_rate
        if skip_check is not None and skip_check != '':
            self.skip_check = skip_check

        try:
            self.device = serial.Serial(self.serial_port, baudrate=self.baud_rate, timeout=1.0)
        except serial.serialutil.SerialException:
            if not allow_fail:
                if platform.system() == 'Windows':
                    print("ERROR: No power supply found (use the '-p COM1' option and provide the correct port)")
                else:
                    print("ERROR: No power supply found (use the '-p /dev/ttyUSB0' option and provide the correct port,"
                          " or install the udev rule as described in the INSTALL file)")
            self.device = None
            return -1

        res = 0
        if not self.skip_check:
            res = self.check_device_type()

        return res

    def close(self):
        if self.device is not None:
            self.device.close()
            self.device = None

    def check_device_type(self):
        self.device_id = self.get_device_id()

        if self.device_id == '' or len(self.device_id) < 5:
            print("ERROR: power supply not found or supported")
            return -1

        self.device_type = self.device_id[6:13]

        if self.device_id.startswith('TENMA'):
            if self.verbose_level == 2:
                print("power supply found with id '{}' (type {})".format(self.device_id, self.device_type))

        else:
            print("ERROR: power supply not found or supported")
            return -1

        return 0

    def set_current(self, channel=1, current=0):
        """
        1. ISET<X>:<NR2>
        Description: Sets the output current.
        Example:ISET1:2.225
        Sets the CH1 output current to 2.225A
        """
        with self.mutex:
            self._send_command('ISET{}:{:05.3f}'.format(channel, current))

    def get_current(self, channel=1):
        """
        2. ISET<X>?
        Description: Returns the output current setting.
        Example: ISET1?
        Returns the CH1 output current setting.
        """
        with self.mutex:
            self._send_command('ISET{}?'.format(channel))
            res = float(self._receive_command(6))
        return res

    def set_voltage(self, channel=1, voltage=0):
        """
        3. VSET<X>:<NR2>
        Description:Sets the output voltage.
        Example VSET1:20.50
        Sets the CH1 voltage to 20.50V
        """
        with self.mutex:
            self._send_command('VSET{}:{:05.2f}'.format(channel, voltage))

    def get_voltage(self, channel=1):
        """
        4. VSET<X>?
        Description:Returns the output voltage setting.
        Example VSET1?
        Returns the CH1 voltage setting
        """
        with self.mutex:
            self._send_command('VSET{}?'.format(channel))
            res = float(self._receive_command(5))
        return res

    def get_actual_current(self, channel=1):
        """
        5. IOUT<X>?
        Description:Returns the actual output current.
        Example IOUT1?
        Returns the CH1 output current
        """
        with self.mutex:
            self._send_command('IOUT{}?'.format(channel))
            res = float(self._receive_command(5))
        return res

    def get_actual_voltage(self, channel=1):
        """
        6. VOUT<X>?
        Description:Returns the actual output voltage.
        Example VOUT1?
        Returns the CH1 output voltage
        """
        with self.mutex:
            self._send_command('VOUT{}?'.format(channel))
            res = float(self._receive_command(5))
        return res

    def set_beep(self, on):
        """
        7. BEEP<Boolean>
        Description:Turns on or off the beep. Boolean: boolean logic.
        Example BEEP1 Turns on the beep.
        """
        with self.mutex:
            if on:
                self._send_command('BEEP1')
            else:
                self._send_command('BEEP0')

    def set_output(self, on):
        """
        8. OUT<Boolean>
        Description:Turns on or off the output.
        Boolean:0 OFF,1 ON
        Example: OUT1 Turns on the output
        """
        with self.mutex:
            if on:
                self._send_command('OUT1')
            else:
                self._send_command('OUT0')

    def get_status(self):
        """
        9. STATUS?
        Description:Returns the POWER SUPPLY status.
        Contents 8 bits in the following format
        Bit Item Description
        0 CH1 0=CC mode, 1=CV mode
        1 CH2 0=CC mode, 1=CV mode
        2, 3 Tracking 00=Independent, 01=Tracking series,11=Tracking parallel
        4 Beep 0=Off, 1=On
        5 Lock 0=Lock, 1=Unlock
        6 Output 0=Off, 1=On
        7 N/A N/A
        """
        if self.device is None:
            print('ERROR: no power supply found connected')
            return None

        with self.mutex:
            self._write('STATUS?')
            status = self._read_bytes(1)[0]
            ch1 = (status & 0b10000000) >> 7
            ch2 = (status & 0b01000000) >> 6
            tracking = (status & 0b00110000) >> 4
            beep = (status & 0b00001000) >> 3
            lock = (status & 0b00000100) >> 2
            output = (status & 0b00000010) >> 1
        return {'ch1': ch1, 'ch2': ch2, 'tracking': tracking, 'beep': beep, 'lock': lock, 'output': output}

    def get_device_id(self):
        """
        10. *IDN?
        Description:Returns the KA3005P identification.
        Example *IDN?
        Contents TENMA 72‐2535 V2.0 (Manufacturer, model name,).
        """
        if self.device is None:
            print('ERROR: no power supply connected')
            return None

        with self.mutex:
            self._write('*IDN?')
            res = self._read(18)   # e.g. 'TENMA 72-2540 V2.1'
        return res

    def recall(self, nr):
        """
        11. RCL<NR1>
        Description:Recalls a panel setting.
        NR1 1 – 5: Memory number 1 to 5
        Example RCL1 Recalls the panel setting stored in memory number 1
        """
        with self.mutex:
            self._send_command('RCL{}'.format(nr))

    def store(self, nr):
        """
        12. SAV<NR1>
        Description:Stores the panel setting.
        NR1 1 – 5: Memory number 1 to 5
        Example: SAV1 Stores the panel setting in memory number 1
        """
        with self.mutex:
            self._send_command('SAV{}'.format(nr))
            time.sleep(0.1)

    def set_ocp(self, on):
        """
        13. OCP< Boolean >
        Description:Stores the panel setting.
        Boolean: 0 OFF, 1 ON
        Example: OCP1 Turns on the OCP
        """
        with self.mutex:
            if on:
                self._send_command('OCP1')
            else:
                self._send_command('OCP0')

    def set_ovp(self, on):
        """
        14. OVP< Boolean >
        Description:Turns on the OVP.
        Boolean: 0 OFF, 1 ON
        Example: OVP1 Turns on the OVP
        """
        with self.mutex:
            if on:
                self._send_command('OVP1')
            else:
                self._send_command('OVP0')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020, Chaim Zax <chaim.zax@gmail.com>
#

import argparse
import os
import sys
import logging
import platform
import serial
import time

VERSION = "1.0"
FORMAT = '%(asctime)-15s %(levelname)s %(filename)s:%(lineno)d %(message)s'
DEFAULT_SERIAL_PORT = '/dev/ttyACM0'
DEFAULT_VERBOSE_LEVEL = 2
DEFAULT_BAUD_RATE = 115200
DEFAULT_SKIP_CHECK = False
if platform.system() == 'Windows':
    DEFAULT_PORT = 'COM99'
else:
    DEFAULT_PORT = '/dev/ttyACM0'  # try '/dev/ttyACM0' without udev rules
DEFAULT_MAX_VOLTAGE_POWER_SUPPLY = 30
DEFAULT_PRECHARGE_VOLTAGE_LEVEL = 3.00
DEFAULT_PRECHARGE_CURRENT_LEVEL = 0.010
DEFAULT_CONSTAND_VOLTAGE_LEVEL = 4.20
DEFAULT_CONSTAND_CURRENT_LEVEL = 0.120
DEFAULT_END_OF_CURRENT_LEVEL = 0.010
DEFAULT_TOTAL_CAPACITY = 0.500
#DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL = 3.10
DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL = 3.00
DEFAULT_MAX_CURRENT = 1.000
DEFAULT_TYPICAL_DISCHARGE_CURRENT = 0.036
DEFAULT_SERIES_DISCHARGE_RESISTOR = 118.1

m_description = """
This tool"""

m_epilog = "tenma-power-supply.py v{:s}, Copyright (c) 2020, Chaim Zax <chaim.zax@gmail.com>" \
           .format(VERSION)
m_verbose_level = 1
m_serial_port = DEFAULT_SERIAL_PORT
m_baud_rate = DEFAULT_BAUD_RATE
m_skip_check = DEFAULT_SKIP_CHECK
m_device = None
m_device_id = None
m_device_type = None
m_verbose = DEFAULT_VERBOSE_LEVEL
m_precharge_voltage_level = DEFAULT_PRECHARGE_VOLTAGE_LEVEL
m_precharge_current_level = DEFAULT_PRECHARGE_CURRENT_LEVEL
m_constand_voltage_level = DEFAULT_CONSTAND_VOLTAGE_LEVEL
m_constand_current_level = DEFAULT_CONSTAND_CURRENT_LEVEL
m_end_of_current_level = DEFAULT_END_OF_CURRENT_LEVEL
m_total_capacity = DEFAULT_TOTAL_CAPACITY
m_soc_empty_voltage_level = DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL
m_max_current = DEFAULT_MAX_CURRENT
m_typical_discharge_current = DEFAULT_TYPICAL_DISCHARGE_CURRENT
m_series_discharge_resistor = DEFAULT_SERIES_DISCHARGE_RESISTOR

def get_command_line_arguments():
    parser = argparse.ArgumentParser(description=m_description, epilog=m_epilog)

    parser.add_argument("-v", "--version", action='version', version=VERSION)
    parser.add_argument('-V', '--verbose-level', action='store', type=int, default=None,
                        help='set the verbose level, where 1=DEBUG, 2=INFO, 3=WARNING (default),' +
                             ' 4=ERROR, 5=CRITICAL')
    parser.add_argument('-b', '--baud-rate',
                        action='store', default=DEFAULT_BAUD_RATE, type=int,
                        help='set the baud-rate of the serial port (default {})' \
                        .format(DEFAULT_BAUD_RATE))
    parser.add_argument('-p', '--serial-port',
                        action='store', default='',
                        help="set the serial port (default '{}')".format(DEFAULT_PORT))
    parser.add_argument('-K', '--skip-check',
                        action='store_true', default=None,
                        help="skip sanity/device checking on start-up")
    parser.add_argument('-PV', '--precharge-voltage-level',
                        action='store', default=DEFAULT_PRECHARGE_VOLTAGE_LEVEL, type=float,
                        help='(default {} V)'.format(DEFAULT_PRECHARGE_VOLTAGE_LEVEL))
    parser.add_argument('-PC', '--precharge-current-level',
                        action='store', default=DEFAULT_PRECHARGE_CURRENT_LEVEL, type=float,
                        help='(default {} A)'.format(DEFAULT_PRECHARGE_CURRENT_LEVEL))
    parser.add_argument('-CV', '--constand-voltage-level',
                        action='store', default=DEFAULT_CONSTAND_VOLTAGE_LEVEL, type=float,
                        help='(default {} V)'.format(DEFAULT_CONSTAND_VOLTAGE_LEVEL))
    parser.add_argument('-CC', '--constand-current-level',
                        action='store', default=DEFAULT_CONSTAND_CURRENT_LEVEL, type=float,
                        help='(default {} A)'.format(DEFAULT_CONSTAND_CURRENT_LEVEL))
    parser.add_argument('-EC', '--end-of-current-level',
                        action='store', default=DEFAULT_END_OF_CURRENT_LEVEL, type=float,
                        help='(default {} A)'.format(DEFAULT_END_OF_CURRENT_LEVEL))
    parser.add_argument('-C', '--total-capacity',
                        action='store', default=DEFAULT_TOTAL_CAPACITY, type=float,
                        help='value in A/h at 3.7V (default {} A/h)'.format(DEFAULT_TOTAL_CAPACITY))

    args = parser.parse_args()
    return args


def set_verbose_level(verbose):
    global m_verbose
    m_verbose = verbose


def open_device(port=None, baud_rate=115200, skip_check=False,
                allow_fail=False):
    global m_device

    if port is None or port == '':
        port = DEFAULT_PORT

    try:
        m_device = serial.Serial(port, baudrate=baud_rate, timeout=1.0)
    except serial.serialutil.SerialException:
        if not allow_fail:
            if platform.system() == 'Windows':
                print("ERROR: No device found (use the '-p COM1' option and provide the correct port)")
            else:
                print("ERROR: No device found (use the '-p /dev/ttyUSB0' option and provide the correct port, or install the udev rule as described in the INSTALL file)")
        return -1

    #clear_port()

    res = 0
    if not skip_check:
        res = check_device_type()

    return res


def check_device_type():
    global m_device_id, m_device_type

    m_device_id = get_device_id()

    if m_device_id == '' or len(m_device_id) < 5:
        print("ERROR: device not found or supported")
        return -1

    m_device_type = m_device_id[6:13]

    if m_device_id.startswith('TENMA'):
        if m_verbose == 2:
            print("device found with id '{}' (type {})".format(m_device_id, m_device_type))

    else:
        print("ERROR: device not found or supported")
        return -1

    return 0


def get_device_id():
    if m_device is None:
        print('ERROR: no device connected')
        return ''

    m_device.write('*IDN?'.encode('ascii'))
    return m_device.read(18).decode('ascii')   # 'TENMA 72-2540 V2.1'


def _send_command(cmd):
    if m_device is None:
        print('ERROR: no device connected')
        return ''

    m_device.write(cmd.encode('ascii'))

def _receive_command(length=100):
    if m_device is None:
        print('ERROR: no device connected')
        return ''

    return m_device.read(length).decode('ascii')

# 1. ISET<X>:<NR2>
# Description: Sets the output current.
# Example:ISET1:2.225
# Sets the CH1 output current to 2.225A
def set_current(channel=1, current=0):
    _send_command('ISET{}:{:05.3f}'.format(channel, current))
    time.sleep(0.05)

# 2. ISET<X>?
# Description: Returns the output current setting.
# Example: ISET1?
# Returns the CH1 output current setting.
def get_current(channel=1):
    _send_command('ISET{}?'.format(channel))
    return float(_receive_command(6))

# 3. VSET<X>:<NR2>
# Description:Sets the output voltage.
# Example VSET1:20.50
# Sets the CH1 voltage to 20.50V
def set_voltage(channel=1, voltage=0):
    _send_command('VSET{}:{:05.2f}'.format(channel, voltage))
    time.sleep(0.05)

# 4. VSET<X>?
# Description:Returns the output voltage setting.
# Example VSET1?
# Returns the CH1 voltage setting
def get_voltage(channel=1):
    _send_command('VSET{}?'.format(channel))
    return float(_receive_command(5))

# 5. IOUT<X>?
# Description:Returns the actual output current.
# Example IOUT1?
# Returns the CH1 output current
def get_actual_current(channel=1):
    _send_command('IOUT{}?'.format(channel))
    return float(_receive_command(5))

# 6. VOUT<X>?
# Description:Returns the actual output voltage.
# Example VOUT1?
# Returns the CH1 output voltage
def get_actual_voltage(channel=1):
    _send_command('VOUT{}?'.format(channel))
    return float(_receive_command(5))

# 7. BEEP<Boolean>
# Description:Turns on or off the beep. Boolean: boolean logic.
# Example BEEP1 Turns on the beep.
def set_beep(on):
    if on:
        _send_command('BEEP1')
    else:
        _send_command('BEEP0')
    time.sleep(0.05)

# 8. OUT<Boolean>
# Description:Turns on or off the output.
# Boolean:0 OFF,1 ON
# Example: OUT1 Turns on the output
def set_output(on):
    if on:
        _send_command('OUT1')
    else:
        _send_command('OUT0')
    time.sleep(0.05)

# 9. STATUS?
# Description:Returns the POWER SUPPLY status.
# Contents 8 bits in the following format
# Bit Item Description
# 0 CH1 0=CC mode, 1=CV mode
# 1 CH2 0=CC mode, 1=CV mode
# 2, 3 Tracking 00=Independent, 01=Tracking series,11=Tracking parallel
# 4 Beep 0=Off, 1=On
# 5 Lock 0=Lock, 1=Unlock
# 6 Output 0=Off, 1=On
# 7 N/A N/A
def get_status():
    if m_device is None:
        print('ERROR: no device connected')
        return ''

    m_device.write('STATUS?'.encode('ascii'))
    status = m_device.read(1)[0]
    ch1 = (status & 0b10000000) >> 7
    ch2 = (status & 0b01000000) >> 6
    tracking = (status & 0b00110000) >> 4
    beeb = (status & 0b00001000) >> 3
    lock = (status & 0b00000100) >> 2
    output = (status & 0b00000010) >> 1
    return {'ch1':ch1, 'ch2':ch2, 'tracking':tracking, 'beeb':beeb, 'lock':lock, 'output':output}

# 10. *IDN?
# Description:Returns the KA3005P identification.
# Example *IDN?
# Contents TENMA 72‐2535 V2.0 (Manufacturer, model name,).

# 11. RCL<NR1>
# Description:Recalls a panel setting.
# NR1 1 – 5: Memory number 1 to 5
# Example RCL1 Recalls the panel setting stored in memory number 1
def recall(nr):
    _send_command('RCL{}'.format(nr))
    time.sleep(0.05)

# 12. SAV<NR1>
# Description:Stores the panel setting.
# NR1 1 – 5: Memory number 1 to 5
# Example: SAV1 Stores the panel setting in memory number 1
def store(nr):
    _send_command('SAV{}'.format(nr))
    time.sleep(0.1)

# 13. OCP< Boolean >
# Description:Stores the panel setting.
# Boolean: 0 OFF, 1 ON
# Example: OCP1 Turns on the OCP
def set_ocp(on):
    if on:
        _send_command('OCP1')
    else:
        _send_command('OCP0')
    time.sleep(0.05)

# 14. OVP< Boolean >
# Description:Turns on the OVP.
# Boolean: 0 OFF, 1 ON
# Example: OVP1 Turns on the OVP
def set_ovp(on):
    if on:
        _send_command('OVP1')
    else:
        _send_command('OVP0')
    time.sleep(0.05)


def charge_battery():
    print('charging battery...')
    set_output(False)
    set_current(1, m_precharge_current_level)
    set_voltage(1, m_constand_voltage_level)
    set_ocp(False)
    set_ovp(False)
    set_output(True)

    voltage = get_actual_voltage(1)
    ui_feedback = 0
    while voltage < m_precharge_voltage_level:
        voltage = get_actual_voltage(1)
        current = get_actual_current(1)
        if ui_feedback == 0:
            print('precharge phase (actual {} V, {} A)'.format(voltage, current))
        time.sleep(1)
        ui_feedback = (ui_feedback + 1) % (60 * 5)

    set_current(1, m_constand_current_level)

    voltage = get_actual_voltage(1)
    ui_feedback = 0
    while voltage < m_constand_voltage_level:
        voltage = get_actual_voltage(1)
        current = get_actual_current(1)
        if ui_feedback == 0:
            print('constand current phase (actual {} V, {} A)'.format(voltage, current))
        time.sleep(1)
        ui_feedback = (ui_feedback + 1) % (60 * 5)

    current = get_actual_current(1)
    ui_feedback = 0
    while current > m_end_of_current_level:
        voltage = get_actual_voltage(1)
        current = get_actual_current(1)
        if ui_feedback == 0:
            print('constand voltage phase (actual {} V, {} A)'.format(voltage, current))
        time.sleep(1)
        ui_feedback = (ui_feedback + 1) % (60 * 5)

    print('battery fully charged')
    set_output(False)


def get_battery_discharge_voltage(channel=1):
    supply_voltage = get_actual_voltage(channel)

    if m_series_discharge_resistor == 0:
        return supply_voltage

    current = get_actual_current(channel)
    return m_series_discharge_resistor * current - supply_voltage


def discharge_battery():
    print('discharging battery...')
    set_output(False)
    set_current(1, m_typical_discharge_current)
    if m_series_discharge_resistor == 0:
        set_voltage(1, m_soc_empty_voltage_level)
        set_ovp(False)
    else:
        set_voltage(1, m_series_discharge_resistor * m_typical_discharge_current -
                    m_constand_voltage_level +
                    (m_constand_voltage_level - m_soc_empty_voltage_level))
        #set_ovp(True)
    set_ocp(False)
    set_output(True)

    voltage = get_battery_discharge_voltage(1)
    ui_feedback = 0
    while voltage > m_soc_empty_voltage_level:
        voltage = get_battery_discharge_voltage(1)
        current = get_actual_current(1)
        if ui_feedback == 0:
            print('discharge phase (actual {} V, {} A)'.format(voltage, current))
        time.sleep(1)
        ui_feedback = (ui_feedback + 1) % (60 * 5)

    set_output(False)
    print('battery fully discharged')


# set the default log level
logging.basicConfig(level=logging.WARNING, stream=sys.stdout, format=FORMAT)

# get all command line options
args = get_command_line_arguments()

# handle individual commands
if args.verbose_level is not None:
    m_verbose_level = args.verbose_level
logging.getLogger().setLevel(m_verbose_level * 10)

if args.serial_port is not None:
    m_serial_port = args.serial_port
if args.baud_rate != '':
    m_baud_rate = args.baud_rate
if args.skip_check is not None:
    m_skip_check = args.skip_check
if args.precharge_voltage_level is not None:
    m_precharge_voltage_level = args.precharge_voltage_level
if args.precharge_current_level is not None:
    m_precharge_current_level = args.precharge_current_level
if args.constand_voltage_level is not None:
    m_constand_voltage_level = args.constand_voltage_level
if args.constand_current_level is not None:
    m_constand_current_level = args.constand_current_level
if args.end_of_current_level is not None:
    m_end_of_current_level = args.end_of_current_level
if args.total_capacity is not None:
    m_total_capacity = args.total_capacity

# prefix the comport to support ports above COM9
if platform.system() == 'Windows':
    m_serial_port = '\\\\.\\' + m_serial_port

print('- precharge voltage level = {:4.2f} V'.format(m_precharge_voltage_level))
print('- precharge current level = {:.0f} mA'.format(m_precharge_current_level * 1000))
print('- constand voltage level  = {:4.2f} V'.format(m_constand_voltage_level))
print('- constand current level  = {:.0f} mA'.format(m_constand_current_level * 1000))
print('- end of current_level    = {:.0f} mA'.format(m_end_of_current_level * 1000))
print('- total capacity          = {:.0f} mA/h'.format(m_total_capacity * 1000))

if m_precharge_current_level > m_max_current or \
   m_constand_current_level > m_max_current or \
   m_end_of_current_level > m_max_current or \
   m_typical_discharge_current > m_max_current:
    print('ERROR: one of the current settings exceeds the maximum allowed current ({:.0f} mA)' \
          .format(m_max_current * 1000))
    sys.exit(-1)

if m_series_discharge_resistor > 0:
    if m_constand_voltage_level > m_series_discharge_resistor * m_typical_discharge_current:
        print('WARNING: the series-discharge-resistor is not large enough to create a positive voltage on the power supply')
    if m_series_discharge_resistor * m_typical_discharge_current - m_soc_empty_voltage_level > \
       DEFAULT_MAX_VOLTAGE_POWER_SUPPLY:
        print('WARNING: the series-discharge-resistor is to large to create the correct voltage on the battery')

# all commands below require a connected device
res = open_device(port=m_serial_port, baud_rate=m_baud_rate, skip_check=m_skip_check)
if res != 0:
    sys.exit(-res)

charge_battery()
#discharge_battery()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020, Chaim Zax <chaim.zax@gmail.com>
#

import argparse
import os
import sys
import signal
import logging
import platform
import time
import threading
from tenma import Tenma

VERSION = "1.0"
FORMAT = '%(asctime)-15s %(levelname)s %(filename)s:%(lineno)d %(message)s'
DEFAULT_CONFIG = '~/.tenma-config.py'
DEFAULT_MAX_VOLTAGE_POWER_SUPPLY = 30
DEFAULT_PRECHARGE_VOLTAGE_LEVEL = 3.00
DEFAULT_PRECHARGE_CURRENT_LEVEL = 0.010
DEFAULT_CONSTANT_VOLTAGE_LEVEL = 4.20
DEFAULT_CONSTANT_CURRENT_LEVEL = 0.120
DEFAULT_END_OF_CURRENT_LEVEL = 0.020
DEFAULT_TOTAL_CAPACITY = 0.500
# DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL = 3.10
DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL = 3.00
DEFAULT_MAX_CURRENT = 1.000
DEFAULT_TYPICAL_DISCHARGE_CURRENT = 0.036
DEFAULT_SERIES_DISCHARGE_RESISTOR = 127.4
DEFAULT_DECAY_TIME = 60 * 10
DEFAULT_LUT_STEPS = 20

m_description = """
This tool"""
m_epilog = "battery-profiler.py v{:s}, Copyright (c) 2020, Chaim Zax <chaim.zax@gmail.com>" \
           .format(VERSION)
m_tenma = Tenma()
m_running = True
m_discharge_test = False
m_pause_lock = threading.Lock()

def signal_handler(sig, frame):
    global m_running
    print('')
    print('aborting...')
    m_running = False
    sys.exit(0)


def get_command_line_arguments():
    parser = argparse.ArgumentParser(description=m_description, epilog=m_epilog)

    parser.add_argument("-v", "--version", action='version', version=VERSION)
    parser.add_argument('-V', '--verbose-level', action='store', type=int, default=None,
                        help='set the verbose level, where 1=DEBUG, 2=INFO, 3=WARNING (default),' +
                             ' 4=ERROR, 5=CRITICAL')
    parser.add_argument('-c', '--config',
                        action='store', default=None,
                        help='load command line options from a configuration file')
    parser.add_argument('-b', '--baud-rate',
                        action='store', default=Tenma.DEFAULT_BAUD_RATE, type=int,
                        help='set the baud-rate of the serial port (default {})'
                        .format(Tenma.DEFAULT_BAUD_RATE))
    parser.add_argument('-p', '--serial-port',
                        action='store', default='',
                        help="set the serial port (default '{}')".format(Tenma.DEFAULT_SERIAL_PORT_LINUX))
    parser.add_argument('-K', '--skip-check',
                        action='store_true', default=None,
                        help="skip sanity/device checking on start-up")
    parser.add_argument('-PV', '--precharge-voltage-level',
                        action='store', default=DEFAULT_PRECHARGE_VOLTAGE_LEVEL, type=float,
                        help='(default {} V)'.format(DEFAULT_PRECHARGE_VOLTAGE_LEVEL))
    parser.add_argument('-PC', '--precharge-current-level',
                        action='store', default=DEFAULT_PRECHARGE_CURRENT_LEVEL, type=float,
                        help='(default {} A)'.format(DEFAULT_PRECHARGE_CURRENT_LEVEL))
    parser.add_argument('-CV', '--constant-voltage-level',
                        action='store', default=DEFAULT_CONSTANT_VOLTAGE_LEVEL, type=float,
                        help='(default {} V)'.format(DEFAULT_CONSTANT_VOLTAGE_LEVEL))
    parser.add_argument('-CC', '--constant-current-level',
                        action='store', default=DEFAULT_CONSTANT_CURRENT_LEVEL, type=float,
                        help='(default {} A)'.format(DEFAULT_CONSTANT_CURRENT_LEVEL))
    parser.add_argument('-EC', '--end-of-current-level',
                        action='store', default=DEFAULT_END_OF_CURRENT_LEVEL, type=float,
                        help='(default {} A)'.format(DEFAULT_END_OF_CURRENT_LEVEL))
    parser.add_argument('-C', '--total-capacity',
                        action='store', default=DEFAULT_TOTAL_CAPACITY, type=float,
                        help='value in A/h at 3.7V (default {} A/h)'
                        .format(DEFAULT_TOTAL_CAPACITY))
    parser.add_argument('-EV', '--soc-empty-voltage-level',
                        action='store', default=DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL, type=float,
                        help='(default {} V)'.format(DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL))
    parser.add_argument('-MC', '--max-current',
                        action='store', default=DEFAULT_MAX_CURRENT, type=float,
                        help='(default {} A)'.format(DEFAULT_MAX_CURRENT))
    parser.add_argument('-DC', '--typical-discharge-current',
                        action='store', default=DEFAULT_TYPICAL_DISCHARGE_CURRENT, type=float,
                        help='(default {} A)'.format(DEFAULT_TYPICAL_DISCHARGE_CURRENT))
    parser.add_argument('-DR', '--series-discharge-resistor',
                        action='store', default=DEFAULT_SERIES_DISCHARGE_RESISTOR, type=float,
                        help='(default {} Ohm)'.format(DEFAULT_SERIES_DISCHARGE_RESISTOR))

    arguments = parser.parse_args()
    return arguments


def charge_battery():
    global m_running, m_discharge_test

    print('charging battery...')
    m_discharge_test = False
    m_tenma.set_output(False)
    m_tenma.set_current(1, m_precharge_current_level)
    m_tenma.set_voltage(1, m_constant_voltage_level)
    m_tenma.set_ocp(False)
    m_tenma.set_ovp(False)
    m_tenma.set_output(True)

    voltage = m_tenma.get_actual_voltage(1)
    #ui_feedback = 0
    while voltage < m_precharge_voltage_level and m_running:
        with m_pause_lock:
            pass  # just continue if we are not paused
        voltage = m_tenma.get_actual_voltage(1)
        current = m_tenma.get_actual_current(1)
        #if ui_feedback == 0:
        #    print('pre-charge phase (actual {} V, {} A)'.format(voltage, current))
        time.sleep(1)
        #ui_feedback = (ui_feedback + 1) % (60 * 5)

    if m_running:
        m_tenma.set_current(1, m_constant_current_level)

    voltage = m_tenma.get_actual_voltage(1)
    #ui_feedback = 0
    while voltage < m_constant_voltage_level and m_running:
        with m_pause_lock:
            pass  # just continue if we are not paused
        voltage = m_tenma.get_actual_voltage(1)
        current = m_tenma.get_actual_current(1)
        #if ui_feedback == 0:
        #    print('constant current phase (actual {} V, {} A)'.format(voltage, current))
        time.sleep(1)
        #ui_feedback = (ui_feedback + 1) % (60 * 5)

    current = m_tenma.get_actual_current(1)
    #ui_feedback = 0
    while current > m_end_of_current_level and m_running:
        with m_pause_lock:
            pass  # just continue if we are not paused
        voltage = m_tenma.get_actual_voltage(1)
        current = m_tenma.get_actual_current(1)
        #if ui_feedback == 0:
        #    print('constant voltage phase (actual {} V, {} A)'.format(voltage, current))
        time.sleep(1)
        #ui_feedback = (ui_feedback + 1) % (60 * 5)

    if m_running:
        print('')
        print('battery fully charged')
        m_running = False
    m_tenma.set_output(False)


def get_battery_voltage(channel=1):
    if m_discharge_test:
        return get_battery_discharge_voltage(channel)
    return m_tenma.get_actual_voltage(channel)


def get_battery_discharge_voltage(channel=1):
    supply_voltage = m_tenma.get_actual_voltage(channel)

    if m_series_discharge_resistor == 0:
        return supply_voltage

    current = m_tenma.get_actual_current(channel)
    return m_series_discharge_resistor * current - supply_voltage


def discharge_battery():
    global m_running, m_discharge_test

    print('discharging battery...')
    m_discharge_test = True
    m_tenma.set_output(False)
    m_tenma.set_current(1, m_typical_discharge_current)
    if m_series_discharge_resistor == 0:
        m_tenma.set_voltage(1, m_soc_empty_voltage_level)
        m_tenma.set_ovp(False)
    else:
        m_tenma.set_voltage(1, m_series_discharge_resistor * m_typical_discharge_current -
                            m_constant_voltage_level +
                            (m_constant_voltage_level - m_soc_empty_voltage_level))
        m_tenma.set_ovp(True)
    m_tenma.set_ocp(False)
    m_tenma.set_output(True)

    voltage = get_battery_discharge_voltage(1)
    #ui_feedback = 0
    while voltage > m_soc_empty_voltage_level and m_running:
        with m_pause_lock:
            pass  # just continue if we are not paused
        voltage = get_battery_discharge_voltage(1)
        current = m_tenma.get_actual_current(1)
        #if ui_feedback == 0:
        #    print('discharge phase (actual {} V, {} A)'.format(voltage, current))
        time.sleep(1)
        #ui_feedback = (ui_feedback + 1) % (60 * 5)

    if m_running:
        print('')
        print('battery fully discharged')
        m_running = False
    m_tenma.set_output(False)


# initialize defaults
m_verbose_level = Tenma.DEFAULT_VERBOSE_LEVEL
if platform.system() == 'Windows':
    m_serial_port = Tenma.DEFAULT_SERIAL_PORT_WIN
else:
    m_serial_port = Tenma.DEFAULT_SERIAL_PORT_LINUX
m_baud_rate = Tenma.DEFAULT_BAUD_RATE
m_skip_check = Tenma.DEFAULT_SKIP_CHECK
m_device = None
m_device_id = None
m_device_type = None
m_precharge_voltage_level = DEFAULT_PRECHARGE_VOLTAGE_LEVEL
m_precharge_current_level = DEFAULT_PRECHARGE_CURRENT_LEVEL
m_constant_voltage_level = DEFAULT_CONSTANT_VOLTAGE_LEVEL
m_constant_current_level = DEFAULT_CONSTANT_CURRENT_LEVEL
m_end_of_current_level = DEFAULT_END_OF_CURRENT_LEVEL
m_total_capacity = DEFAULT_TOTAL_CAPACITY
m_soc_empty_voltage_level = DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL
m_max_current = DEFAULT_MAX_CURRENT
m_typical_discharge_current = DEFAULT_TYPICAL_DISCHARGE_CURRENT
m_series_discharge_resistor = DEFAULT_SERIES_DISCHARGE_RESISTOR
m_decay_time = DEFAULT_DECAY_TIME

# get all command line options
args = get_command_line_arguments()

# load configuration file(s)
home = os.path.expanduser("~")
default_config = DEFAULT_CONFIG.replace('~', home)
if os.path.isfile(default_config):
    exec(open(default_config).read())

if args.config is not None and os.path.isfile(args.config):
    exec(open(args.config).read())

# handle individual commands
if args.verbose_level is not None:
    m_verbose_level = args.verbose_level
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
if args.constant_voltage_level is not None:
    m_constant_voltage_level = args.constant_voltage_level
if args.constant_current_level is not None:
    m_constant_current_level = args.constant_current_level
if args.end_of_current_level is not None:
    m_end_of_current_level = args.end_of_current_level
if args.total_capacity is not None:
    m_total_capacity = args.total_capacity
if args.soc_empty_voltage_level is not None:
    m_soc_empty_voltage_level = args.soc_empty_voltage_level
if args.max_current is not None:
    m_max_current = args.max_current
if args.typical_discharge_current is not None:
    m_typical_discharge_current = args.typical_discharge_current
if args.series_discharge_resistor is not None:
    m_series_discharge_resistor = args.series_discharge_resistor

# configure logging
logging.basicConfig(level=logging.WARNING, stream=sys.stdout, format=FORMAT)
logging.getLogger().setLevel(m_verbose_level * 10)
m_tenma.set_verbose_level(m_verbose_level)

# prefix the comport to support ports above COM9
if platform.system() == 'Windows':
    m_serial_port = '\\\\.\\' + m_serial_port

# handle CTRL-C
signal.signal(signal.SIGINT, signal_handler)

# print and check arguments/configuration
print('- pre-charge voltage level  = {:4.2f} V'.format(m_precharge_voltage_level))
print('- pre-charge current level  = {:.0f} mA'.format(m_precharge_current_level * 1000))
print('- constant voltage level    = {:4.2f} V'.format(m_constant_voltage_level))
print('- constant current level    = {:.0f} mA'.format(m_constant_current_level * 1000))
print('- end of current level      = {:.0f} mA'.format(m_end_of_current_level * 1000))
print('- total capacity            = {:.0f} mA/h ({:.0f} mW/h)'
      .format(m_total_capacity * 1000, m_total_capacity * 1000 * 3.7))
print('- soc empty voltage level   = {:4.2f} V'.format(m_soc_empty_voltage_level))
print('- max current               = {:.0f} mA'.format(m_max_current * 1000))
print('- typical discharge current = {:.0f} mA'.format(m_typical_discharge_current * 1000))
print('- series discharge resistor = {} Ohm'.format(m_series_discharge_resistor))
print('- decay time                = {} s'.format(m_decay_time))

if m_precharge_current_level > m_max_current or \
   m_constant_current_level > m_max_current or \
   m_end_of_current_level > m_max_current or \
   m_typical_discharge_current > m_max_current:
    print('ERROR: one of the current settings exceeds the maximum allowed current ({:.0f} mA)'
          .format(m_max_current * 1000))
    sys.exit(-1)

if m_series_discharge_resistor > 0:
    if m_constant_voltage_level > m_series_discharge_resistor * m_typical_discharge_current:
        print('WARNING: the series-discharge-resistor is not large enough to create a positive voltage '
              'on the power supply')
    if m_series_discharge_resistor * m_typical_discharge_current - m_soc_empty_voltage_level > \
       DEFAULT_MAX_VOLTAGE_POWER_SUPPLY:
        print('WARNING: the series-discharge-resistor is to large to create the correct voltage on the battery')

# all commands below require a connected power supply
res = m_tenma.open(serial_port=m_serial_port, baud_rate=m_baud_rate, skip_check=m_skip_check)
if res != 0:
    sys.exit(-res)

# measure state-of-charge and creat the look-up table
total_capacity = m_total_capacity * 3.7  # in W/h
delta_capacity = total_capacity / DEFAULT_LUT_STEPS  # measure every 5 % increase
actual_capacity = 0.0
delay = 1  # in seconds
start_clock = time.perf_counter()

# the actual charging/discharging is done independently (in a separate thread)
charger = threading.Thread(target=charge_battery)
#charger = threading.Thread(target=discharge_battery)
charger.start()

prev_clock = start_clock
prev_capacity = actual_capacity
while m_running:
    voltage = get_battery_voltage(1)
    if voltage == 0:
        time.sleep(0.1)
        continue  # charging/discharging not yet started

    current = m_tenma.get_actual_current(1)
    clock = time.perf_counter()
    actual_capacity += voltage * current * (clock - prev_clock) / 3600
    prev_clock = clock
    print('{:.2f} V, {:.3f} A, {:.0f} mW/h ({:.0f} mW/h), {:.1f} %, {:.0f} s'
          .format(voltage, current, actual_capacity * 1000, total_capacity * 1000,
                  100 * actual_capacity / total_capacity, clock - start_clock), end='\r')

    if actual_capacity - prev_capacity >= delta_capacity:
        print('')
        print('capacity {:.0f} mW/h ({} %), pausing for {} seconds'
              .format(actual_capacity - prev_capacity, 100 / DEFAULT_LUT_STEPS, m_decay_time))
        prev_capacity = actual_capacity
        with m_pause_lock:
            m_tenma.set_output(False)
            time.sleep(m_decay_time)
            m_tenma.set_output(True)

    time.sleep(delay)

print('')
charger.join()
m_tenma.set_output(False)

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

try:
    from Phidget22.Phidget import *
    from Phidget22.Devices.DigitalOutput import *

    m_relays_connected = True
except ImportError as error:
    print('disabling relays, Phidget library not found (see https://www.phidgets.com/docs/Language_-_Python)')
    m_relays_connected = False
from tenma import Tenma

VERSION = "1.0"
FORMAT = '%(asctime)-15s %(levelname)s %(filename)s:%(lineno)d %(message)s'
DEFAULT_CONFIG = '~/.tenma-config.py'
DEFAULT_PRECHARGE_VOLTAGE_LEVEL = 3.00
DEFAULT_PRECHARGE_CURRENT_LEVEL = 0.010
DEFAULT_CONSTANT_VOLTAGE_LEVEL = 4.20
DEFAULT_CONSTANT_CURRENT_LEVEL = 0.250  # between 1 and 0.5 C (total-capacity)
DEFAULT_END_OF_CURRENT_LEVEL = 0.025
DEFAULT_TOTAL_CAPACITY = 0.500
DEFAULT_NOMINAL_VOLTAGE = 3.7
DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL = 3.10
DEFAULT_MAX_CURRENT = 1.000
DEFAULT_TYPICAL_DISCHARGE_CURRENT = 0.036
DEFAULT_SERIES_CONNECTION_RESISTANCE = 0.94  # increase if measured voltage during charge is too high
DEFAULT_SERIES_DISCHARGE_RESISTOR = 118.8 + 7.75  # increase if measured voltage during discharge is too low
DEFAULT_DECAY_TIME = 60 * 15
DEFAULT_LUT_STEPS = 20

RELAYS_NEG_CON = 0
RELAYS_POS_CON = 3
RELAYS_ENABLE_BATTERY = 1
RELAYS_RESISTOR = 2

m_description = """
This tool"""
m_epilog = "battery-profiler.py v{:s}, Copyright (c) 2020, Chaim Zax <chaim.zax@gmail.com>" \
           .format(VERSION)
m_tenma = Tenma()
m_relays = [None, None, None, None]
m_resistor = [0, 0, 0, 0]
m_running = True
m_device = None
m_device_id = None
m_device_type = None
m_set_ovp = False
m_pause_lock = threading.Lock()
m_polling_delay = 1  # in seconds

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
    parser.add_argument('-s', '--skip-check',
                        action='store_true', default=None,
                        help="skip sanity/device checking on start-up")
    parser.add_argument('-d', '--discharge',
                        action='store_true', default=None,
                        help="discharge the battery (default will charge battery)")
    parser.add_argument('-MV', '--max-voltage-power-supply',
                        action='store', default=Tenma.DEFAULT_POWER_SUPPLY_MAX_VOLTAGE, type=float,
                        help='(default {} V)'.format(Tenma.DEFAULT_POWER_SUPPLY_MAX_VOLTAGE))
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
                        help='value in A/h at {} V (default {} A/h)'
                        .format(DEFAULT_NOMINAL_VOLTAGE, DEFAULT_TOTAL_CAPACITY))
    parser.add_argument('-NV', '--nominal-voltage',
                        action='store', default=DEFAULT_NOMINAL_VOLTAGE, type=float,
                        help='(default {} V)'.format(DEFAULT_NOMINAL_VOLTAGE))
    parser.add_argument('-EV', '--soc-empty-voltage-level',
                        action='store', default=DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL, type=float,
                        help='(default {} V)'.format(DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL))
    parser.add_argument('-MC', '--max-current',
                        action='store', default=DEFAULT_MAX_CURRENT, type=float,
                        help='(default {} A)'.format(DEFAULT_MAX_CURRENT))
    parser.add_argument('-DC', '--typical-discharge-current',
                        action='store', default=DEFAULT_TYPICAL_DISCHARGE_CURRENT, type=float,
                        help='(default {} A)'.format(DEFAULT_TYPICAL_DISCHARGE_CURRENT))
    parser.add_argument('-CR', '--series-connection-resistance',
                        action='store', default=DEFAULT_SERIES_CONNECTION_RESISTANCE, type=float,
                        help='(default {} Ohm)'.format(DEFAULT_SERIES_CONNECTION_RESISTANCE))
    parser.add_argument('-DR', '--series-discharge-resistor',
                        action='store', default=DEFAULT_SERIES_DISCHARGE_RESISTOR, type=float,
                        help='(default {} Ohm)'.format(DEFAULT_SERIES_DISCHARGE_RESISTOR))
    parser.add_argument('-DT', '--decay-time',
                        action='store', default=DEFAULT_DECAY_TIME, type=int,
                        help='(default {} s)'.format(DEFAULT_DECAY_TIME))
    parser.add_argument('-L', '--lut-steps',
                        action='store', default=DEFAULT_LUT_STEPS, type=int,
                        help='(default {})'.format(DEFAULT_LUT_STEPS))

    arguments = parser.parse_args()
    return arguments


def get_battery_voltage(channel=Tenma.CHANNEL_1, discharge=False):
    supply_voltage = m_tenma.get_actual_voltage(channel)
    current = m_tenma.get_actual_current(channel)

    if discharge:
        return ((m_resistor[RELAYS_ENABLE_BATTERY] + m_resistor[RELAYS_RESISTOR]) * current
                - supply_voltage)
    return (supply_voltage
            - (m_resistor[RELAYS_ENABLE_BATTERY] + m_resistor[RELAYS_RESISTOR]) * current)


def charge_battery():
    global m_running, m_set_ovp

    print('charging battery...')
    m_tenma.set_output(False)
    m_tenma.set_current(Tenma.CHANNEL_1, m_precharge_current_level)
    m_tenma.set_voltage(Tenma.CHANNEL_1, m_constant_voltage_level)
    m_tenma.set_ocp(False)
    m_set_ovp = False
    m_tenma.set_ovp(m_set_ovp)

    attach_battery(enable=True, reverse_polarity=False)
    m_tenma.set_output(True)

    voltage = get_battery_voltage(Tenma.CHANNEL_1, discharge=m_discharge)
    while voltage < m_precharge_voltage_level and m_running:
        with m_pause_lock:
            voltage = get_battery_voltage(Tenma.CHANNEL_1, discharge=m_discharge)
        time.sleep(1)

    if m_running:
        m_tenma.set_current(Tenma.CHANNEL_1, m_constant_current_level)

    voltage = get_battery_voltage(Tenma.CHANNEL_1, discharge=m_discharge)
    while voltage < m_constant_voltage_level and m_running:
        with m_pause_lock:
            voltage = get_battery_voltage(Tenma.CHANNEL_1, discharge=m_discharge)
            current = m_tenma.get_actual_current(Tenma.CHANNEL_1)
            # adjust voltage to make sure the applied battery voltage is as required
            m_tenma.set_voltage(Tenma.CHANNEL_1, m_constant_voltage_level +
                                m_series_connection_resistance * current)
        time.sleep(1)

    current = m_tenma.get_actual_current(Tenma.CHANNEL_1)
    while current > m_end_of_current_level and m_running:
        with m_pause_lock:
            current = m_tenma.get_actual_current(Tenma.CHANNEL_1)
            # adjust voltage to make sure the applied battery voltage is as required
            m_tenma.set_voltage(Tenma.CHANNEL_1, m_constant_voltage_level +
                                m_series_connection_resistance * current)
        time.sleep(1)

    if m_running:
        m_running = False
        time.sleep(m_polling_delay)
        print('')
        print('battery fully charged')
    m_tenma.set_output(False)


def discharge_battery():
    global m_running, m_set_ovp

    print('discharging battery...')
    m_tenma.set_output(False)
    m_tenma.set_current(Tenma.CHANNEL_1, m_typical_discharge_current)
    if m_series_discharge_resistor == 0:
        m_tenma.set_voltage(Tenma.CHANNEL_1, m_soc_empty_voltage_level)
        m_set_ovp = False
        m_tenma.set_ovp(m_set_ovp)
    else:
        m_tenma.set_voltage(Tenma.CHANNEL_1,
                            (m_series_discharge_resistor + m_series_connection_resistance)
                            * m_typical_discharge_current -
                            m_constant_voltage_level +
                            (m_constant_voltage_level - m_soc_empty_voltage_level))
        m_set_ovp = True
        m_tenma.set_ovp(m_set_ovp)
    m_tenma.set_ocp(False)

    attach_battery(enable=True, reverse_polarity=True)
    m_tenma.set_output(True)

    voltage = get_battery_voltage(Tenma.CHANNEL_1, discharge=m_discharge)
    while voltage > m_soc_empty_voltage_level and m_running:
        with m_pause_lock:
            voltage = get_battery_voltage(Tenma.CHANNEL_1, discharge=m_discharge)
        time.sleep(1)

    if m_running:
        m_running = False
        time.sleep(m_polling_delay)
        print('')
        print('battery fully discharged')
    m_tenma.set_output(False)


def attach_battery(enable=True, reverse_polarity=False):
    global m_relays, m_resistor

    if not m_relays_connected:
        return
    if m_relays[0] is None:
        for i in range(4):
            m_relays[i] = DigitalOutput()
            m_relays[i].setChannel(i)
            m_relays[i].openWaitForAttachment(5000)

    m_relays[RELAYS_ENABLE_BATTERY].setState(False)
    time.sleep(0.1)

    if reverse_polarity:
        m_relays[RELAYS_POS_CON].setState(True)
        m_relays[RELAYS_NEG_CON].setState(True)
        m_relays[RELAYS_RESISTOR].setState(False)
        m_resistor[RELAYS_RESISTOR] = m_series_discharge_resistor
    else:
        m_relays[RELAYS_POS_CON].setState(False)
        m_relays[RELAYS_NEG_CON].setState(False)
        m_relays[RELAYS_RESISTOR].setState(True)
        m_resistor[RELAYS_RESISTOR] = 0

    m_relays[RELAYS_ENABLE_BATTERY].setState(enable)
    if enable:
        m_resistor[RELAYS_ENABLE_BATTERY] = m_series_connection_resistance
    else:
        m_resistor[RELAYS_ENABLE_BATTERY] = 1000000000

    time.sleep(0.1)


def open_file(charge=True):
    suffix = ''
    f = None
    for i in range(1, 99):
        try:
            if charge:
                file_name = 'charge-cycle' + suffix + '.csv'
            else:
                file_name = 'discharge-cycle' + suffix + '.csv'

            f = open(file_name, 'x')
            break

        except FileExistsError:
            suffix = '-{:02d}'.format(i)

    if charge:
        f.write('soc (%),llut (mV),hlut (mV)\n')
    else:
        f.write('soc (%),clut (mV)\n')
    return f


def measure_battery_voltage(charge=True, decay_time=0):
    with m_pause_lock:
        set_voltage = m_tenma.get_voltage(Tenma.CHANNEL_1)
        set_current = m_tenma.get_current(Tenma.CHANNEL_1)

        # give the battery time to settle
        attach_battery(enable=False)
        m_tenma.set_output(False)
        time.sleep(decay_time)

        # measure (open) voltage
        m_tenma.set_ovp(False)
        m_tenma.set_voltage(Tenma.CHANNEL_1, m_max_voltage_power_supply)
        m_tenma.set_current(Tenma.CHANNEL_1, 0.001)
        m_tenma.set_output(True)
        attach_battery(enable=True, reverse_polarity=False)
        time.sleep(1)  # give the power supply some time to settle
        voltage = get_battery_voltage(Tenma.CHANNEL_1, discharge=False)
        print('{:.2f} V, resume (dis)charging'.format(voltage))

        # continue (dis)charging
        attach_battery(enable=False)
        m_tenma.set_voltage(Tenma.CHANNEL_1, set_voltage)
        m_tenma.set_current(Tenma.CHANNEL_1, set_current)
        attach_battery(enable=True, reverse_polarity=not charge)
        clock = time.perf_counter()
        time.sleep(1)  # give the power supply some time to settle
        m_tenma.set_ovp(m_set_ovp)
        return voltage, clock


def profile_battery(charge=True):
    # all commands below require a connected power supply
    res = m_tenma.open(serial_port=m_serial_port, baud_rate=m_baud_rate, skip_check=m_skip_check)
    if res != 0:
        sys.exit(-res)

    f = open_file(charge)

    # measure state-of-charge and creat the look-up table
    total_capacity = m_total_capacity * m_nominal_voltage  # in W/h
    delta_capacity = total_capacity / m_lut_steps  # measure every 5 % increase
    actual_capacity = 0.0
    start_clock = time.perf_counter()
    llut = 0
    hlut = 0
    clut = 0

    # the actual charging/discharging is done independently (in a separate thread)
    if charge:
        charger = threading.Thread(target=charge_battery)
    else:
        charger = threading.Thread(target=discharge_battery)
    charger.start()

    prev_clock = start_clock
    prev_capacity = actual_capacity
    while m_running:
        voltage = get_battery_voltage(Tenma.CHANNEL_1, discharge=m_discharge)
        if voltage == 0:
            time.sleep(0.1)
            continue  # charging/discharging not yet started

        current = m_tenma.get_actual_current(Tenma.CHANNEL_1)
        clock = time.perf_counter()
        actual_capacity += voltage * current * (clock - prev_clock) / 3600
        prev_clock = clock
        print('{:.2f} V, {:.3f} A, {:.0f} mW/h ({:.0f} mW/h), {:.1f} %, {:.0f} s'
              .format(voltage, current, actual_capacity * 1000, total_capacity * 1000,
                      100 * actual_capacity / total_capacity, clock - start_clock), end='\r')

        if actual_capacity - prev_capacity >= delta_capacity:
            print('')
            print('capacity {:.0f} mW/h ({:.0f} %), pausing for {} seconds'
                  .format(actual_capacity * 1000, 100 * actual_capacity / total_capacity, m_decay_time))
            prev_capacity = actual_capacity
            voltage, prev_clock = measure_battery_voltage(charge=charge, decay_time=m_decay_time)

        time.sleep(m_polling_delay)

    print('')
    charger.join()
    m_tenma.set_output(False)
    m_tenma.close()
    if m_relays[0] is not None:
        for i in range(3):
            m_relays[i].close()


# initialize defaults
m_verbose_level = Tenma.DEFAULT_VERBOSE_LEVEL
if platform.system() == 'Windows':
    m_serial_port = Tenma.DEFAULT_SERIAL_PORT_WIN
else:
    m_serial_port = Tenma.DEFAULT_SERIAL_PORT_LINUX
m_baud_rate = Tenma.DEFAULT_BAUD_RATE
m_skip_check = Tenma.DEFAULT_SKIP_CHECK
m_discharge = False
m_max_voltage_power_supply = Tenma.DEFAULT_POWER_SUPPLY_MAX_VOLTAGE
m_precharge_voltage_level = DEFAULT_PRECHARGE_VOLTAGE_LEVEL
m_precharge_current_level = DEFAULT_PRECHARGE_CURRENT_LEVEL
m_constant_voltage_level = DEFAULT_CONSTANT_VOLTAGE_LEVEL
m_constant_current_level = DEFAULT_CONSTANT_CURRENT_LEVEL
m_end_of_current_level = DEFAULT_END_OF_CURRENT_LEVEL
m_total_capacity = DEFAULT_TOTAL_CAPACITY
m_nominal_voltage = DEFAULT_NOMINAL_VOLTAGE
m_soc_empty_voltage_level = DEFAULT_SOC_EMPTY_VOLTAGE_LEVEL
m_max_current = DEFAULT_MAX_CURRENT
m_typical_discharge_current = DEFAULT_TYPICAL_DISCHARGE_CURRENT
m_series_connection_resistance = DEFAULT_SERIES_CONNECTION_RESISTANCE
m_series_discharge_resistor = DEFAULT_SERIES_DISCHARGE_RESISTOR
m_decay_time = DEFAULT_DECAY_TIME
m_lut_steps = DEFAULT_LUT_STEPS

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
if args.discharge is not None:
    m_discharge = args.discharge

if args.max_voltage_power_supply is not None:
    m_max_voltage_power_supply = args.max_voltage_power_supply
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
if args.nominal_voltage is not None:
    m_nominal_voltage = args.nominal_voltage
if args.soc_empty_voltage_level is not None:
    m_soc_empty_voltage_level = args.soc_empty_voltage_level
if args.max_current is not None:
    m_max_current = args.max_current
if args.typical_discharge_current is not None:
    m_typical_discharge_current = args.typical_discharge_current
if args.series_connection_resistance is not None:
    m_series_connection_resistance = args.series_connection_resistance
if args.series_discharge_resistor is not None:
    m_series_discharge_resistor = args.series_discharge_resistor
if args.decay_time is not None:
    m_decay_time = args.decay_time
if args.lut_steps is not None:
    m_lut_steps = args.lut_steps

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
print('- max voltage power supply     = {} V'.format(m_max_voltage_power_supply))
print('- pre-charge voltage level     = {:4.2f} V'.format(m_precharge_voltage_level))
print('- pre-charge current level     = {:.0f} mA'.format(m_precharge_current_level * 1000))
print('- constant voltage level       = {:4.2f} V'.format(m_constant_voltage_level))
print('- constant current level       = {:.0f} mA'.format(m_constant_current_level * 1000))
print('- end of current level         = {:.0f} mA'.format(m_end_of_current_level * 1000))
print('- total capacity               = {:.0f} mA/h at {} V ({:.0f} mW/h)'
      .format(m_total_capacity * 1000, m_nominal_voltage,
              m_total_capacity * 1000 * m_nominal_voltage))
print('- nominal voltage              = {} V'.format(m_nominal_voltage))
print('- soc empty voltage level      = {:4.2f} V'.format(m_soc_empty_voltage_level))
print('- max current                  = {:.0f} mA'.format(m_max_current * 1000))
print('- typical discharge current    = {:.0f} mA'.format(m_typical_discharge_current * 1000))
print('- series connection resistance = {} Ohm'.format(m_series_connection_resistance))
print('- series discharge resistor    = {} Ohm'.format(m_series_discharge_resistor))
print('- decay time                   = {} s'.format(m_decay_time))
print('- lut steps                    = {} ({:.1f} %)'.format(m_lut_steps, 100 / m_lut_steps))

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
       m_max_voltage_power_supply:
        print('WARNING: the series-discharge-resistor is to large to create the correct voltage on the battery')

profile_battery(charge=not m_discharge)

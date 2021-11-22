# Tenma library and utilies

Control library for the Tenma power supplies.  The battery-charger tool provides
a convenient cross platform (Linux, Windows  & OS X) command line user interface
to charge most common batteries. The  default is set for 250mAh lithium battery,
but can easily be changed to fit other types.


## The following options are provided with battery-charger.py:

--help
    Show a help message describing the usage and options of the tool.

--version
    Show program's version number and exit.

--verbose-level
    Set the verbose level, where 1=DEBUG, 2=INFO, 3=WARNING (default), 4=ERROR,
    5=CRITICAL

--config
    Load command line options from a configuration file

--baud-rate
    Set the baud-rate of the serial port (default 115200)

--serial-port
    Set the serial port (default '/dev/ttyACM0')

--skip-check
    Skip sanity/device checking on start-up

--discharge
    Discharge the battery (default will charge battery)

--max-voltage-power-supply
    Default 30 V

### charging related options

--precharge-voltage-level
    Default 3.0 V

--precharge-current-level
    Default 0.01 A

--constant-voltage-level
    Default 4.2 V

--constant-current-level
    Default 0.25 A

--end-of-current-level
    Default 0.025 A

--soc-empty-voltage-level
    Default 3.1 V

--series-connection-resistance
    Default 0.00 Ohm

--max-current
    Default 1.0 A

### discharging related options

--constant-voltage-level
    Default 4.2 V

--soc-empty-voltage-level
    Default 3.1 V

--typical-discharge-current
    Default 0.036 A

--series-connection-resistance
    Default 0.00 Ohm

--series-discharge-resistor
    Default 100 Ohm

--max-current
    Default 1.0 A


## Usage Linux

To get the device information the following command could be used:

    ~/tenma$ ./battery-charger.py

Which should result (in the case of the TENMA 72-2540 device) in:

    power supply found with id 'TENMA 72-2540 V2.1' (type 72-2540)

Normally  no additional  option are  required to  run this  tool in  Linux. When
multiple USB  devices are connected the  tool might not find  the (correct) PSU.
In this case look  for an tty USB device by  disconnecting and reconnecting your
PSU while checking which tty USB device dis- and re-appears:

    $ ls /dev/ttyUSB*

Provide the correct device using the '-p' option:

    ~/tenma$ ./battery-charger.py -p /dev/ttyACM0

Or when the udev rules are installed:

    ~/tenma$ ./battery-charger.py -p /dev/tenma-psu

When you get access denied errors running this tool, please refer to the INSTALL
file and  correct group  permissions. If  problems persist  there is  always the
option to  prepend the battery-charger.py  command with the 'sudo'  command (not
advisable).


## Usage Windows

Once the device is  connected using USB a virtual com  port should be available.
Check the 'devices' in the control panel and  look for COM & LPT ports.  The one
you are looking for is called like "USB Serial (COMx)" or "USB CDC (COMx)".  Try
disconnecting and  reconnecting your  PSU while checking  which device  dis- and
re-appears. In the examples below we assume the device was connected to COM3.

To get the device information the following command could be used:

    C:\tenma> C:\Python310\python battery-charger.py -p COM3

Which should result (in the case of the TENMA 72-2540 device) in:

    power supply found with id 'TENMA 72-2540 V2.1' (type 72-2540)

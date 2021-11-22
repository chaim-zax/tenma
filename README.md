# Tenma PSU library and utilies

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
5=CRITICAL.

    --config
Load command line options from a configuration file.

    --baud-rate
Set the baud-rate of the serial port (default 115200).

    --serial-port
Set the serial port (default '/dev/ttyACM0').

    --skip-check
Skip sanity/device checking on start-up.

    --discharge
Discharge the battery (default will charge battery).

    --max-voltage-power-supply
Maximum voltage the current PSU can deliver.

    --precharge-voltage-level
Voltage  threshold   used  to   initially  pre-charge   the  battery   with  the
precharge-current-level before  going to the constant-current  stage. Pre-charge
is the first phase were the battery is checked for proper behavior.

    --precharge-current-level
Current used during  the pre-charge phase. The pre-charge  stage continues until
the voltage reaches the precharge-voltage-level.

    --constant-current-level
Current    used    to   charge    the    battery    until   it    reaches    the
constant-voltage-level.  The constant-current  phase  is the  second stage  when
charging the battery.

    --constant-current-grace-period
Period in  seconds to  startup the  constant-current-level without  checking the
thresholds. Large capacity  batteries might take a few seconds  to settle before
the actual charging current is reached (default 0 s).

    --constant-voltage-level
Voltage    from   which    the   charger    goes   from    constant-current   to
constant-voltage. The  constant-voltage phase is  the third stage  when charging
the battery.

    --end-of-current-level
Current  threshold  to determine  if  the  battery is  full  when  in the  final
(constant-voltage) charging stage.

    --soc-empty-voltage-level
Voltage threshold to determine when the discharge cycle has ended.

    --max-current
Extra safety  check to make  sure the configuration  set never goes  beyond this
current. Increase for large capacity batteries to support fast charging.

    --typical-discharge-current
Current used for discharging.

    --series-connection-resistance
Resistance of the  wires when charging or discharging. Used  when large currents
are used,  to compensate  for the  voltage drop between  PSU and  actual battery
voltage. Tune  by measuring  the voltage  directly on  the battery  (default 0.0
Ohm).

    --series-discharge-resistor
Resistance used for discharging.


### Relevant for charging are:

    --precharge-voltage-level
    --precharge-current-level
    --constant-current-level
    --constant-current-grace-period
    --constant-voltage-level
    --end-of-current-level
    --series-connection-resistance
    --max-current

### Relevant for discharing are:

    --discharge
    --constant-voltage-level
    --soc-empty-voltage-level
    --typical-discharge-current
    --series-connection-resistance
    --series-discharge-resistor
    --max-current


## Usage Linux

To get the device information the following command could be used:

    ~/tenma$ ./battery-charger.py

Which should result (in the case of the TENMA 72-2540 device) in:

    power supply found with id 'TENMA 72-2540 V2.1' (type 72-2540)

Normally no  additional options  are required  to run this  tool in  Linux. When
multiple USB  devices are connected the  tool might not find  the (correct) PSU.
In this case look  for an tty USB device by  disconnecting and reconnecting your
PSU while checking which tty USB device dis- and re-appears:

    $ ls /dev/ttyUSB*

Provide the correct device using the '-p' option:

    ~/tenma$ ./battery-charger.py -p /dev/ttyACM0

Or when the udev rules are installed:

    ~/tenma$ ./battery-charger.py -p /dev/tenma-psu

Provide a specific battery profile using the '-c' option:

    ~/tenma$ ./battery-charger.py -c lithium-250mAh-conf.py

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

    C:\tenma> C:\Python310\python.exe battery-charger.py -p COM3

Which should result (in the case of the TENMA 72-2540 device) in:

    power supply found with id 'TENMA 72-2540 V2.1' (type 72-2540)

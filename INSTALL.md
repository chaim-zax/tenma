Installation instructions
=========================

Dependencies
------------

- python 3.4 or newer
- pyserial


Linux installations
-------------------

This tool requires  access to one of  the tty devices. By  default these devices
can only be  access when a user is  in the group 'plugdev' or  'dialout'. To add
the current user to this group use the following command:

    $ sudo adduser $USER dialout

The change becomes active the next time you log in.

Alternatively install the  udev rules provided by  coping the 99-tenma-psu.rules
file to /etc/udev/rules.d (directory might  vary per distribution). Restart udev
to make changes active (sudo systemctl restart udev).

On most Linux systems you should use the package manager to install new packages
and their  dependencies.  Manual installation  of software these days  is rarely
necessary, and only makes it harder to maintain your system.

On Debian based Linux systems (like Ubuntu):

    $  sudo apt-get install python3-serial

On Fedora and CentOS based Linux systems:

    $  sudo yum install pyserial

On Red Hat based Linux systems:

    $  sudo rpm --install pyserial

On Slackware based Linux systems:

    $  sudo installpkg pyserial

On Arch Linux based Linux systems:

    $  sudo pacman --sync python-pyserial

On Gentoo based Linux systems:

    $  sudo emerge dev-python/pyserial

If every else fails, use the python package manager:

    $  sudo pip install pyserial


Windows installations
---------------------
Windows based systems should install the individual components separately:

* python 3.x
https://www.python.org/downloads/

* pyserial
C:\Python310\Scripts> pip install pyserial

* USB CDC driver (optionally)
https://msdn.microsoft.com/en-us/library/windows/hardware/dn707976(v=vs.85).aspx


OS X installations
------------------
Not tested, but should be possible. The Windows based install instructions
should work here too.

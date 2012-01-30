xen_vm_rescue.py
================

First release - Hereward Cooper <coops@iomart.com>

USAGE
-----
./xen_vm-rescue.py

I probably need to be run from /opt/xensource/sm as that's where all
my XenAPI python friends live.

DESCRIPTION
-----------

This script is designed to "snatch" VMs from a dead XenServer host, and
allow them to be started elsewhere. There are basically three steps:
1) Retrieve a list of VMs running on the selected (dead) XenServer.
2) Forcibly reset their power-state to off.
3) Unlock their storage to allow it to be accessed by the new host.

TODO:
-----
 * Reintroduce SR locking, once I figure out how it works
 * World domination.

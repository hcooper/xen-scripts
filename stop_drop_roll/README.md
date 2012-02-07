Stop, Drop & Roll
=================

Hereward Cooper <coops@fawk.eu>

This script aims to discover VMs are running on a given list
of Xen hosts, save these details and power off the host. Once
power is restored the script can then ensure the VMs are restored
to the same power-state.

The script was first written to aid the migration of a large number
of Xen hosts between physical locations, which where hosting VMs in
a variety of power-states, and with a variety of auto-reboot states.

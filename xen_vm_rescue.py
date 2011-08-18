#!/usr/bin/python

# xen_vm_rescue.py
# First release - Hereward Cooper <coops@iomart.com>

# DESCRIPTION:
# This script is designed to "snatch" VMs from a dead XenServer host, and
# allow them to be started elsewhere. There are basically three steps:
# 1) Retrieve a list of VMs running on the selected (dead) XenServer.
# 2) Forcibly reset their power-state to off.
# 3) Unlock their storage to allow it to be accessed by the new host.

# TODO:
# --> Reintroduce SR locking, once I figure out how it works
# --> World domination.


# Xen Login Details, quite important.
xen_url = "https://localhost/"
xen_user = "root"
xen_password = "Hafyerv6"

import XenAPI
import sys
from pprint import pprint

# Assign some decent colours, because we're worth it.
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''

session = XenAPI.Session(xen_url)
session.login_with_password(xen_user,xen_password)

print bcolors.WARNING + """
#####################################################################

__  __           __     ____  __   ____                           
\ \/ /___ _ __   \ \   / /  \/  | |  _ \ ___  ___  ___ _   _  ___ 
 \  // _ \ '_ \   \ \ / /| |\/| | | |_) / _ \/ __|/ __| | | |/ _ \\
 /  \  __/ | | |   \ V / | |  | | |  _ <  __/\__ \ (__| |_| |  __/
/_/\_\___|_| |_|    \_/  |_|  |_| |_| \_\___||___/\___|\__,_|\___|
                                                                  
v0.1 Hereward Cooper <coops@iomart.com>

#####################################################################
""" + bcolors.ENDC

# Select the dead host from the lists of hosts in the pool
def select_a_host():
	all_hosts = [session.xenapi.host.get_record(x) for x in session.xenapi.host.get_all()]
        count = 0
        print "Please select the dead host:\n"
        for host in all_hosts:
                count = count + 1
                print bcolors.OKGREEN + str(count) + ") " + host["name_label"] + " [UUID:" + host["uuid"] + "]" + bcolors.ENDC
        selected_option = raw_input("Enter Host> ")
        host_uuid = all_hosts[int(selected_option)-1]["uuid"]
        return(host_uuid)


# From the given host, retrieve the list of VMs which lived on it
def retrieve_vm_list(host):
	global resident_vms_record
	resident_vms_record = [session.xenapi.VM.get_record(x) for x in session.xenapi.host.get_resident_VMs(host) if not session.xenapi.VM.get_is_a_template(x) if not session.xenapi.VM.get_is_control_domain(x)]
	if len(resident_vms_record) < 1:
		print "Quitting... no non-management VMs found on this host"
		sys.exit(1)
	else:
		print "\n#####################################################################"
		print "\nThese VMs are resident on " + session.xenapi.host.get_name_label(host) + ":\n"
		for vm in resident_vms_record:
			print  bcolors.OKBLUE + " --> " + vm["name_label"] + " [UUID: " + vm["uuid"] + "]" + bcolors.ENDC
		print "\n#####################################################################"

# For each VM on the dead host reset its power-state to OFF (bye! bye!)
def reset_vm_powerstate(host):
	print "\nNext each VM's powerstate will be forcibly reset to 'Off'. To continue type YES"
	answer = raw_input("Continue?> ")	
	if answer != "YES":
		sys.exit(1)
	else:
		print "\n"
		for vm in resident_vms_record:
			# For each VM reset it's powerstate
			print "Resetting " + vm["name_label"] + " [UUID: " + vm["uuid"] + "]"
			session.xenapi.VM.power_state_reset(session.xenapi.VM.get_by_uuid(vm["uuid"]))

# For each VDI remove its storage lock (aka: shot the lock and kick the door down)
def unlock_storage_improved(session, host):
	print "Proceeding with resetting storage locks..."
	host_key = "host_%s" % host

	for vm in resident_vms_record:
		for vdi_ref in vm["VBDs"]:
			vdi = session.xenapi.VBD.get_VDI(vdi_ref)
			if vdi != "OpaqueRef:NULL":
				print ("Clearing attached status for VDI %s" % vdi)
				session.xenapi.VDI.remove_from_sm_config(vdi, host_key)

# Magic. Don't touch.
host_uuid = select_a_host()
host = session.xenapi.host.get_by_uuid(host_uuid)
retrieve_vm_list(host)
reset_vm_powerstate(host)
unlock_storage_improved(session, host)

print bcolors.OKGREEN + """
#####################################################################
COMPLETE - now go and restart your VMs!
#####################################################################
""" + bcolors.ENDC

# Go get beers.
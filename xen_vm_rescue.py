#!/usr/bin/python

# xen_vm_rescue.py
# First release - Hereward Cooper <coops@iomart.com>

# Description:
# This script is designed to "snatch" VMs from a dead XenServer host, and
# allow them to be started elsewhere. There are basically three steps:
# 1) Retrieve a list of VMs running on the selected (dead) XenServer.
# 2) Forcibly reset their power-state to off.
# 3) Unlock their storage to allow it to be accessed by the new host.


# Todo:
# --> Expand the storage unlocking to handle more than one SR.
# --> Refine the unlock function.
# --> World domination.


# Xen Login Details:
xen_url = "https://localhost/"
xen_user = "root"
xen_password = "oc7Kokphy&ooc"



import XenAPI
import sys
from pprint import pprint

# Assign some decent colours
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


# From the given host, retrieve the list of VMs which lvied on it
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

# For each VM on the dead host reset its power-state to OFF
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

# For each VM find out which SR their drives live on
def list_sr_in_use():
	sr_in_use_complete=[]															# Create an empty list we can list the SRs in

	for vm in resident_vms_record:													# Go through each VM in turn
		for vdi_ref in vm["VBDs"]:													# Get the reference to each vdi connected to the bus
		                vdi = session.xenapi.VBD.get_VDI(vdi_ref)					# Retrieve the VDI itself
		                if vdi != "OpaqueRef:NULL":									# Check it's not NULL
		                        vdi_name = session.xenapi.VDI.get_name_label(vdi)	# Make a note of it's name
		                        vdi_sr = session.xenapi.VDI.get_SR(vdi) 			# Get the storage resource the vdi lives on
		                        sr_in_use_complete.append(vdi_sr)					# Add the storage resource on our list
	
	sr_in_use = dict().fromkeys(sr_in_use_complete).keys()							# Remove repeat entries in the storage resource list
	
	print "\nThis is the list of detected Storage Resources which are in use:\n"
	temp_sr=[]
	for sr in sr_in_use:
		print bcolors.OKBLUE + " --> " + session.xenapi.SR.get_name_label(sr) + " [UUID: " + session.xenapi.SR.get_uuid(sr) + "]" + bcolors.ENDC
		temp_sr.append(session.xenapi.SR.get_uuid(sr))
	print "\n"
	return temp_sr



import util
import lock
from vhdutil import LOCK_TYPE_SR
from cleanup import LOCK_TYPE_RUNNING


def unlock_storage_improved(session, host_uuid):
	#gc_lock = lock.Lock(LOCK_TYPE_RUNNING, sr_uuid)
	#sr_lock = lock.Lock(LOCK_TYPE_SR, sr_uuid)
	#gc_lock.acquire()
	#sr_lock.acquire()

	print "Proceeding with resetting storage locks..."

	host_ref = host_uuid
	host_key = "host_%s" % host_ref

	for vm in resident_vms_record:
		for vdi_ref in vm["VBDs"]:
			vdi = session.xenapi.VBD.get_VDI(vdi_ref)
			if vdi != "OpaqueRef:NULL":
				print ("Clearing attached status for VDI %s" % vdi)
				session.xenapi.VDI.remove_from_sm_config(vdi, host_key)
	print "Done"

	#sr_lock.release()
	#gc_lock.release()



# Unlock each VDI
def unlock_storage(session, host_uuid, sr_uuid):
	gc_lock = lock.Lock(LOCK_TYPE_RUNNING, sr_uuid)
	sr_lock = lock.Lock(LOCK_TYPE_SR, sr_uuid)
	gc_lock.acquire()
	sr_lock.acquire()

	sr_ref = session.xenapi.SR.get_by_uuid(sr_uuid)

	host_ref = host_uuid
	host_key = "host_%s" % host_ref

	# Get list of VDIs on a certain SR
	vdi_recs = session.xenapi.VDI.get_all_records_where("field \"SR\" = \"%s\"" % sr_ref)

	print "Proceeding with resetting storage locks..."
	for vdi_ref, vdi_rec in vdi_recs.iteritems():
		vdi_uuid = vdi_rec["uuid"]
		sm_config = vdi_rec["sm_config"]
		if sm_config.get(host_key):
			util.SMlog("Clearing attached status for VDI %s" % vdi_uuid)
			print ("Clearing attached status for VDI %s" % vdi_uuid)
			session.xenapi.VDI.remove_from_sm_config(vdi_ref, host_key)
	sr_lock.release()
	gc_lock.release()

	print "\n*** COMPLETE *** \n"



host_uuid = select_a_host()
host = session.xenapi.host.get_by_uuid(host_uuid)
retrieve_vm_list(host)
reset_vm_powerstate(host)
#temp_sr = list_sr_in_use()
unlock_storage_improved(session, host)

#host = "OpaqueRef:c399f64b-d03e-c533-3e04-b7602b8eb63b"
#host = "OpaqueRef:5a59de4d-b209-fd50-a484-9504d1973885"
#host = "OpaqueRef:832e4c6e-38d1-4644-8331-87e8f41428eb"
#temp_sr = "4242fef0-bee5-5114-69ec-7c58314fc7d4"
#unlock_storage(session, host, temp_sr)
#!/usr/bin/python

import XenAPI
import sys
from pprint import pprint

session = XenAPI.Session('https://localhost/')
session.login_with_password('root','oc8Groto')

print """
#####################################################################

__  __           __     ____  __   ____                           
\ \/ /___ _ __   \ \   / /  \/  | |  _ \ ___  ___  ___ _   _  ___ 
 \  // _ \ '_ \   \ \ / /| |\/| | | |_) / _ \/ __|/ __| | | |/ _ \\
 /  \  __/ | | |   \ V / | |  | | |  _ <  __/\__ \ (__| |_| |  __/
/_/\_\___|_| |_|    \_/  |_|  |_| |_| \_\___||___/\___|\__,_|\___|
                                                                  
v0.1 Hereward Cooper <coops@iomart.com>

#####################################################################
"""


def select_a_host():
	all_hosts = [session.xenapi.host.get_record(x) for x in session.xenapi.host.get_all()]
        count = 0
        print "Please select the dead host:\n"
        for host in all_hosts:
                count = count + 1
                print str(count) + ") " + host["name_label"] + " [UUID:" + host["uuid"] + "]"
        selected_option = raw_input("Enter Host> ")

        host_uuid = all_hosts[int(selected_option)-1]["uuid"]
        return(host_uuid)


def reset_vm_powerstate(host):
	global resident_vms_record
	resident_vms_record = [session.xenapi.VM.get_record(x) for x in session.xenapi.host.get_resident_VMs(host) if not session.xenapi.VM.get_is_a_template(x) if not session.xenapi.VM.get_is_control_domain(x)]
	if len(resident_vms_record) < 1:
		print "Quitting... no non-management VMs found on this host"
		sys.exit(1)
	else:
		print "\n#####################################################################"
		print "\nThese VMs are resident on " + session.xenapi.host.get_name_label(host) + ":\n"
		for vm in resident_vms_record:
			print " --> " + vm["name_label"] + " [UUID: " + vm["uuid"] + "]"
		print "\n!!! Please check these are the VMs you want to snatch!!!\n"
		print "\n#####################################################################"
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

def list_sr_in_use():
	sr_in_use_complete=[]							# Create an empty list we can list the SRs in

	for vm in resident_vms_record:						# Go through each VM in turn
		for vdi_ref in vm["VBDs"]:					# Get the reference to each vdi connected to the bus
		                vdi = session.xenapi.VBD.get_VDI(vdi_ref)	# Retrieve the VDI itself
		                if vdi != "OpaqueRef:NULL":			# Check it's not NULL
		                        vdi_name = session.xenapi.VDI.get_name_label(vdi)	# Make a note of it's name
		                        vdi_sr = session.xenapi.VDI.get_SR(vdi) # Get the storage resource the vdi lives on
		                        sr_in_use_complete.append(vdi_sr)	# Add the storage resource on our list
	
	sr_in_use = dict().fromkeys(sr_in_use_complete).keys()			# Remove repeat entries in the storage resource list
	
	print "\nThis is the list of detected Storage Resources which are in use:"
	for sr in sr_in_use:
		print " --> " + session.xenapi.SR.get_name_label(sr) + " [UUID: " + session.xenapi.SR.get_uuid(sr) + "]"
		temp_sr = session.xenapi.SR.get_uuid(sr)
	print "\n"
	return temp_sr

### TODO EXPAND TO HANDLE MULTIE SRs


import util
import lock
from vhdutil import LOCK_TYPE_SR
from cleanup import LOCK_TYPE_RUNNING

def unlock_storage(session, host_uuid, sr_uuid):
	gc_lock = lock.Lock(LOCK_TYPE_RUNNING, sr_uuid)
	sr_lock = lock.Lock(LOCK_TYPE_SR, sr_uuid)
	gc_lock.acquire()
	sr_lock.acquire()

	sr_ref = session.xenapi.SR.get_by_uuid(sr_uuid)

	host_ref = host_uuid
	host_key = "host_%s" % host_ref

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
reset_vm_powerstate(host)
temp_sr = list_sr_in_use()

#host = "OpaqueRef:c399f64b-d03e-c533-3e04-b7602b8eb63b"
#host = "OpaqueRef:5a59de4d-b209-fd50-a484-9504d1973885"
#host = "OpaqueRef:832e4c6e-38d1-4644-8331-87e8f41428eb"
#temp_sr = "4242fef0-bee5-5114-69ec-7c58314fc7d4"
unlock_storage(session, host, temp_sr)


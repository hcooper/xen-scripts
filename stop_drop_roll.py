#!/usr/bin/env python

# Originally written to save the list of running VMs, so that after a physical server migration
# an indentical list of VMs can be started. (Avoiding the issue of some VMs set to auto-restart,
# and others not).

import sys, time
import XenAPI
import pickle
import os.path

# Read in our list of Xen hosts (and their connection details)
# [host,user,pass]
from hosts import xenhosts

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

# Let's make sure people aren't mistaken as to who we are.
print bcolors.WARNING + """
########################################################################
  _   _   _     _   _   _   _     _   _   _   _     _     _   _   _   _  
 / \ / \ / \   / \ / \ / \ / \   / \ / \ / \ / \   / \   / \ / \ / \ / \ 
( X | e | n ) ( S | t | o | p ) ( D | r | o | p ) ( & ) ( R | o | l | l )
 \_/ \_/ \_/   \_/ \_/ \_/ \_/   \_/ \_/ \_/ \_/   \_/   \_/ \_/ \_/ \_/ 

v0.1 Hereward Cooper <coops@iomart.com>

########################################################################
""" + bcolors.ENDC

def shutdown(session):

    print "========= " + xenhost[0] + " ========="

    # If status files already exist for this host, prompt to overwrite, otherwise run away.
    if os.path.isfile("hosts/"+xenhost[0]):
        answer = raw_input(bcolors.FAIL + "WARNING: status file already exists for this host. Overwrite? (y/n) " + bcolors.ENDC)
        if answer != "y":
            return


    # Find a non-template VM object
    vms = session.xenapi.VM.get_all()
    print "========= SHUTING DOWN ========="

    statuslist = []

    for vm in vms:
        record = session.xenapi.VM.get_record(vm)

        # We cannot power-cycle templates and we should avoid touching control domains
        if not(record["is_a_template"]) and not(record["is_control_domain"]):
            name = record["name_label"]

            # Build the list of servers and their status
            statuslist.append( [ record["uuid"], record["power_state"], name ] )

            record = session.xenapi.VM.get_record(vm)            

            if record["power_state"] == "Suspended":
                print bcolors.HEADER + record["uuid"] + bcolors.OKGREEN + " HALTING" + bcolors.ENDC
                session.xenapi.VM.resume(vm, False, True) # start_paused = False; force = True
                session.xenapi.VM.clean_shutdown(vm)

            elif record["power_state"] == "Paused":
                print bcolors.HEADER + record["uuid"] + bcolors.OKGREEN + " HALTING" + bcolors.ENDC
                session.xenapi.VM.unpause(vm)
                session.xenapi.VM.clean_shutdown(vm)

            elif record["power_state"] == "Running":
                print bcolors.HEADER + record["uuid"] + bcolors.OKGREEN + " HALTING" + bcolors.ENDC
                session.xenapi.VM.clean_shutdown(vm)

            elif record["power_state"] == "Halted":
                print bcolors.HEADER + record["uuid"] + bcolors.OKBLUE + " keeping halted" + bcolors.ENDC


            pickle.dump(statuslist, open ("hosts/"+xenhost[0], "wb") )

def startup(session):
    print "========= STARTING UP ========="
    # Read in the list of VM statuses
    statuslist = pickle.load( open( "hosts/"+xenhost[0], "rb" ) )

    for uuid,state,name in statuslist:
        vm = session.xenapi.VM.get_by_uuid(uuid)
        record = session.xenapi.VM.get_record(vm)

        if state == "Running" and record["power_state"] == "Running":
            print bcolors.HEADER + record["uuid"] + bcolors.OKBLUE + " keeping running" + bcolors.ENDC

        if state == "Running" and record["power_state"] == "Halted":
            print bcolors.HEADER + record["uuid"] + bcolors.OKGREEN + " STARTING" + bcolors.ENDC
            session.xenapi.VM.start(vm, False, False)

        if state == "Halted" and record["power_state"] == "Halted":
            print bcolors.HEADER + record["uuid"] + bcolors.OKBLUE + " keeping halted" + bcolors.ENDC

        if state == "Halted" and record["power_state"] == "Running":
            print bcolors.HEADER + record["uuid"] + bcolors.FAIL + " HALTING" + bcolors.ENDC
            session.xenapi.VM.clean_shutdown(vm)


if __name__ == "__main__":
    for xenhost in xenhosts:
        session = XenAPI.Session("http://" + xenhost[0])
        session.xenapi.login_with_password(xenhost[1], xenhost[2])

        if sys.argv[1] == "shutdown":
            shutdown(session)
        elif sys.argv[1] == "startup":
            startup(session)

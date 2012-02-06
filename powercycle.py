#!/usr/bin/env python

# Find all VMs on a list of given hosts, record their state, shut them all down,
# and then sutdown the machine.

# Restart all VMs exactly as they were prior to shutdown

import sys, time
import XenAPI
import pickle

xenhosts = [
        #Host, User, Password
        ['10.4.100.152','root','oc7Kokphy&ooc'],
]

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


def main(session):

    # Find a non-template VM object
    vms = session.xenapi.VM.get_all()
    print "========= " + xenhost[0] + " ========="
    print "========= SHUTING DOWN ========="


    statuslist = []

    for vm in vms:
        record = session.xenapi.VM.get_record(vm)

        # We cannot power-cycle templates and we should avoid touching control domains
        if not(record["is_a_template"]) and not(record["is_control_domain"]):
            name = record["name_label"]

            # Build the list of servers and their status
            statuslist.append( [ record["uuid"], record["power_state"] ] )

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

    print "========= STARTING UP ========="
    # Read in the list of VM statuses
    statuslist = pickle.load( open( "hosts/"+xenhost[0], "rb" ) )

    for uuid,state in statuslist:
        vm = session.xenapi.VM.get_by_uuid(uuid)
        record = session.xenapi.VM.get_record(vm)
        name = record["name_label"]

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
    # First acquire a valid session by logging in:
    for xenhost in xenhosts:
        session = XenAPI.Session("http://" + xenhost[0])
        session.xenapi.login_with_password(xenhost[1], xenhost[2])
        main(session)


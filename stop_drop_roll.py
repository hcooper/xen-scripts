#!/usr/bin/env python

# Originally written to save the list of running VMs, so that after a physical server migration
# an identical list of VMs can be started. (Avoiding the issue of some VMs set to auto-restart,
# and others not).

import sys, time
import XenAPI
import pickle
import os.path
import optparse
import time

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

By default all actions are dry run only. See --help for more info

########################################################################
""" + bcolors.ENDC


def shutdown(session):

    print "========= " + xenhost[0] + " ========="

    # If a status files already exist for this host, prompt to overwrite, otherwise run away.
    if os.path.isfile("hosts/"+xenhost[0]):
        # If the skip-existing flag is set, skip already processed hosts
        if SKIP:
            print "Skipping host"
            return
        # Otherwise prompt what to do
        else:
            answer = raw_input(bcolors.FAIL + "WARNING: status file already exists for this host. Overwrite? (y/n) " + bcolors.ENDC)
            if answer != "y":
                return


    # Find a non-template VM object
    vms = session.xenapi.VM.get_all()
    print "========= SHUTING DOWN ========="

    # Start with an empty list of VMs
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
                if DRYRUN:
                    print bcolors.HEADER + record["uuid"] + bcolors.OKGREEN + " HALTING" + bcolors.ENDC
                else:
                    print bcolors.HEADER + record["uuid"] + bcolors.OKGREEN + " HALTING" + bcolors.ENDC
                    session.xenapi.VM.resume(vm, False, True) # start_paused = False; force = True
                    session.xenapi.VM.clean_shutdown(vm)

            elif record["power_state"] == "Paused":
                if DRYRUN:
                    print bcolors.HEADER + record["uuid"] + bcolors.OKGREEN + " HALTING" + bcolors.ENDC
                else:
                    print bcolors.HEADER + record["uuid"] + bcolors.OKGREEN + " HALTING" + bcolors.ENDC
                    session.xenapi.VM.unpause(vm)
                    session.xenapi.VM.clean_shutdown(vm)

            elif record["power_state"] == "Running":
                if DRYRUN:
                    print bcolors.HEADER + record["uuid"] + bcolors.OKGREEN + " HALTING" + bcolors.ENDC
                else:
                    print bcolors.HEADER + record["uuid"] + bcolors.OKGREEN + " HALTING" + bcolors.ENDC
                    session.xenapi.VM.clean_shutdown(vm)

            elif record["power_state"] == "Halted":
                if DRYRUN:
                    print bcolors.HEADER + record["uuid"] + bcolors.OKBLUE + " keeping halted" + bcolors.ENDC
                else:
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

    # Move the status list out the way
    os.rename("hosts/"+xenhost[0], "hosts/"+xenhost[0]+".OLD")


if __name__ == "__main__":

    # Set some defaults
    SKIP=False
    DRYRUN=True

    parser = optparse.OptionParser()
    parser.add_option('--skip', help='skips hosts which already have a status file', dest='skip', default=False, action='store_true')
    parser.add_option('--real', help='skips dry run, and alters VMs power state', dest='real', default=False, action='store_true')
    parser.add_option('--shutdown', help='start the shutdown procedure', dest='shutdown', action='store_true')
    parser.add_option('--startup', help='start the startup procedure', dest='startup', action='store_true')
    (opts, args) = parser.parse_args()

    # Check we're not being told to do something stupid
    if opts.shutdown and opts.startup:
        print "Please only run --shutdown or --startup"
        sys.exit(-1)

    # If the --real flag is set, disable the DRYRUN variable
    if opts.real:
        print bcolors.FAIL + "WARNING - this is for real!" + bcolors.ENDC
        DRYRUN=False
        time.sleep(3)
    print ""

    # If the --skip flag is set, enable the SKIP variable
    if opts.skip:
        SKIP=True

    # Fire up the engines
    for xenhost in xenhosts:
        session = XenAPI.Session("http://" + xenhost[0])
        try:
            session.xenapi.login_with_password(xenhost[1], xenhost[2])
        except:
            print bcolors.FAIL + xenhost[0] + " login failure - skipping to next host" + bcolors.ENDC
            continue

        if opts.shutdown:
            shutdown(session)
        if opts.startup:
            startup(session)

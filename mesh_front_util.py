#!/usr/bin/env python
__author__ = 'Jon Stratton'
import os, re, subprocess, socket, hashlib

net_fs = '/sys/class/net'
net_ifaces = '/etc/network/interfaces'

# List the connected network interfaces.
def get_interface_list(if_type = None):
    if_list = []
    for iface in os.listdir(net_fs):
        if (if_type) and (not iface.startswith(if_type)):
            continue
        if_list.append(iface)
    return(if_list)

def get_interface_state(interface):
    if_state = '';
    with open('%s/%s/operstate' % (net_fs, interface), 'r') as f:
        if_state = f.readline().replace('\n', '')
    return if_state

def get_interface_settings():
    interfaces = []
    interface  = {}
    split_col = re.compile('\s+')
    with open(net_ifaces, 'r') as f: # TODO, read the interfaces.d dir too
        for line in f:
            line = line.replace('\n', '').strip()
            if (not line) or (line.startswith('#')):
               continue
            elif (line.startswith('auto ')) or (line.startswith('source ')) or (line.startswith('allow-hotplug ')):
               continue # I just dont care about these right now
            if (line.startswith('iface ')):
               #New Interface. Add it to our list and start another
               if (interface):
                   interfaces.append(interface)
               interface = {}
            split = split_col.split(line)
            split[0] = split[0].replace('-', '_') # Remove the dashes for sqlite col name
            interface[split[0]] = split[1]
            if (len(split) > 3):
               interface[split[2]] = split[3]
    if (interface):
        interfaces.append(interface)
    return(interfaces)

def get_available_networks(interface = None):
    net_list = []

    # Id no interface is passed in, get the first ip one
    interface = get_interface_list('w')[0]

    # If the interface isnt up, brink it up
    if_upd = 0
    if (get_interface_state(interface) != 'up'):
        set_interface_state(interface, 'up')
        if_upd = 1

    network  = {}
    split_col = re.compile('\s*:\s*')
    cmd = 'sudo iwlist %s scan' % (interface)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
       split_line = split_col.split( line.decode('utf-8') )
       key = split_line[0].strip()
       value = re.sub(r'^"|"$', '', ':'.join( split_line[1:] ).strip() )
       if key.endswith('Address'): # New record found
          key = 'Address'
          net_list.append(network)
          network = {} # Clear it out
       network[key] = value
    retval = p.wait
    net_list.append(network)

    # Take down interface if it was set up
    if (if_upd):
        set_interface_state(interface, 'up')

    return net_list

def do_reboot():
    cmd = 'sudo reboot'
    code = subprocess.call(cmd, shell=True, stdout=None, stderr=None)
    return(code)

def do_halt():
    cmd = 'sudo halt -p now'
    code = subprocess.call(cmd, shell=True, stdout=None, stderr=None)
    return(code)

def set_interface_state(interface, state):
    cmd = 'sudo ip link set %s %s' % (interface, state)
    code = subprocess.call(cmd, shell=True, stdout=None, stderr=None)
    return(code)

def get_hostname():
    return(socket.gethostname())

def set_hostname(hostname):
    cmd = 'sudo hostname %s' % (hostname)
    code = subprocess.call(cmd, shell=True, stdout=None, stderr=None)

    # TODO, /etc/hosts
    return(code)

def get_neighbors():
    # TODO
    return(0)

# Used for generating an IP off of a hostname
def get_bg_by_string(base, bit_groups_count):
    # Build a long number based on string
    total  = 0
    offset = 1
    for c in base[::-1]:
        total = total + (ord(c) * offset)
        offset = offset * 10

    # Pull X 3 digit chunks off and mod them by max size
    bit_groups = []
    offset = 255
    for bg in range(0, bit_groups_count):
        bit_groups.append(str(total % 256))
        total = int(total / 1000)

    return(bit_groups[::-1])


def hash_password(password, salt=''):
    salted_password = password+salt
    return(hashlib.md5(salted_password.encode()))

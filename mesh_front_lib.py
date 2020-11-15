#!/usr/bin/env python3
__author__ = 'Jon Stratton'
import sqlite3, os, re, subprocess, socket, hashlib, random, string, json
from jinja2 import Environment, FileSystemLoader

# Defaults
root = os.path.dirname(os.path.realpath(__file__))
db_file = os.path.join(root, 'db.sqlite3')
env = Environment(loader=FileSystemLoader('templates'))

###################
# Refresh Configs #
###################
    # Basically, saves everything to system files

def refresh_configs():
    mesh_interface = query_setting('mesh_interface')
    uplink_interface = query_setting('uplink_interface')

    mesh_interfaces = [ query_setting('wireless_interface') ]
    gw_mode = 'server' if (uplink_interface) else 'client'

    # Make interfaces Files
    interfaces = query_interface_settings()
    make_interface_config(interfaces, gw_mode, mesh_interfaces)

    # Bridge Interfaces if sharing internet
    if (uplink_interface):
        system_clear_iptables()
        system_bridge_interfaces('bat0', uplink_interface)
        make_sysctl_conf()
    else: # Clear the bridge otherwise
        system_clear_iptables()
        clear_sysctl_conf()

    # DHCP Server if serving internet
    if (query_setting('dhcp_server_interface')):
        make_dnsmasq_conf()
    else:
        clear_dnsmasq_conf()

    return(0)

############
# Wireless #
############

def get_available_wireless_meshes():
    wireless_meshes = []
    for network in system_wifi_networks():
        if (network.get('Mode') == 'Ad-Hoc'):
            wireless_meshes.append(network)
    return(wireless_meshes)

###########
# Network #
###########

###########
# Overlay #
###########

######
# DB #
######

def query_setting(setting):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('SELECT value FROM server_settings WHERE key=?;', (setting,))
    value = ''
    values = c.fetchone()
    if (values):
        value = values[0]
    return(value)

def upsert_setting(setting, value):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('INSERT INTO server_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value;', (setting, value))
    conn.commit()
    return(0)

def upsert_interface(interface):
    ipv     = interface.get('ipv', 4)
    iface   = interface.get('iface', '')
    netmask = interface.get('netmask', '')
    address = interface.get('address', '')
    inet    = interface.get('inet', '')

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('INSERT INTO interface_settings (ipv, iface, inet, address, netmask) VALUES (?, ?, ?, ?, ?) ON CONFLICT(ipv, iface) DO UPDATE SET inet=excluded.inet, address=excluded.address, netmask=excluded.netmask;', (ipv, iface, inet, address, netmask))
    conn.commit()
    return(0)

def query_interface_settings(interface = None, ipv = 4):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    if (interface):
        c.execute('SELECT ipv, iface, inet, address, netmask FROM interface_settings WHERE iface = ? and ipv = ?;', (interface, ipv, ))
    else:
        c.execute('SELECT ipv, iface, inet, address, netmask FROM interface_settings;')
    columns = list(map(lambda x: x[0], c.description))
    columns_length = len(columns)
    
    records = []
    for row in c.fetchall():
        record = {}
        for col_num in range(0, columns_length):
            record[columns[col_num]] = row[col_num]
        records.append(record)

    return(records)

def query_interfaces_configured():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('SELECT iface FROM interface_settings;')
    records = []
    for row in c.fetchall():
        records.append(row[0])
    return(records)

def upsert_user(username, password_hash):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('INSERT INTO user_settings VALUES (?, ?) ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash;', (username, password_hash) )
    conn.commit()
    return(0)

def user_auth(user, password_hash):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('SELECT count(*) FROM user_settings WHERE username=? AND password_hash=?;', (user, password_hash))
    return(c.fetchone()[0])

##########
# System #
##########
    # Mostly our interaction with the system, minus the templating

def system_debug(commands = []):
    commands_and_outputs = []
    for command in commands:
        command_and_output = {'command': command, 'output': []}
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line_bytes in p.stdout.readlines():
            command_and_output['output'].append( line_bytes.decode('utf-8').rstrip() )
        commands_and_outputs.append(command_and_output)
    return(commands_and_outputs)

def system_hostname():
    return(socket.gethostname())

def system_reboot():
    cmd = 'sudo reboot'
    code = subprocess.call(cmd, shell=True, stdout=None, stderr=None)
    return(code)

def system_set_interface_state(interface, state):
    interface = re.sub('[^0-9a-zA-Z]+', '', interface)
    state = re.sub('[^a-zA-Z]+', '', state)
    cmd = 'sudo ip link set %s %s' % (interface, state)
    code = subprocess.call(cmd, shell=True, stdout=None, stderr=None)
    return(code)

def system_get_interface_state(interface):
    if_state = ''
    interface = re.sub('[^0-9a-zA-Z]+', '', interface)
    with open('/sys/class/net/%s/operstate' % (interface), 'r') as f:
        if_state = f.readline().replace('\n', '')
    return if_state

# List the connected network interfaces.
def system_interfaces(if_type = None):
    if_list = []
    for iface in os.listdir('/sys/class/net'):
        if (if_type) and (not iface.startswith(if_type)):
            continue
        if (iface == 'lo'):
            continue
        if_list.append(iface)
    return(if_list)

# Bridge Interfaces if sharing.
def system_bridge_interfaces(w_iface, e_iface):
    w_iface = re.sub('[^0-9a-zA-Z]+', '', w_iface)
    e_iface = re.sub('[^0-9a-zA-Z]+', '', e_iface)
    cmds = [ 'sudo iptables -t nat -A POSTROUTING -o %s -j MASQUERADE' % (e_iface),
            'sudo iptables -A FORWARD -i %s -o %s -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT' % (e_iface, w_iface),
            'sudo iptables -A FORWARD -i %s -o %s -j ACCEPT' % (w_iface, e_iface),
            'sudo iptables-save > /etc/iptables/rules.v4' ]
    for cmd in cmds:
        subprocess.call(cmd, shell=True, stdout=None, stderr=None)
    return(0)

def system_clear_iptables():
    cmds = [ 'sudo iptables -P INPUT ACCEPT',
            'sudo iptables -P FORWARD ACCEPT',
            'sudo iptables -P OUTPUT ACCEPT',
            'sudo iptables -t nat -F',
            'sudo iptables -t mangle -F',
            'sudo iptables -F',
            'sudo iptables -X',
            'sudo iptables-save > /etc/iptables/rules.v4' ]
    for cmd in cmds:
        subprocess.call(cmd, shell=True, stdout=None, stderr=None)
    return(0)

#############################
# System Interface Settings #
#############################
    # TODO, read the interfaces.d dir too

def system_interface_settings(interface):
    interface_settings = {}
    temp_iface = ''
    split_col = re.compile('\s+')
    with open('/etc/network/interfaces', 'r') as f:
        for line in f:
            line = line.replace('\n', '').strip()
            if (not line) or (line.startswith('#')):
               continue
            elif (line.startswith('auto ')) or (line.startswith('source ')) or (line.startswith('allow-hotplug ')):
               continue # I just dont care about these right now

            split = split_col.split(line)
            split[0] = split[0].replace('-', '_') # Remove the dashes for sqlite col name
            if ( split[0] == 'iface' ):
               temp_iface = split[1]
               interface_settings[temp_iface] = {}
            elif ( not temp_iface ):
               continue # Keep going until I get my first iface
 
            interface_settings[temp_iface][split[0]] = split[1]
            if (len(split) > 3):
               interface_settings[temp_iface][split[2]] = split[3]

    return(interface_settings.get(interface, {}))

########################
# System Wifi Networks #
########################
    # TODO, clean this function up

def system_wifi_networks(interface = None):
    net_list = []

    # Id no interface is passed in, get the first ip one
    interface = system_interfaces('w')[0]

    # If the interface isnt up, brink it up
    if_upd = 0
    if (system_get_interface_state(interface) != 'up'):
        system_set_interface_state(interface, 'up')
        if_upd = 1

    network  = {}
    split_col = re.compile('\s*:|=\s*')
    split_first = re.compile('\s+|\(')
    cmd = 'sudo iw %s scan' % (interface)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line_bytes in p.stdout.readlines():
        line = line_bytes.decode('utf-8')

        if line.startswith('BSS '): # New record found
            if (network):
                net_list.append(clean_network(network))
                network = {}
            split_line = split_first.split(line)
            key = split_line[0].strip()
            network[key] = split_line[1].strip()

        else:
            split_line = split_col.split(line)
            key = split_line[0].strip()
            network[key] = re.sub(r'^"|"$', '', ':'.join( split_line[1:] ).strip() )

    retval = p.wait
    net_list.append(clean_network(network))

    # Take down interface if it was set up
    if (if_upd):
        system_set_interface_state(interface, 'up')

    return net_list

# Basically make the output from "iw XXX scan" look like "iwlist XXX scan" for some things.
def clean_network(network):
    clean_network = {}
    clean_network['ESSID'] = network.get('SSID', '')
    clean_network['Quality'] = network.get('signal', '')
    clean_network['Mode'] = 'Ad-Hoc' if network.get('capability', '').startswith('IBSS ') else 'normal'
    clean_network['Channel'] = re.sub('[^0-9]','', network.get('DS Parameter set', '') )
    return clean_network

#############
# Templates #
#############

def make_interface_config(interfaces, gw_mode='', mesh_interfaces=[]):
    config_file = '/etc/network/interfaces'
    template = env.get_template('interfaces')
    output_from_parsed_template = template.render(ifaces=interfaces, bat_gw_mode=gw_mode, bat_mesh_interfaces=mesh_interfaces)
    with open(config_file, 'w') as f:
        f.write(output_from_parsed_template)
    return(0)

def make_dnsmasq_conf():
    config_file = '/etc/dnsmasq.d/mesh-front-dnsmasq.conf'

    interfaces = system_interfaces()
    dhcp_server = query_interface_settings('bat0')[0]
    dhcp_server['dhcp_start'] = query_setting('dhcp_start')
    dhcp_server['dhcp_end'] = query_setting('dhcp_end')
    dhcp_server['dns1'] = query_setting('dns1')
    dhcp_server['dns2'] = query_setting('dns2')

    template = env.get_template('mesh-front-dnsmasq.conf')
    output_from_parsed_template = template.render(interfaces = interfaces, dhcp_server = dhcp_server)
    with open(config_file, 'w') as f:
        f.write(output_from_parsed_template)
    return(0)

# Clear it with an empty files, so we can keep its permissions
def clear_dnsmasq_conf():
    config_file = '/etc/dnsmasq.d/mesh-front-dnsmasq.conf'
    with open(config_file, 'w') as f:
        pass
    return(0)

def make_sysctl_conf():
    config_file = '/etc/sysctl.d/mesh-front-sysctl.conf'
    with open(config_file, 'w') as f:
        f.write('net.ipv4.ip_forward = 1')
    return(0)

# Clear it with an empty files, so we can keep its permissions
def clear_sysctl_conf():
    config_file = '/etc/sysctl.d/mesh-front-sysctl.conf'
    with open(config_file, 'w') as f:
        pass
    return(0)

#########
# Setup #
#########

def setup_db():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('CREATE TABLE user_settings (username text PRIMARY KEY, password_hash text);')
    c.execute('CREATE TABLE interface_settings (ipv integer, iface text, inet text, address text, netmask text, wireless_essid text, wireless_channel text, UNIQUE(ipv, iface))')
    c.execute('CREATE TABLE server_settings (key text PRIMARY KEY, value text);')
    conn.commit()
    conn.close()
    return(0)

def setup_initial_settings():
    # Set some server configs we have
    upsert_setting('listen_port', '8080')
    upsert_setting('listen_ip', '0.0.0.0')

    # Pull in current interface settings
    for iface in system_interfaces():
        interface_settings = system_interface_settings(iface);
        if not interface_settings:
            interface_settings = {'iface': iface, 'inet': 'dhcp'}
        upsert_interface(interface_settings)

    return(0)

##############
# Misc Utils #
##############

def generate_ipv6(ssid, hostname, index = '1'):
    mesh_block = ''.join(magic_string_to_nums(16, ssid, 4))
    host = magic_string_to_nums(16, hostname, 8)
    host_block1 = ''.join(host[0:3])
    host_block2 = ''.join(host[4:])
    indx_block = ''.join(magic_string_to_nums(16, index, 4))
    return('fd00::%s:%s:%s:%s/80' % (mesh_block, host_block1, host_block2, indx_block))

# Used for generating an IP off of a hostname
def magic_string_to_nums(num_size, base, bit_groups_count, num_format = '{:x}'):
    # Build a long number based on string
    total  = 0
    offset = 1
    for c in base[::-1]:
        total = total + (ord(c) * offset)
        offset = offset * 10

    # Pull off bit_groups_count digits by num_size
    bit_groups = []
    for bg in range(0, bit_groups_count):
        bit_groups.append(num_format.format(int(total % num_size)))
        total = int(total / 10)

    return(bit_groups[::-1])

# Password Salt in file to help passwords in case of sqli
# Generate password salt at first run.
def salt(salt_file):
    salt = ''
    if (os.path.isfile(salt_file)):
        with open(salt_file, 'r') as f:
            salt = f.readline().replace('\n', '')
    else:
        salt = randomword(10)
        with open(salt_file, 'w') as f:
            f.write(salt)
    return(salt)

def hash_password(password, salt=''):
    salted_password = password+salt
    return(hashlib.md5(salted_password.encode()))

# https://stackoverflow.com/questions/2030053/random-strings-in-python#2030081
def randomword(length):
    nonwhitespace = string.digits + string.ascii_letters + string.punctuation
    return ''.join(random.choice(nonwhitespace) for i in range(length))

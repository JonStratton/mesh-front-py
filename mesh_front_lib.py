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
    # Writes all the system files

def refresh_configs():
    mesh_interface = query_setting('mesh_interface')
    uplink_interface = query_setting('uplink_interface')
    mesh_interface = re.sub('[^0-9a-zA-Z]+', '', mesh_interface)
    uplink_interface = re.sub('[^0-9a-zA-Z]+', '', uplink_interface)

    # Make interfaces Files
    make_interface_config()

    # Bridge Interfaces if sharing internet
    if (uplink_interface):
        system_clear_iptables()
        system_clear_iptables(6)
        system_bridge_interfaces('bat0', uplink_interface)
        system_bridge_interfaces('bat0', uplink_interface, 6)
        make_sysctl_conf()
    else: # Clear the bridge otherwise
        system_clear_iptables()
        system_clear_iptables(6)
        clear_sysctl_conf()

    # DHCP Server if serving internet
    if (query_setting('dhcp') and query_setting('dhcp') == 'server'):
        make_dnsmasq_conf()
    else:
        clear_dnsmasq_conf()

    return(0)

############
# Wireless #
############

def get_available_wireless_meshes(wireless_interface):
    wireless_meshes = []
    for network in system_wifi_networks(wireless_interface):
        if (network.get('Mode') == 'Ad-Hoc'):
            wireless_meshes.append(network)
    return(wireless_meshes)

# Basically make the output from "iw XXX scan" look like "iwlist XXX scan" for some things.
def clean_network(network):
    clean_network = {}
    clean_network['ESSID'] = network.get('SSID', '')
    clean_network['Quality'] = network.get('signal', '')
    clean_network['Mode'] = 'Ad-Hoc' if network.get('capability', '').startswith('IBSS ') else 'normal'
    clean_network['Channel'] = re.sub('[^0-9]','', network.get('DS Parameter set', '') )
    return clean_network

def system_wifi_networks(interface):
    net_list = []

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

###########
# Overlay #
###########

def read_json_conf(config_file):
    config_file_lines = []

    with open(config_file) as f:
        for line in f:
            line = re.sub('^\s*\/\/.*$', '', line) # Remove '// Comments\n'
            line = line.strip('\n')
            if line:
                config_file_lines.append(line)

    # Flatten file to remove multi line '/* Comments */' comments
    config_file_flat = ''.join(config_file_lines)
    config_file_flat = re.sub('\s*\/\*.*\*\/\s*', '', config_file_flat)

    return(json.loads(config_file_flat))

def make_json_conf(config_file, config_file_json):
    with open(config_file, 'w') as f:
        f.write(json.dumps(config_file_json, indent=4))
    return(0)

############
# Services #
############

def refresh_services():
    for service in query_services():
        make_avahi_service(service)
    return(0)

def avahi_service_file(service): # Careful now
    port = service.get('port', 0)
    protocol = service.get('protocol', '')
    protocol = re.sub('[^0-9a-zA-Z]+', '', protocol)
    return('/etc/avahi/services/%s_%s.service' % (str(port), protocol))

def avahi_browse():
    remote_services = []
    split_col = re.compile('"*;"*')
    # --ignore-local
    cmd = 'avahi-browse --all --resolve --parsable --terminate'
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line_bytes in p.stdout.readlines():
        line = line_bytes.decode('utf-8').rstrip()
        split = split_col.split(line)
        if split[0] == '=':
           rs = {}
           rs['interface'], rs['spv'], rs['name'], rs['type_s'], rs['domain'], rs['avahi_hostname'], rs['ip'], rs['port'], rs['txt_record'] = split[1:]
           remote_services.append(rs)

    return(remote_services)

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

def upsert_service(service):
    port = service.get('port', None)
    protocol = service.get('protocol', None)
    text = service.get('text', None)

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('INSERT INTO services VALUES (?, ?, ?) ON CONFLICT(port) DO UPDATE SET protocol=excluded.protocol, text=excluded.text;', (port, protocol, text) )
    conn.commit()
    return(0)

def delete_service(port):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('DELETE FROM services WHERE port = ?;', (port, ) )
    conn.commit()
    return(0)

def query_services(port = None):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    if (port):
        c.execute('SELECT port, protocol, text FROM services WHERE port = ?;', (port, ))
    else:
        c.execute('SELECT port, protocol, text FROM services;')
    columns = list(map(lambda x: x[0], c.description))
    columns_length = len(columns)

    services = []
    for row in c.fetchall():
        service = {}
        for col_num in range(0, columns_length):
            service[columns[col_num]] = row[col_num]
        services.append(service)

    return(services)

##########
# System #
##########
    # Mostly our interaction with the system, minus the templating

def system_debug(commands = []):
    commands_and_outputs = []
    for command in commands:
        command_and_output = {'command': command, 'output': []}
        with subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True) as p:
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
def system_bridge_interfaces(mesh_interface, uplink_interface, ipv = 4):
    iptables = 'iptables' if (ipv == 4) else 'ip6tables'
    rules = 'rules.v4' if (ipv == 4) else 'rules.v6'
    cmds = [ 'sudo %s -t nat -A POSTROUTING -o %s -j MASQUERADE' % (iptables, uplink_interface),
            'sudo %s -A FORWARD -i %s -o %s -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT' % (iptables, uplink_interface, mesh_interface),
            'sudo %s -A FORWARD -i %s -o %s -j ACCEPT' % (iptables, mesh_interface, uplink_interface),
            'sudo %s-save > /etc/iptables/%s' % (iptables, rules) ]
    for cmd in cmds:
        subprocess.call(cmd, shell=True, stdout=None, stderr=None)
    return(0)

def system_clear_iptables(ipv = 4):
    iptables = 'iptables' if (ipv == 4) else 'ip6tables'
    rules = 'rules.v4' if (ipv == 4) else 'rules.v6'
    cmds = [ 'sudo %s -P INPUT ACCEPT' % (iptables),
            'sudo %s -P FORWARD ACCEPT' % (iptables),
            'sudo %s -P OUTPUT ACCEPT' % (iptables),
            'sudo %s -t nat -F' % (iptables),
            'sudo %s -t mangle -F' % (iptables),
            'sudo %s -F' % (iptables),
            'sudo %s -X' % (iptables),
            'sudo %s-save > /etc/iptables/%s' % (iptables, rules) ]
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

#############
# Templates #
#############

def make_avahi_service(service):
    config_file = avahi_service_file(service)

    template = env.get_template('avahi_app.service')
    output_from_parsed_template = template.render(service=service)
    with open(config_file, 'w') as f:
        f.write(output_from_parsed_template)
    return(0)

def make_interface_config():
    config_file = '/etc/network/interfaces'

    interfaces = query_interface_settings()
    gw_mode = 'server' if (query_setting('uplink_interface')) else 'client'
    wireless_interface = query_setting('wireless_interface')
    wireless_ssid = query_setting('wireless_ssid')
    wireless_channel = query_setting('wireless_channel')

    template = env.get_template('interfaces')
    output_from_parsed_template = template.render(interfaces=interfaces, gw_mode=gw_mode, wireless_interface=wireless_interface, wireless_ssid=wireless_ssid, wireless_channel=wireless_channel)
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
        f.write("net.ipv4.ip_forward = 1\n")
        f.write("net.ipv6.ip_forward = 1\n")
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
    c.execute('CREATE TABLE interface_settings (ipv integer, iface text, inet text, address text, netmask text, UNIQUE(ipv, iface))')
    c.execute('CREATE TABLE server_settings (key text PRIMARY KEY, value text);')
    c.execute('CREATE TABLE services (port integer PRIMARY KEY AUTOINCREMENT NOT NULL, protocol text, text text);')
    conn.commit()
    conn.close()
    return(0)

def setup_initial_settings():
    # Set some server configs we have
    upsert_setting('listen_port', '8080')
    upsert_setting('listen_ip', '0.0.0.0')
    if os.path.isfile('/etc/yggdrasil.conf') or os.path.isfile('/etc/cjdroute.conf'):
       upsert_setting('has_overlay', '1')

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

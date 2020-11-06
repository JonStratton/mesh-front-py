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
    mesh_type = query_setting('mesh_type')
    mesh_interface = query_setting('mesh_interface')
    uplink_interface = query_setting('uplink')

    mesh_interfaces = [ query_setting('wireless_interface') ]
    gw_mode = 'server' if (uplink_interface) else 'client'

    if (mesh_type == 'olsr'):
        make_olsrd_config()
        make_olsrd_key(query_setting('olsrd_key'))

    if (not mesh_type == 'batman'):
        delete_interface('bat0')

    # Make interfaces Files
    interfaces = query_interface_settings()
    make_interface_config(interfaces, gw_mode, mesh_interfaces)

    # Bridge Interfaces if sharing internet
    if (uplink_interface):
        system_clear_iptables()
        system_bridge_interfaces(mesh_interface, uplink_interface)
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


########
# Mesh #
########

# Try to get guess the network settings based in ESSID, etc.
# TODO, Split this out into a mesh identifier, and a default configuration by mesh type
def mesh_get_defaults(wireless):
    mesh = {}
    system = {}
    ham_mesh = 0

    system['mesh_type'] = 'batman'
    system['hostname'] = system_hostname()

    # Need to make sure people tread lightly here
    # AREDN / BBHN / HSMM
    if (wireless['wireless_essid'].startswith('AREDN-') or wireless['wireless_essid'].startswith('BroadbandHamnet-')):
        ham_mesh = 1
    if (wireless['wireless_channel'] == '-1' or wireless['wireless_channel'] == '-2'):
        ham_mesh = 1

    # Now that we have these things, what do we set the defaults too
    if (ham_mesh and (not system_hostname().startswith(query_setting('callsign')))):
        system['hostname'] = '%s-%s' % (query_setting('callsign'), system_hostname())
        system['mesh_type'] = 'olsr'

    if (system['mesh_type'] == 'olsr'):
        mesh['inet'] = 'static'
        mesh['address'] = '10.%s' % '.'.join(get_bg_by_string(system_hostname(), 3))
        mesh['netmask'] = '255.0.0.0'

    if (system['mesh_type'] == 'batman'):
        wireless['wireless_address'] = ''

    return system, mesh, wireless

def olsr_get(item = None):
    # wget over python request just so you dont have to import??! Are you insane?!!
    data = []
    cmd = 'wget -qO- http://127.0.0.1:9090/%s' % (item)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    cmd_return = ''.join([line.decode('utf-8') for line in p.stdout.readlines()])
    if (cmd_return):
        data = json.loads(cmd_return)
    return(data)

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
    iface   = interface.get('iface', '')
    netmask = interface.get('netmask', '')
    address = interface.get('address', '')
    inet    = interface.get('inet', '')
    wireless_address = interface.get('wireless_address', '')
    wireless_mode    = interface.get('wireless_mode', '')
    wireless_channel = interface.get('wireless_channel', '')
    wireless_essid   = interface.get('wireless_essid', '')

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('INSERT INTO interface_settings (iface, inet, address, netmask, wireless_address, wireless_mode, wireless_essid, wireless_channel) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(iface) DO UPDATE SET inet=excluded.inet, address=excluded.address, netmask=excluded.netmask, wireless_address=excluded.wireless_address, wireless_mode=excluded.wireless_mode, wireless_essid=excluded.wireless_essid, wireless_channel=excluded.wireless_channel;', (iface, inet, address, netmask, wireless_address, wireless_mode, wireless_essid, wireless_channel))
    conn.commit()
    return(0)

def delete_interface(iface):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('DELETE FROM interface_settings WHERE iface = ?;', (iface, ) )
    conn.commit()
    return(0)

def query_interface_settings(interface = None):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    if (interface):
        c.execute('SELECT iface, inet, address, netmask, wireless_address, wireless_mode, wireless_essid, wireless_channel FROM interface_settings WHERE iface = ?;', (interface, ))
    else:
        c.execute('SELECT iface, inet, address, netmask, wireless_address, wireless_mode, wireless_essid, wireless_channel FROM interface_settings;')
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

def upsert_service(service):
    service_id = service.get('service_id', None)
    name = service.get('name', None)
    host = service.get('host', None)
    port = service.get('port', None)
    protocol = service.get('protocol', None)
    local_port = service.get('local_port', None)
    path = service.get('path', None)

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('INSERT INTO services VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(service_id) DO UPDATE SET name=excluded.name, host=excluded.host, port=excluded.port, protocol=excluded.protocol, local_port=excluded.local_port, path=excluded.path;', (service_id, name, host, port, protocol, local_port, path) )
    conn.commit()
    return(0)

def delete_service(service_id):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('DELETE FROM services WHERE service_id = ?;', (service_id, ) )
    conn.commit()
    return(0)

def query_services(service_id = None):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    if (service_id):
        c.execute('SELECT service_id, name, host, port, protocol, local_port, path FROM services WHERE service_id = ?;', (service_id, ))
    else:
        c.execute('SELECT service_id, name, host, port, protocol, local_port, path FROM services;')
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
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line_bytes in p.stdout.readlines():
            command_and_output['output'].append( line_bytes.decode('utf-8').rstrip() )
        commands_and_outputs.append(command_and_output)
    return(commands_and_outputs)

def system_hostname(new_hostname = None):
    if (new_hostname):
        new_hostname = re.sub('[^0-9a-zA-Z\-]+', '', new_hostname)
        cmd = 'sudo hostname %s' % (new_hostname)
        code = subprocess.call(cmd, shell=True, stdout=None, stderr=None)
        make_hostname_and_hosts(new_hostname)
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

def system_mesh_types():
    mesh_types = []
    if os.path.exists('/usr/sbin/batctl'):
        mesh_types.append('batman')
    if os.path.exists('/opt/cjdns/cjdroute'):
        mesh_types.append('cjdns')
    if os.path.exists('/usr/local/sbin/olsrd'):
        mesh_types.append('olsr')
    return(mesh_types)

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
   clean_network['Address'] = network.get('BSS', '')
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

def make_olsrd_config():
    config_file = '/etc/olsrd/olsrd.conf'

    interface = query_setting('mesh_interface')
    ifes_settings = query_interface_settings(interface)
    if ifes_settings:
        if_settings = ifes_settings[0]
        address = if_settings['address']
        olsrd_key = query_setting('olsrd_key')

        template = env.get_template('olsrd.conf')
        output_from_parsed_template = template.render(interface=interface, address=address, hostname=system_hostname(),
                olsrd_key=olsrd_key, share_iface=query_setting('uplink'), services=query_services())
        with open(config_file, 'w') as f:
            f.write(output_from_parsed_template)
    return(0)

def make_olsrd_key(olsrd_key):
    config_file = '/etc/olsrd/olsrd.key'
    template = env.get_template('olsrd.key')
    output_from_parsed_template = template.render(olsrd_key=olsrd_key)
    with open(config_file, 'w') as f:
        f.write(output_from_parsed_template)
    return(0)

def make_hostname_and_hosts(hostname):
    config_file = '/etc/hostname'
    template = env.get_template('hostname')
    output_from_parsed_template = template.render(hostname=hostname)
    with open(config_file, 'w') as f:
        f.write(output_from_parsed_template)
    config_file = '/etc/hosts'
    template = env.get_template('hosts')
    output_from_parsed_template = template.render(hostname=hostname)
    with open(config_file, 'w') as f:
        f.write(output_from_parsed_template)
    return(0)

def make_dnsmasq_conf():
    config_file = '/etc/dnsmasq.d/mesh-front-dnsmasq.conf'

    interfaces = system_interfaces()
    dhcp_interface = query_setting('dhcp_server_interface')
    dhcp_server = query_interface_settings(dhcp_interface)[0]
    dhcp_server['ip_start'] = query_setting('dhcp_server_ip_start')
    dhcp_server['ip_end'] = query_setting('dhcp_server_ip_end')
    dhcp_server['dns1'] = query_setting('dns1')
    dhcp_server['dns2'] = query_setting('dns2')

    template = env.get_template('mesh-front-dnsmasq.conf')
    output_from_parsed_template = template.render(interfaces = interfaces, dhcp_interface = dhcp_interface, dhcp_server = dhcp_server, hostname = system_hostname())
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
    c.execute('CREATE TABLE interface_settings (iface text PRIMARY KEY, inet text, address text, netmask text, wireless_address text, wireless_mode text, wireless_essid text, wireless_channel text)')
    c.execute('CREATE TABLE server_settings (key text PRIMARY KEY, value text);')
    c.execute('CREATE TABLE services (service_id integer PRIMARY KEY AUTOINCREMENT NOT NULL, name text, host text, port integer, protocol text, local_port integer, path text);')
    conn.commit()
    conn.close()
    return(0)

def setup_initial_settings():
    # Set some server configs we have
    upsert_setting('hostname', system_hostname())
    upsert_setting('callsign', 'NOCALL')
    upsert_setting('listen_port', '8080')
    upsert_setting('listen_ip', '0.0.0.0')

    # Pull in current interface settings
    for iface in system_interfaces():
        interface_settings = system_interface_settings(iface);
        if not interface_settings:
            interface_settings = {'iface': iface, 'inet': 'dhcp'}
        upsert_interface(interface_settings)

    # Meshes and modules
    upsert_setting('mesh_batman_available', '1' if (os.path.isfile('/usr/sbin/batctl')) else None)
    upsert_setting('mesh_olsr_available', '1' if (os.path.isfile('/usr/sbin/olsrd')) else None)
    upsert_setting('cjdns_available', '1' if (os.path.isfile('/opt/cjdns/cjdroute')) else None)

    return(0)

##############
# Misc Utils #
##############

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

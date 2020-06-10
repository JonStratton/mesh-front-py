#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sqlite3, os, re, subprocess, socket, hashlib, random, string, json
from jinja2 import Environment, FileSystemLoader

# Defaults
db_file  = 'db.sqlite3'
env = Environment(loader=FileSystemLoader('templates'))

########
# Mesh #
########

# Try to get guess the network settings based in ESSID, etc.
# TODO, Split this out into a mesh identifier, and a default configuration by mesh type
def mesh_get_defaults(wifi_network):
    mesh = {}
    for key in wifi_network:
        mesh[key] = wifi_network.get(key)
    mesh['inet'] = 'static'
    mesh['address'] = '10.%s' % '.'.join(get_bg_by_string(system_hostname(), 3))
    mesh['netmask'] = '255.0.0.0'

    # LibreMesh (Adhoc)
    if (mesh['wireless_essid'] == 'LibreMesh.org' or mesh['wireless_address'] == 'CA:FE:00:C0:FF:EE'):
        mesh['type'] = 'batman'

    # freifunk.net
    # https://github.com/rubo77/batman-connect/blob/master/batman-connect
    if (mesh['wireless_address'] == '02:C0:FF:EE:BA:BE'):
        mesh['type'] = 'batman'

    # Need to make sure people tread lightly here
    # AREDN / BBHN / HSMM
    if (mesh['wireless_essid'].startswith('AREDN-') or mesh['wireless_essid'].startswith('BroadbandHamnet-')):
        mesh['ham_mesh'] = 1
        mesh['type'] = 'olsr'
    if (mesh['wireless_channel'] == '-1' or mesh['wireless_channel'] == '-2'):
        mesh['ham_mesh'] = 1

    return(mesh)

def mesh_get(item = None):
    # wget over python request just so you dont have to import??! Are you insane?!!
    data = []
    cmd = 'wget -qO- http://127.0.0.1:9090/%s' % (item)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    cmd_return = ''.join(p.stdout.readlines())
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

def system_hostname(new_hostname = None):
    if (new_hostname):
        cmd = 'sudo hostname %s' % (new_hostname)
        code = subprocess.call(cmd, shell=True, stdout=None, stderr=None)
        make_hostname_and_hosts(new_hostname)
        return(socket.gethostname())
    else:
        return(socket.gethostname())

def system_reboot():
    cmd = 'sudo reboot'
    code = subprocess.call(cmd, shell=True, stdout=None, stderr=None)
    return(code)

def system_set_interface_state(interface, state):
    cmd = 'sudo ip link set %s %s' % (interface, state)
    code = subprocess.call(cmd, shell=True, stdout=None, stderr=None)
    return(code)

def system_get_interface_state(interface):
    if_state = ''
    with open('/sys/class/net/%s/operstate' % (interface), 'r') as f:
        if_state = f.readline().replace('\n', '')
    return if_state

# List the connected network interfaces.
def system_interfaces(if_type = None):
    if_list = []
    for iface in os.listdir('/sys/class/net'):
        if (if_type) and (not iface.startswith(if_type)):
            continue
        if_list.append(iface)
    return(if_list)

# Bridge Interfaces if sharing.
def system_bridge_interfaces(w_iface, e_iface):
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

def system_interface_settings():
    interfaces = []
    interface  = {}
    split_col = re.compile('\s+')
    with open('/etc/network/interfaces', 'r') as f:
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

    # For now, just dont load lo and default
    interfaces_custom = []
    for interface in interfaces:
        iface = interface.get('iface')
        if (iface == 'lo' or iface == 'default'):
            continue
        interfaces_custom.append(interface)

    return(interfaces_custom)

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
    cmd = 'sudo iwlist %s scan' % (interface)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
        if (line.startswith(interface)):
            continue
        split_line = split_col.split( line.decode('utf-8') )
        key = split_line[0].strip()
        value = re.sub(r'^"|"$', '', ':'.join( split_line[1:] ).strip() )
        if key.endswith('Address'): # New record found
            key = 'Address'
            if (network):
                net_list.append(network)
                network = {}
        network[key] = value
    retval = p.wait
    net_list.append(network)

    # Take down interface if it was set up
    if (if_upd):
        system_set_interface_state(interface, 'up')

    return net_list

#############
# Templates #
#############

def make_interface_config(interfaces):
    config_file = '/etc/network/interfaces'
    template = env.get_template('interfaces')
    output_from_parsed_template = template.render(ifaces=interfaces)
    with open(config_file, 'w') as f:
        f.write(output_from_parsed_template)
    return(0)

def make_olsrd_config(interface, address, hostname, share_iface, olsrd_key):
    config_file = '/etc/olsrd/olsrd.conf'
    template = env.get_template('olsrd.conf')
    output_from_parsed_template = template.render(interface=interface, address=address, hostname=hostname,
            olsrd_key=olsrd_key, share_iface=share_iface)
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


#########
# Setup #
#########

def setup_db():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('CREATE TABLE user_settings (username text PRIMARY KEY, password_hash text);')
    c.execute('CREATE TABLE interface_settings (iface text PRIMARY KEY, inet text, address text, netmask text, wireless_address text, wireless_mode text, wireless_essid text, wireless_channel text)')
    c.execute('CREATE TABLE server_settings (key text PRIMARY KEY, value text);')
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
    for interface in system_interface_settings():
        upsert_interface(interface)

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
    nonwhitespace = string.digits + string.letters + string.punctuation
    return ''.join(random.choice(nonwhitespace) for i in range(length))

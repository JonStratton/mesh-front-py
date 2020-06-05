#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sqlite3
from jinja2 import Environment, FileSystemLoader
import mesh_front_util as mfu

# Defaults
db_file  = 'db.sqlite3'
env = Environment(loader=FileSystemLoader('templates'))

######
# DB #
######

def get_setting(setting):
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('SELECT value FROM server_settings WHERE key=?;', (setting,))
    return(c.fetchone()[0])

def set_setting(setting, value):
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('INSERT INTO server_settings (key, value) VALUES (?, ?);', (setting, value))
    conn.commit()
    return(0)

def set_interface(interface):
    iface   = interface.get('iface', '')
    netmask = interface.get('netmask', '')
    address = interface.get('address', '')
    inet    = interface.get('inet', '')
    wireless_mode    = interface.get('wireless_mode', '')
    wireless_channel = interface.get('wireless_channel', '')
    wireless_essid   = interface.get('wireless_essid', '')

    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('INSERT INTO interface_settings (iface, inet, address, netmask, wireless_mode, wireless_essid, wireless_channel) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(iface) DO UPDATE SET inet=excluded.inet, address=excluded.address, netmask=excluded.netmask, wireless_mode=excluded.wireless_mode, wireless_essid=excluded.wireless_essid, wireless_channel=excluded.wireless_channel;', (iface, inet, address, netmask, wireless_mode, wireless_essid, wireless_channel))
    conn.commit()
    return(0)

def get_interface_configs(interface = None):
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    if (interface):
        c.execute('SELECT iface, inet, address, netmask, wireless_mode, wireless_essid, wireless_channel FROM interface_settings WHERE iface = ?;', (interface, ))
    else:
        c.execute('SELECT iface, inet, address, netmask, wireless_mode, wireless_essid, wireless_channel FROM interface_settings;')
    columns = list(map(lambda x: x[0], c.description))
    columns_length = len(columns)
    
    records = []
    for row in c.fetchall():
        record = {}
        for col_num in range(0, columns_length):
            record[columns[col_num]] = row[col_num]
        records.append(record)

    return(records)

def create_user(username, password_hash):
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('INSERT INTO user_settings VALUES (?, ?);', (username, password_hash) )
    conn.commit()
    return(0)

def user_auth(user, pass_hash):
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('SELECT count(*) FROM user_settings WHERE username=? AND password_hash=?;', (user, pass_hash))
    return(c.fetchone()[0])

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

#########
# Setup #
#########

def setup_db():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('CREATE TABLE user_settings (username text PRIMARY KEY, password_hash text);')
    c.execute('CREATE TABLE interface_settings (iface text PRIMARY KEY, inet text, address text, netmask text, wireless_mode text, wireless_essid text, wireless_channel text)')
    c.execute('CREATE TABLE server_settings (key text PRIMARY KEY, value text);')
    conn.commit()
    conn.close()
    return(0)

def setup_initial_settings(password):
    # Set some server configs we have
    mfdb.set_setting('hostname', mfu.get_hostname())
    mfdb.set_setting('listen_port', '8080')
    mfdb.set_setting('listen_ip', '0.0.0.0')

    # Pull in current interface settings
    for interface in mfu.get_interface_settings():
        mfdb.set_interface(interface)

    # Create admin user
    password_hash = mfu.hash_password(password).hexdigest()
    mfdb.create_user('admin', password_hash)
    return(0)

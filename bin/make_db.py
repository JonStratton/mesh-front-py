#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sys, os, getopt
run_dir = os.path.dirname(os.path.realpath(__file__))
lib_loc = os.path.realpath('%s/../lib/' % run_dir)
sys.path.insert(1, lib_loc )
import mesh_front_util as mfu
import mesh_front_db as mfdb
import sqlite3

# Defaults
password = 'changeme'
refresh  = 0

# Command line params
myopts, args = getopt.getopt(sys.argv[1:],'p:r')
for o, a in myopts:
    if (o == '-p'):
        password = a
    elif (o == '-r'):
        refresh = 1

password_hash = mfu.hash_password(password).hexdigest()
conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Drop tables if refresh
if (refresh):
    c.execute('DROP TABLE user_settings;')
    c.execute('DROP TABLE interface_settings;')
    c.execute('DROP TABLE server_settings;')
# Admin passwd table
c.execute('CREATE TABLE user_settings (username text, password_hash text);')
# Settings for each interface
c.execute('CREATE TABLE interface_settings (interface text, ip text, netmask text, gateway text, dns1 text, dns2 text, type text, enabled integer, dhcp_client integer, dhcp_server integer)')
# Generic server settings: hostname, wifi_channel, wifi_ssid, dns1, dns2, share_iternet
c.execute('CREATE TABLE server_settings (key text, value text);')
conn.commit()
conn.close()

# Set some server configs we have
mfdb.set_setting('hostname', mfu.get_hostname())
mfdb.set_setting('listen_port', '8080')
mfdb.set_setting('listen_ip', '0.0.0.0')

# Create admin user
password_hash = mfu.hash_password(password).hexdigest()
mfdb.create_user('admin', password_hash)

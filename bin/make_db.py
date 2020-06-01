#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sys, os, getopt, sqlite3
run_dir = os.path.dirname(os.path.realpath(__file__))
lib_loc = os.path.realpath('%s/../lib/' % run_dir)
sys.path.insert(1, lib_loc )
import mesh_front_util as mfu
import mesh_front_db as mfdb

# Defaults
db_file  = 'db.sqlite3'
password = 'changeme'

# Command line params
myopts, args = getopt.getopt(sys.argv[1:],'p:r')
for o, a in myopts:
    if (o == '-p'):
        password = a

# Backup old DB if it exists
if (os.path.isfile(db_file)):
    os.rename(db_file, '%s.backup' % db_file)

password_hash = mfu.hash_password(password).hexdigest()
conn = sqlite3.connect(db_file)
c = conn.cursor()

# Admin passwd table
c.execute('CREATE TABLE user_settings (username text, password_hash text);')
# Settings for each interface
c.execute('CREATE TABLE interface_settings (iface text, inet text, address text, netmask text, wireless_mode text, wireless_essid text, wireless_channel text)')
c.execute('CREATE TABLE server_settings (key text, value text);')
conn.commit()
conn.close()

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

import sys, os

run_dir = os.path.dirname(os.path.realpath(__file__))
lib_loc = os.path.realpath('%s/../lib/' % run_dir)
sys.path.insert(1, lib_loc )
import mesh_front_util as mfu
import sqlite3

password = 'changeme'
password_hash = mfu.hash_password(password).hexdigest()
#print(password_hash)

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Drop tables if refresh
c.execute('DROP TABLE user_settings;')
c.execute('DROP TABLE interface_settings;')
c.execute('DROP TABLE mesh_settings;')
c.execute('DROP TABLE server_settings;')
c.execute('DROP TABLE service_settings;')

# Admin passwd table
c.execute('CREATE TABLE user_settings (username text, password_hash text);')
c.execute('INSERT INTO user_settings VALUES (\'admin\', ?);', (password_hash,) )
#c.execute('UPDATE user_settings SET password_hash = ? WHERE username = \'admin\';', (password_hash,) )

# Settings for each interface
c.execute('CREATE TABLE interface_settings (interface text, ip text, netmask text, gateway text, dns1 text, dns2 text, type text, enabled integer, dhcp_client integer, dhcp_server integer)')
#c.execute('INSERT INTO interface_settings VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (,) )

# Settings for the mesh network: interface, key
c.execute('CREATE TABLE mesh_settings (key text, value text);')

# Generic server settings: hostname, wifi_channel, wifi_ssid, dns1, dns2, share_iternet
c.execute('CREATE TABLE server_settings (key text, value text);')
c.execute('INSERT INTO server_settings VALUES (\'hostname\', ?);', (mfu.get_hostname(),) )

#c.execute('SELECT * FROM users')
#print(c.fetchone())
conn.commit()
conn.close()

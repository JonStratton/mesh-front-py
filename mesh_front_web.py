#!/usr/bin/env python3
__author__ = 'Jon Stratton'
import sys, os, getopt
from flask import Flask, render_template, request, session, escape, send_from_directory
import mesh_front_lib as mfl

# Defaults
root     = os.path.dirname(os.path.realpath(__file__))
Salt     = mfl.salt(os.path.join(root, 'salt.txt'))
FirstRun = not os.path.isfile(os.path.join(root, 'db.sqlite3'))
app      = Flask(__name__)

# Reset password from command line
NewPassword = mfl.randomword(10) if (FirstRun) else ''
myopts, args = getopt.getopt(sys.argv[1:], 'p:')
for o, a in myopts:
    if (o == '-p'):
        NewPassword = a

# Mfl functions templates can call directly
app.jinja_env.globals.update(system_hostname=mfl.system_hostname)
app.jinja_env.globals.update(query_setting=mfl.query_setting)

def escape_request(request): # Cant help but think Im redoing something built in here...
    escaped_request = {}
    for key in request:
        escaped_request[escape(key)] = escape(request.get(key))
    return escaped_request

@app.route('/static/mesh-front-py.tgz')
def static_meshfrontpy():
    return send_from_directory('', 'static/mesh-front-py.tgz')

@app.route('/static/jquery.min.js')
def static_jquery():
    return send_from_directory('', 'static/jquery.min.js')

@app.route('/debug')
def debug():
    if not session.get('logged_in'):
       return render_template('login.html')
    else:
       outputs = mfl.system_debug_batctl()
       return render_template('debug.html', outputs = outputs)

@app.route('/ifconfig', methods=['GET', 'POST'])
def if_config():
    if not session.get('logged_in'):
       return render_template('login.html')
    else:
        # If an Interface is passed in, update it
        escaped_request = escape_request(request.values)
        if (escaped_request.get('save')):
            mfl.upsert_interface(escaped_request)
            mfl.refresh_configs()
            mfl.upsert_setting('should_reboot', 'true')
        # If we have an interface, only get it
        interface = None
        if (escaped_request.get('interface')):
            interface = escaped_request.get('interface')
        if_configs = mfl.query_interface_settings(interface)
        return render_template('ifconfig.html', ifaces=if_configs)

@app.route('/scan')
def scan():
    if not session.get('logged_in'):
       return render_template('login.html')
    else:
        networks = mfl.system_wifi_networks()
        return render_template('scan.html', networks=networks)

@app.route('/mesh', methods=['GET', 'POST'])
def mesh():
    if not session.get('logged_in'):
       return render_template('login.html')
    else:
        escaped_request = escape_request(request.values)
        if (request.values.get('save')): # Save settings and generate system files
            mfl.upsert_setting('mesh_type', escaped_request.get('system_mesh_type'))
            mfl.upsert_setting('mesh_interface', escaped_request.get('mesh_interface'))
            mfl.upsert_setting('wireless_interface', escaped_request.get('wireless_interface'))
            mfl.upsert_setting('olsrd_key', escaped_request.get('system_olsrd_key'))
            mfl.upsert_setting('uplink', escaped_request.get('system_uplink'))
            mfl.system_hostname(escaped_request.get('system_hostname'))

            wireless_iface = { 'iface': escaped_request.get('wireless_interface'),
                    'inet': escaped_request.get('wireless_inet'),
                    'wireless_address': escaped_request.get('wireless_address'),
                    'wireless_mode': escaped_request.get('wireless_mode'),
                    'wireless_channel': escaped_request.get('wireless_channel'),
                    'wireless_essid': escaped_request.get('wireless_essid')}
            if (escaped_request.get('system_mesh_type') == 'batman'):
                mesh_iface = { 'iface': escaped_request.get('mesh_interface'),
                        'inet': escaped_request.get('mesh_inet'),
                        'address': escaped_request.get('mesh_address'),
                        'netmask': escaped_request.get('mesh_netmask')}
                mfl.upsert_interface(mesh_iface)
            elif (escaped_request.get('system_mesh_type') == 'olsr'):
                wireless_iface['address'] = escaped_request.get('mesh_address')
                wireless_iface['netmask'] = escaped_request.get('mesh_netmask')

            mfl.upsert_interface(wireless_iface)
            mfl.refresh_configs()
            mfl.upsert_setting('should_reboot', 'true')

        system = {}
        mesh = {}
        wireless = {}
        if (request.values.get('copy')): # Just populate the form from the scan item. Still needs to be saved
            system, mesh, wireless = mfl.mesh_get_defaults(escaped_request)
        else:
            if (mfl.query_setting('mesh_interface')):
                mesh = mfl.query_interface_settings(mfl.query_setting('mesh_interface'))[0]
            if (mfl.query_setting('wireless_interface')):
                wireless = mfl.query_interface_settings(mfl.query_setting('wireless_interface'))[0]
            system['hostname'] = mfl.system_hostname()
            system['mesh_type'] = mfl.query_setting('mesh_type')

        system['wireless_interfaces'] = mfl.system_interfaces('w')
        system['interfaces'] = mfl.system_interfaces()
        system['uplink'] = mfl.query_setting('uplink')
        system['olsrd_key'] = mfl.query_setting('olsrd_key')

        return render_template('mesh.html', system = system, wireless = wireless, mesh = mesh)

# List
@app.route('/status')
def status():
    olsr_neighbors = {}
    if (mfl.query_setting('mesh_type') == 'olsr'):
        olsr_neighbors = mfl.olsr_get('links')
    return render_template('status.html', olsr_neighbors = olsr_neighbors)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('logged_in'):
       return render_template('login.html')
    else:
        escaped_request = escape_request(request.values)
        if (request.values.get('save')):
            mfl.system_hostname(escaped_request.get('hostname'))
            mfl.upsert_setting('callsign', escaped_request.get('callsign'))
            mfl.upsert_setting('listen_port', escaped_request.get('listen_port'))
            mfl.upsert_setting('listen_ip', escaped_request.get('listen_ip'))
            mfl.upsert_setting('dns1', escaped_request.get('dns1'))
            mfl.upsert_setting('dns2', escaped_request.get('dns2'))
            if (request.values.get('password')): # Get the raw password!
                mfl.upsert_user('admin', mfl.hash_password(request.values.get('password'), Salt).hexdigest())
            mfl.refresh_configs()
            mfl.upsert_setting('should_reboot', 'true')
        settings = {}
        settings['hostname'] = mfl.system_hostname()
        settings['callsign'] = mfl.query_setting('callsign')
        settings['listen_port'] = mfl.query_setting('listen_port')
        settings['listen_ip'] = mfl.query_setting('listen_ip')
        settings['dns1'] = mfl.query_setting('dns1')
        settings['dns2'] = mfl.query_setting('dns2')
        return render_template('settings.html', settings = settings)

@app.route('/olsr_services', methods=['GET', 'POST'])
@app.route('/olsr_services/<action>', methods=['GET', 'POST'])
@app.route('/olsr_services/<action>/<service_id>', methods=['GET', 'POST'])
def services(action = 'display', service_id = None):
    if not session.get('logged_in'):
       return render_template('login.html')
    else:
        escaped_request = escape_request(request.values)
        if (escaped_request.get('save')):
            mfl.upsert_service(escaped_request)
            mfl.refresh_configs()
            mfl.upsert_setting('should_reboot', 'true')
        if (action == 'add'):
            return render_template('olsr_servicesadd.html')
        elif (action == 'delete' and service_id):
            mfl.delete_service(service_id)
            mfl.refresh_configs()
            mfl.upsert_setting('should_reboot', 'true')
        services = mfl.query_services()
        return render_template('olsr_services.html', services = services, hostname = mfl.system_hostname())

@app.route('/dhcp_server', methods=['GET', 'POST'])
def dhcp_server():
    if not session.get('logged_in'):
       return render_template('login.html')
    else:
        escaped_request = escape_request(request.values)
        if (escaped_request.get('save')):
            mfl.upsert_setting('dhcp_server_interface', escaped_request.get('dhcp_server_interface'))
            mfl.upsert_setting('dhcp_server_ip_start', escaped_request.get('ip_start'))
            mfl.upsert_setting('dhcp_server_ip_end', escaped_request.get('ip_end'))

            if (escaped_request.get('dhcp_server_interface')):
                dhcp_settings = escaped_request
                dhcp_settings['iface'] = dhcp_settings['dhcp_server_interface']
                mfl.upsert_interface(dhcp_settings)

            mfl.refresh_configs()
            mfl.upsert_setting('should_reboot', 'true')

        # Default to class B internal
        dhcp_server = {}
        dhcp_server['inet'] = 'static'
        dhcp_server['address'] = '172.31.254.1'
        dhcp_server['netmask'] = '255.255.255.0'

        # If we are called with an interface, try to get the settings we have
        if (mfl.query_setting('dhcp_server_interface')):
            dhcp_server = mfl.query_interface_settings(mfl.query_setting('dhcp_server_interface'))[0]
            dhcp_server['dhcp_server_interface'] = mfl.query_setting('dhcp_server_interface')
            dhcp_server['ip_start'] = mfl.query_setting('dhcp_server_ip_start')
            dhcp_server['ip_end'] = mfl.query_setting('dhcp_server_ip_end')

        # Else if we have a mesh interface, we are probably going to want to use that
        elif (mfl.query_setting('mesh_interface')):
            dhcp_server = mfl.query_interface_settings(mfl.query_setting('mesh_interface'))[0]
            dhcp_server['dhcp_server_interface'] = mfl.query_setting('mesh_interface')

        # Have an ip, but not start (and end?).
        if dhcp_server['address'] and (not mfl.query_setting('dhcp_server_ip_start')):
            address_base = '.'.join( dhcp_server['address'].split('.')[:3] )
            dhcp_server['ip_start'] = "%s.%d" % (address_base, 100)
            dhcp_server['ip_end'] = "%s.%d" % (address_base, 200)

        # mesh iface might not exist yet, so base ifaces off of config'd ifaces
        interfaces = mfl.query_interfaces_configured()
        return render_template('dhcp_server.html', interfaces = interfaces, dhcp_server = dhcp_server )

# Just reboot.
@app.route('/reboot')
def reboot():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        mfl.upsert_setting('should_reboot', '')
        mfl.system_reboot()
        return status()

@app.route('/login', methods=['GET', 'POST'])
def do_admin_login():
    escaped_request = escape_request(request.values)
    if (escaped_request.get('username') and escaped_request.get('password')):
        password_hash = mfl.hash_password(request.form['password'], Salt).hexdigest()
        if (mfl.user_auth(request.form['username'], password_hash)):
            session['logged_in'] = True
            return status()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session['logged_in'] = False
    return status()

@app.route('/')
def home():
    return status()

def first_run():
    mfl.setup_db()
    mfl.setup_initial_settings()
    return()

if (__name__ == '__main__'):
    app.secret_key = os.urandom(12)
    if (FirstRun):
        first_run()
    if (NewPassword):
        password_hash = mfl.hash_password(NewPassword, Salt).hexdigest()
        mfl.upsert_user('admin', password_hash)
        print("New Password Set. Log in with user 'admin' and password '%s'.\n" % NewPassword)
    port = mfl.query_setting('listen_port')
    ip   = mfl.query_setting('listen_ip')
    app.run(host=ip, port=port, debug=False)

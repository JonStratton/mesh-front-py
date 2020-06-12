#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sys, os, getopt
from flask import Flask, render_template, request, session, escape
import mesh_front_lib as mfl

Salt     = mfl.salt('salt.txt')
FirstRun = not os.path.isfile('db.sqlite3')
app      = Flask(__name__)

# Reset password from command line
NewPassword = mfl.randomword(10) if (FirstRun) else ''
myopts, args = getopt.getopt(sys.argv[1:], 'p:')
for o, a in myopts:
    if (o == '-p'):
        NewPassword = a

# Mfl functions templates can call directly
app.jinja_env.globals.update(system_hostname=mfl.system_hostname)

def escape_request(request): # Cant help but think Im redoing something built in here...
    escaped_request = {}
    for key in request:
        escaped_request[escape(key)] = escape(request.get(key))
    return escaped_request

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
            mfl.upsert_setting('mesh_interface', escaped_request.get('mesh_interface'))
            mfl.upsert_setting('olsrd_key', escaped_request.get('olsrd_key'))
            mfl.upsert_setting('gateway_interface', escaped_request.get('gateway_interface'))
            mfl.upsert_setting('dhcp_server_interface', escaped_request.get('dhcp_server_interface'))
            mfl.system_hostname(escaped_request.get('hostname'))

            mesh_interface_settings = escaped_request
            mesh_interface_settings['iface'] = mesh_interface_settings['mesh_interface'] 
            mfl.upsert_interface(mesh_interface_settings)

            mfl.refresh_configs()
        mesh = {}
        if (request.values.get('copy')): # Just populate the form from the scan item. Still needs to be saved
            mesh = mfl.mesh_get_defaults(escaped_request)
        elif (mfl.query_setting('mesh_interface')):
            mesh = mfl.query_interface_settings(mfl.query_setting('mesh_interface'))[0]
        mesh['wireless_interfaces'] = mfl.system_interfaces('w')
        mesh['interfaces'] = mfl.system_interfaces()
        mesh['gateway_interface'] = mfl.query_setting('gateway_interface')
        mesh['dhcp_server_interface'] = mfl.query_setting('dhcp_server_interface')
        wireless_interfaces = mfl.system_interfaces('w')
        interfaces = mfl.system_interfaces()
        return render_template('mesh.html', wireless_interfaces = wireless_interfaces, interfaces = interfaces, mesh = mesh)

# List
@app.route('/status')
def status():
    neighbors = mfl.mesh_get('links')
    return render_template('status.html', neighbors = neighbors)

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
            if (request.values.get('password')): # Get the raw password!
                mfl.upsert_user('admin', mfl.hash_password(request.values.get('password'), Salt).hexdigest())
            mfl.refresh_configs()
        settings = {}
        settings['hostname'] = mfl.system_hostname()
        settings['callsign'] = mfl.query_setting('callsign')
        settings['listen_port'] = mfl.query_setting('listen_port')
        settings['listen_ip'] = mfl.query_setting('listen_ip')
        return render_template('settings.html', settings = settings)

@app.route('/services', methods=['GET', 'POST'])
@app.route('/services/<action>', methods=['GET', 'POST'])
@app.route('/services/<action>/<service_id>', methods=['GET', 'POST'])
def services(action = 'display', service_id = None):
    if not session.get('logged_in'):
       return render_template('login.html')
    else:
        # TODO: page = request.args.get('page', default = 1, type = int)
        escaped_request = escape_request(request.values)
        if (escaped_request.get('save')):
            mfl.upsert_service(escaped_request)
            mfl.refresh_configs()
        if (action == 'add'):
            return render_template('servicesadd.html')
        elif (action == 'delete' and service_id):
            mfl.delete_service(service_id)
            mfl.refresh_configs()
        services = mfl.query_services()
        return render_template('services.html', services = services, hostname = mfl.system_hostname())

@app.route('/dhcp_server', methods=['GET', 'POST'])
def dhcp_server():
    if not session.get('logged_in'):
       return render_template('login.html')
    else:
        escaped_request = escape_request(request.values)
        if (escaped_request.get('save') and escaped_request.get('dhcp_server_interface')):
            mfl.upsert_setting('dhcp_server_interface', escaped_request.get('dhcp_server_interface'))
            mfl.upsert_setting('dhcp_server_ip_start', escaped_request.get('ip_start'))
            mfl.upsert_setting('dhcp_server_ip_end', escaped_request.get('ip_end'))

            dhcp_settings = escaped_request
            dhcp_settings['iface'] = dhcp_settings['dhcp_server_interface']
            mfl.upsert_interface(dhcp_settings)
            mfl.refresh_configs()
        dhcp_server = {}
        # If we are called with an interface, try to get the settings we have
        if (mfl.query_setting('dhcp_server_interface')):
            dhcp_server = mfl.query_interface_settings(mfl.query_setting('dhcp_server_interface'))[0]
            dhcp_server['dhcp_server_interface'] = mfl.query_setting('dhcp_server_interface')
        # If we dont have these after fetching the IF settings, its time to default them to the end of class B Internal
        dhcp_server['inet'] = 'static'
        dhcp_server['address'] = '172.31.254.1'
        dhcp_server['netmask'] = '255.255.255.0'
        dhcp_server['ip_start'] = mfl.query_setting('dhcp_server_ip_start') if mfl.query_setting('dhcp_server_ip_start') else 100
        dhcp_server['ip_end'] = mfl.query_setting('dhcp_server_ip_end') if mfl.query_setting('dhcp_server_ip_end') else 200
        interfaces = mfl.system_interfaces()
        return render_template('dhcp_server.html', interfaces = interfaces, dhcp_server = dhcp_server )

# Just reboot.
@app.route('/reboot')
def reboot():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
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

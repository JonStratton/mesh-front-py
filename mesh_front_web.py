#!/usr/bin/env python3
__author__ = 'Jon Stratton'
import sys, os, getopt
from flask import Flask, render_template, request, session, escape, send_from_directory, abort
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

def escape_request(request):
    escaped_request = {}
    for key in request:
        escaped_request[escape(key)] = escape(request.get(key))
    return(escaped_request)

@app.route('/debug')
def debug():
    if not session.get('logged_in'):
       return render_template('web/login.html')
    else:
       cmds = ['ip a', 'sudo batctl n']
       commands_and_outputs = mfl.system_debug(cmds)
       return render_template('web/debug.html', commands_and_outputs = commands_and_outputs)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('logged_in'):
       return render_template('web/login.html')
    else:
        if request.values.get('save'):
            escaped_request = escape_request(request.values)
            mfl.upsert_setting('listen_port', escaped_request.get('listen_port'))
            mfl.upsert_setting('listen_ip', escaped_request.get('listen_ip'))
            mfl.upsert_setting('dns1', escaped_request.get('dns1'))
            mfl.upsert_setting('dns2', escaped_request.get('dns2'))
            if (request.values.get('password')): # Get the raw password!
                mfl.upsert_user('admin', mfl.hash_password(request.values.get('password'), Salt).hexdigest())
        settings = {}
        settings['listen_port'] = mfl.query_setting('listen_port')
        settings['listen_ip'] = mfl.query_setting('listen_ip')
        settings['dns1'] = mfl.query_setting('dns1')
        settings['dns2'] = mfl.query_setting('dns2')
        return render_template('web/settings.html', settings = settings)

@app.route('/wireless', methods=['GET', 'POST'])
def wireless():
    if not session.get('logged_in'):
       return render_template('web/login.html')
    else:
        if request.values.get('save'):
            escaped_request = escape_request(request.values)
            mfl.upsert_setting('wireless_interface', escaped_request.get('wireless_interface'))
            if (escaped_request.get('selected_wireless_mesh')):
                wireless_ssid, wireless_channel = escaped_request.get('selected_wireless_mesh').split('|', 1)
                mfl.upsert_setting('wireless_ssid', wireless_ssid)
                mfl.upsert_setting('wireless_channel', str(int(wireless_channel)))
            else:
                mfl.upsert_setting('wireless_ssid', escaped_request.get('wireless_ssid'))
                mfl.upsert_setting('wireless_channel', escaped_request.get('wireless_channel'))

            # If we dont have bat0 now, make one as default.
            if (not mfl.query_interface_settings('bat0', 4)):
                mfl.upsert_interface({'iface': 'bat0', 'inet': 'manual'})

            mfl.refresh_configs()
        settings = {}

        if mfl.query_setting('wireless_interface'):
            settings['wireless_interface'] = mfl.query_setting('wireless_interface')
            settings['available_wireless_meshes'] = mfl.get_available_wireless_meshes(mfl.query_setting('wireless_interface'))
        elif (len(mfl.system_interfaces('w')) >= 1):
            settings['available_wireless_meshes'] = mfl.get_available_wireless_meshes(mfl.system_interfaces('w')[0])

        settings['available_wireless_interfaces'] = mfl.system_interfaces('w')
        settings['wireless_ssid'] = mfl.query_setting('wireless_ssid')
        settings['wireless_channel'] = mfl.query_setting('wireless_channel')
        return render_template('web/wireless.html', settings = settings)

@app.route('/network', methods=['GET', 'POST'])
def network():
    if not session.get('logged_in'):
        return render_template('web/login.html')
    else:
        if request.values.get('save'):
            escaped_request = escape_request(request.values)

            mesh_interface = { 'iface': 'bat0',
                'address': escaped_request.get('ip_address'),
                'netmask': escaped_request.get('netmask')}
            if (escaped_request.get('dhcp') == 'server'):
                mesh_interface['inet'] = 'static'
            elif (escaped_request.get('dhcp') == 'client'):
                mesh_interface['inet'] = 'dhcp'
            else:
                mesh_interface['inet'] = 'manual'
            mfl.upsert_interface(mesh_interface)

            uplink_interface = escaped_request.get('uplink_interface')
            uplink_interface = re.sub('[^0-9a-zA-Z]+', '', uplink_interface)
            mfl.upsert_setting('uplink_interface', uplink_interface)
            mfl.upsert_setting('dhcp_start', escaped_request.get('dhcp_start'))
            mfl.upsert_setting('dhcp_end', escaped_request.get('dhcp_end'))
            mfl.upsert_setting('dhcp', escaped_request.get('dhcp'))
            mfl.refresh_configs()
            mfl.upsert_setting('should_reboot', '1')
        settings = {}
        if (mfl.query_interface_settings('bat0', 4)):
            mesh_interface = mfl.query_interface_settings('bat0', 4)[0]
            settings['ip_address'] = mesh_interface.get('address')
            settings['netmask'] = mesh_interface.get('netmask')

        settings['uplink_interfaces'] = mfl.system_interfaces()
        settings['uplink_interface' ] = mfl.query_setting('uplink_interface')
        settings['dhcp'] = mfl.query_setting('dhcp')
        settings['dhcp_start'] = mfl.query_setting('dhcp_start')
        settings['dhcp_end'] = mfl.query_setting('dhcp_end')
        return render_template('web/network.html', settings = settings)

@app.route('/overlay', methods=['GET', 'POST'])
@app.route('/overlay/<action>', methods=['GET', 'POST'])
@app.route('/overlay/<action>/<mod_item>', methods=['GET', 'POST'])
def overlay(action = None, mod_item = None):
    if not session.get('logged_in'):
       return render_template('web/login.html')
    elif mfl.query_setting('has_overlay'):
        if (action == 'add'):
            return render_template('web/overlay_add.html')

        if request.values.get('save'):
            escaped_request = escape_request(request.values)
            if escaped_request.get('peer'):
                if os.path.isfile('/etc/yggdrasil.conf'):
                    yggdrasil = mfl.read_json_conf('/etc/yggdrasil.conf')
                    yggdrasil['Peers'].append(escaped_request.get('peer'))
                    mfl.make_json_conf('/etc/yggdrasil.conf', yggdrasil)
        elif (action == 'delete' and mod_item):
            if os.path.isfile('/etc/yggdrasil.conf'):
                index_num = int(mod_item)
                yggdrasil = mfl.read_json_conf('/etc/yggdrasil.conf')
                del(yggdrasil['Peers'][index_num])
                mfl.make_json_conf('/etc/yggdrasil.conf', yggdrasil)
                
            
        settings = {}
        if os.path.isfile('/etc/yggdrasil.conf'):
            yggdrasil = mfl.read_json_conf('/etc/yggdrasil.conf')
            settings['StaticPeers'] = yggdrasil.get('Peers', [])
        return render_template('web/overlay.html', settings = settings)
    else:
       abort(401)

@app.route('/services', methods=['GET', 'POST'])
@app.route('/services/<action>', methods=['GET', 'POST'])
@app.route('/services/<action>/<port>', methods=['GET', 'POST'])
def services(action = 'display', port = None):
    if not session.get('logged_in'):
        return render_template('web/login.html')
    else:
        escaped_request = escape_request(request.values)
        if (escaped_request.get('save')):
            mfl.upsert_service(escaped_request)
            mfl.refresh_services()
        if (action == 'add'):
            return render_template('web/services_add.html')
        elif (action == 'delete' and port):
            for saved_service in mfl.query_services(port): # Only delete it if we created it...
                mfl.delete_service(port)
                os.remove(mfl.avahi_service_file(saved_service))
        local_services = mfl.query_services()
        remote_services = mfl.avahi_browse()
        return render_template('web/services.html', local_services=local_services, remote_services=remote_services)

# Just reboot.
@app.route('/reboot')
def reboot():
    if not session.get('logged_in'):
        return render_template('web/login.html')
    else:
        mfl.upsert_setting('should_reboot', '')
        mfl.system_reboot()
        return do_admin_login()

@app.route('/login', methods=['GET', 'POST'])
def do_admin_login():
    if (request.values.get('username') and request.values.get('password')):
        password_hash = mfl.hash_password(request.form['password'], Salt).hexdigest()
        if (mfl.user_auth(request.form['username'], password_hash)):
            session['logged_in'] = True
            return settings()
    return render_template('web/login.html')

@app.route('/logout')
def logout():
    session['logged_in'] = False
    return do_admin_login()

@app.route('/')
def home():
    return do_admin_login()

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

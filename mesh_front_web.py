#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sys, os, sqlite3
from flask import Flask, flash, redirect, render_template, request, session, abort
import mesh_front_lib as mfl

Salt = '1234'
app  = Flask(__name__)

@app.route('/ifconfig', methods=['GET', 'POST'])
def if_config():
    #if not session.get('logged_in'):
    #   return render_template('login.html')
    #else:
        # If an Interface is passed in, update it
        if (request.values.get('save')):
            interface_update = {}
            for key in request.values:
                interface_update[key] = request.values.get(key)
            mfl.upsert_interface(interface_update)

            # Update the config files on the system
            interfaces = mfl.query_interface_settings()
            mfl.make_interface_config(interfaces)

        # If we have an interface, only get it
        interface = None
        if (request.values.get('interface')):
            interface = request.values.get('interface')
        if_configs = mfl.query_interface_settings(interface)
        return render_template('ifconfig.html', ifaces=if_configs)

@app.route('/scan')
def scan():
    #if not session.get('logged_in'):
    #   return render_template('login.html')
    #else:
        networks = mfl.system_wifi_networks()
        return render_template('scan.html', networks=networks)

@app.route('/mesh', methods=['GET', 'POST'])
def mesh():
    #if not session.get('logged_in'):
    #   return render_template('login.html')
    #else:
        if (request.values.get('save')): # Save settings and generate system files
            mfl.upsert_setting('mesh_interface', request.values.get('iface'))
            mfl.upsert_interface(request.values)
            interfaces = mfl.query_interface_settings()
            mfl.make_interface_config(interfaces) # Regenerate interface file
            mfl.make_olsrd_config(request.values.get('iface'), request.values.get('address'), mfl.system_hostname()) # Generate olsrd_config
            mfl.system_bridge_interfaces(request.values.get('iface'), 'ens18')
            # Bounce stuff here, or reboot

        mesh = {}
        if (request.values.get('copy')): # Just populate the form from the scan item. Still needs to be saved
            mesh = mfl.mesh_get_defaults(request.values)
        elif (mfl.query_setting('mesh_interface')):
            mesh_interface_settings = mfl.query_interface_settings(mfl.query_setting('mesh_interface'))[0]
            mesh = mesh_interface_settings
        mesh['ifaces'] = mfl.system_interfaces('w')
        return render_template('mesh.html', mesh=mesh)

# List 
@app.route('/neighbors')
def neighbors():
    if not session.get('logged_in'):
       return render_template('login.html')
    else:
        return render_template('neighbors.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    #if not session.get('logged_in'):
    #   return render_template('login.html')
    #else:
        if (request.values.get('save')):
            mfl.system_hostname(request.values.get('hostname'))
            mfl.upsert_setting('callsign', request.values.get('callsign'))
            mfl.upsert_setting('listen_port', request.values.get('listen_port'))
            mfl.upsert_setting('listen_ip', request.values.get('listen_ip'))
            if (request.values.get('password')):
                upsert_user('admin', hash_password(request.values.get('password'), Salt).hexdigest())
        settings = {}
        settings['hostname'] = mfl.system_hostname()
        settings['callsign'] = mfl.query_setting('callsign')
        settings['listen_port'] = mfl.query_setting('listen_port')
        settings['listen_ip'] = mfl.query_setting('listen_ip')
        return render_template('settings.html', settings=settings)

# Just reboot.
@app.route('/reboot')
def reboot():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        mfl.system_reboot()
        return home()

@app.route('/status')
def status():
    return render_template('status.html')

@app.route('/login', methods=['POST'])
def do_admin_login():
    password_hash = mfl.hash_password(request.form['password'], Salt).hexdigest()
    if (mfl.user_auth(request.form['username'], password_hash)):
        session['logged_in'] = True
    return home()

@app.route('/logout')
def logout():
    session['logged_in'] = False
    return status()

@app.route('/')
def home():
    return status()

def first_run():
    global Salt
    #Salt = mfl.setup_salt()
    mfl.setup_db()
    mfl.setup_initial_settings('changeme', Salt)
    return()

if (__name__ == '__main__'):
    app.secret_key = os.urandom(12)
    if (not os.path.isfile('db.sqlite3')):
        first_run()
    port = mfl.query_setting('listen_port')
    ip   = mfl.query_setting('listen_ip')
    if (len(sys.argv) >= 2):
        port = sys.argv[1]
    app.run(host=ip, port=port, debug=False)

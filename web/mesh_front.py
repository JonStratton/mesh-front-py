#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sys, os, sqlite3
from flask import Flask
from flask import Flask, flash, redirect, render_template, request, session, abort
run_dir = os.path.dirname(os.path.realpath(__file__))
lib_loc = os.path.realpath('%s/../lib/' % run_dir)
sys.path.insert(1, lib_loc )
import mesh_front_util as mfu
import mesh_front_db as mfdb

# Default from db, but overwrite port if called as an arg
port = mfdb.get_setting('listen_port')
ip   = mfdb.get_setting('listen_ip')
if (len(sys.argv) >= 2):
    port = sys.argv[1]
app = Flask(__name__) 

@app.route('/scan')
def scan():
   wiface   = mfu.get_interface_list('w')[0]
   networks = mfu.get_available_networks(wiface)
   return render_template('scan.html', networks=networks)

@app.route('/')
def home():
   if not session.get('logged_in'):
      return render_template('login.html')
   else:
      return "Hello Boss!"

@app.route('/login', methods=['POST'])
def do_admin_login():
   password_hash = mfu.hash_password(request.form['password']).hexdigest()
   if (mfdb.user_auth(request.form['username'], password_hash)):
      session['logged_in'] = True
   else:
      flash('wrong password!')
   return home()

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return home()

if (__name__ == '__main__'):
   app.secret_key = os.urandom(12)
   app.run(host=ip, port=port, debug=False)

#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sys, os
from flask import Flask
from flask import Flask, flash, redirect, render_template, request, session, abort

run_dir = os.path.dirname(os.path.realpath(__file__))
lib_loc = os.path.realpath('%s/../lib/' % run_dir)
sys.path.insert(1, lib_loc )
import mesh_front_util as mfu

port = 8080

app = Flask(__name__) 

@app.route('/')
def home():
   if not session.get('logged_in'):
      return render_template('login.html')
   else:
      return "Hello Boss!"

@app.route('/login', methods=['POST'])
def do_admin_login():
   if request.form['password'] == 'password' and request.form['username'] == 'admin':
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
   app.run(host='0.0.0.0', port=port, debug=False)

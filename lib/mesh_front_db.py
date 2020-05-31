#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sqlite3

conn = sqlite3.connect('db.sqlite3')
#c = conn.cursor()

def get_setting(setting):
    c = conn.cursor()
    c.execute('SELECT value FROM server_settings WHERE key=?;', (setting,))
    return(c.fetchone()[0])

def set_setting(setting, value):
    c = conn.cursor()
    c.execute('INSERT INTO server_settings VALUES (?, ?);', (setting, value))
    conn.commit()
    return(0)

def user_auth(user, pass_hash):
    c = conn.cursor()
    c.execute('SELECT count(*) FROM user_settings WHERE username=? AND password_hash=?;', (user, pass_hash))
    print(c.fetchone()[0])
    return(1)

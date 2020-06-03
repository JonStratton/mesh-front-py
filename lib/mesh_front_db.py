#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sqlite3

def get_setting(setting):
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('SELECT value FROM server_settings WHERE key=?;', (setting,))
    return(c.fetchone()[0])

def set_setting(setting, value):
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('INSERT INTO server_settings (key, value) VALUES (?, ?);', (setting, value))
    conn.commit()
    return(0)

def set_interface(interface):
    iface   = interface.get('iface', '')
    netmask = interface.get('netmask', '')
    address = interface.get('address', '')
    inet    = interface.get('inet', '')
    wireless_mode    = interface.get('wireless-mode', '')
    wireless_channel = interface.get('wireless-channel', '')
    wireless_essid   = interface.get('wireless-essid', '')

    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('INSERT INTO interface_settings (iface, inet, address, netmask, wireless_mode, wireless_essid, wireless_channel) VALUES (?, ?, ?, ?, ?, ?, ?);', (iface, inet, address, netmask, wireless_mode, wireless_essid, wireless_channel))
    conn.commit()
    return(0)

def get_interface_configs():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('SELECT iface, inet, address, netmask, wireless_mode, wireless_essid, wireless_channel FROM interface_settings;')
    columns = list(map(lambda x: x[0], c.description))
    columns_length = len(columns)
    
    records = []
    for row in c.fetchall():
        record = {}
        for col_num in range(0, columns_length):
            record[columns[col_num]] = row[col_num]
        records.append(record)

    return(records)

def create_user(username, password_hash):
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('INSERT INTO user_settings VALUES (?, ?);', (username, password_hash) )
    conn.commit()
    return(0)

def user_auth(user, pass_hash):
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('SELECT count(*) FROM user_settings WHERE username=? AND password_hash=?;', (user, pass_hash))
    return(c.fetchone()[0])

#!/usr/bin/env python3
__author__ = 'Jon Stratton'
import sys, os, getopt, subprocess
from flask import Flask, render_template
import mesh_front_lib as mfl

# Defaults
root     = os.path.dirname(os.path.realpath(__file__))
Salt     = mfl.salt(os.path.join(root, 'salt.txt'))
FirstRun = not os.path.isfile(os.path.join(root, 'db.sqlite3'))
NewPassword = mfl.randomword(10) if (FirstRun) else ''

def get_defaults():
    mesh_networks = []
    # 1. Get Wireless Interfaces and Scan for Mesh Networks. 
    wirelesss_interfaces = mfl.system_interfaces('w')
    if (len(wirelesss_interfaces) >= 1):
        print('Found Wireless Interfaces: %s' % wirelesss_interfaces)
        mesh_networks = mfl.get_available_wireless_meshes(wirelesss_interfaces[0])
        print('Found Possible Mesh Networks: %s' % mesh_networks)

    # 2. Check for network connections on other interfaces
    other_interfaces = []
    for interface in mfl.system_interfaces():
        if interface not in wirelesss_interfaces:
            other_interfaces.append(interface)

    internet_interfaces = []
    for interface in other_interfaces:
        cmd = 'ping -c 1 -q 8.8.8.8 -I %s | grep "1 received"' % (interface)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line_bytes in p.stdout.readlines():
            internet_interfaces.append(interface)
    print('Found Internet Connection on: %s' % internet_interfaces)

    wireless_interface_default = ''
    if (wirelesss_interfaces):
        wireless_interface_default = wirelesss_interfaces[0]

    wireless_ssid_default, wireless_channel_default = '', ''
    if (mesh_networks):
        wireless_ssid_default = mesh_networks[0].get('ESSID')
        wireless_channel_default = mesh_networks[0].get('Channel')

    uplink_interface_default = ''
    if (internet_interfaces):
        uplink_interface_default = internet_interfaces[0]

    return(wireless_interface_default, wireless_ssid_default, wireless_channel_default, uplink_interface_default)

def user_choose(wireless_interface_default, wireless_ssid_default, wireless_channel_default, uplink_interface_default):
    wireless_interface = input('Wireless Interfaces(%s): ' % wireless_interface_default)
    if(not wireless_interface):
        wireless_interface = wireless_interface_default

    wireless_ssid = input('Wireless ESSID(%s): ' % wireless_ssid_default)
    if(not wireless_ssid):
        wireless_ssid = wireless_ssid_default

    wireless_channel = input('Wireless Channel(%s): ' % wireless_channel_default)
    if(not wireless_channel):
        wireless_channel = wireless_channel_default

    uplink_interface = input('Act as Internet Uplink on(%s): ' % uplink_interface_default)
    if(not uplink_interface):
        uplink_interface = uplink_interface_default

    dhcp = input('Act as DHCP; server, client, off: ')
    mesh_inet = 'manual'

    # If DHCP server
    ip_address, netmask, dhcp_start, dhcp_end = '', '', '', ''
    ip_address_default, netmask_default, dhcp_start_default, dhcp_end_default = '192.168.200.1', '255.255.255.0', '192.168.200.100', '192.168.200.200'
    if (dhcp == 'server'):
        mesh_inet = 'static'
        ip_address = input('IP Address(%s): ' % ip_address_default)
        if(not ip_address):
            ip_address = ip_address_default

        netmask = input('Netmask(%s): ' % netmask_default)
        if(not netmask):
            netmask = netmask_default

        dhcp_start = input('IP Start(%s): ' % dhcp_start_default)
        if(not dhcp_start):
            dhcp_start = dhcp_start_default

        dhcp_end = input('IP End(%s): ' % dhcp_end_default)
        if(not dhcp_end):
            dhcp_end = dhcp_end_default
    elif (dhcp == 'client'):
        mesh_inet = 'dhcp'

    return(wireless_interface, wireless_ssid, wireless_channel, uplink_interface, dhcp, mesh_inet, ip_address, netmask, dhcp_start, dhcp_end)

def first_run():
    mfl.setup_db()
    mfl.setup_initial_settings()
    return()

if (__name__ == '__main__'):
    if (FirstRun):
        first_run()
    if (NewPassword):
        password_hash = mfl.hash_password(NewPassword, Salt).hexdigest()
        mfl.upsert_user('admin', password_hash)
        print("New Password Set. Log in with user 'admin' and password '%s'.\n" % NewPassword)
    wireless_interface_default, wireless_ssid_default, wireless_channel_default, uplink_interface_default = get_defaults()
    wireless_interface, ssid, channel, uplink_interface, dhcp, mesh_inet, ip_address, netmask, dhcp_start, dhcp_end = user_choose(wireless_interface_default, wireless_ssid_default, wireless_channel_default, uplink_interface_default)

    # /wireless - Save
    mfl.upsert_setting('wireless_interface', wireless_interface)
    mfl.upsert_setting('wireless_ssid', ssid)
    mfl.upsert_setting('wireless_channel', channel)

    # /network - Save
    mesh_interface = { 'iface': 'bat0',
       'address': ip_address,
       'netmask': netmask,
       'inet': mesh_inet}
    mfl.upsert_interface(mesh_interface)

    mfl.upsert_setting('uplink_interface', uplink_interface)
    mfl.upsert_setting('dhcp_start', dhcp_start)
    mfl.upsert_setting('dhcp_end', dhcp_end)
    mfl.upsert_setting('dhcp', dhcp)
    mfl.refresh_configs()


# mesh-front-py
This project has moved. To get the latest version, pull from https://codeberg.org/JonStratton/mesh-front-py

mesh-front-pi is basically a flask front-end for some command line mesh networking configurations. Basically, any old Debian based Laptop or single board computer you have laying around should be easy to turn into a mesh node with very little work or knowledge of mesh networking software. And if you dont like it, you should be able to remove it and have a working system without doing an entire reinstall. 

It takes inspiration from HSMM-pi (https://github.com/urlgrey/hsmm-pi) and the defunct "Project Byzantium" project. 

## Goals
1. Allow joining an existing mesh network fairly easily. If it sees an Ad Hoc network, it should be a matter of selecting in on the Wireless page. 
1. As few dependencies as possible. Just ideally Python-flask and GNU/Linux system commands.
1. Use the most common, light and shallow version of external dependencies as possible. 
	1. Common so they will be supported as packages in most Distros for a while
	1. Light/shallow so one unused inclusion doesn't cause a rewrite. I
1. Have a front-end that is usable without JavaScript. Lynx, ancient Netscape, Mothra... 
1. Installs and Uninstalls as cleanly as possible on the file system. 
1. Works with and even installs common overlay / "darknets", such as Yggdrasil (https://yggdrasil-network.github.io/) and Cjdns (https://github.com/cjdelisle/cjdns/).

## Pre install check
Most wifi devices support mesh networking. You can double check this by running the fillowing command and searching for "Mesh" or "IBSS".

    sudo iw list

## How to install
Before installing on the system, you should test it out under a user account (with generic sudo access). 

    ./install.sh

If you run this as root, you will be prompted for a non root username. If you run it as a normal user, you might need to log off and on to make sure you have been added to the new "mesh-front" group.

If you want to build and run Yggdrasil or Cjdns on the node and be managed by mesh-front-py, you can set a toggle YGGDRASIL or CJDNS before running the installed.

    YGGDRASIL=1; export YGGDRASIL
    ./install.sh

The installer will attempt to back up some current system files, and make new version that are editable by users in the "mesh-front" group. Once the installer finishes (and you optionally log out and on again), you should be able to run the web front-end with the following command:

    ./mesh_front_web.py

If this is the first run, it will try to automatically generate an admin password. You should see the password during the first run. You can change this any time from the web front-end, or you can modify it from command line with:

    ./mesh_front_web.py -p "Super Secret Password"

You can then visit http://localhost:8080 on the local machine, or connect to http://*IP ADDRESS*:8080 on another machine connected to the same network. This listen port and IP Address can be configured later.

If everything looks fine, you can install mesh-front-py on the system with the following command:

    ./install.sh system

This will attempt to copy the install, salt, and configuration db to /var/www/mesh-front-py/, lock down the permissions a little, and install the boot service file. If you ever want to remove mesh-front-py from the system, it should be as simple as:

    ./install.sh uninstallsystem

This will remove the service and the files in /var/www/mesh-front-py. If you want to remove mesh-front-py from the system and restore the original system configuration files, you will also need to run:

    ./install.sh uninstall

## Using

### Basic
Go to the "Wireless" page. Your wireless interface should already be selected. If you are joining an existing Mesh network, it should be in the "Available Wireless Meshes" menu. You can select it and save. Otherwise, set the ESSID (Name) and Channel. This will need to be the same on all the nodes.

By default, batman-adv gives the node a local link IPv6 address. So with the basic setting or if you intend to use this with an Overlay network, you shouldnt need to set anything else at this point. You should be able to ping the IPv6 Address of all the other nodes at this point.

### Batman Mesh - Adding an network (internet) gateway
If you want one node to act as an network (or internet) Uplink to the other nodes, here is one strategy.

One internet connected Node will need to be configured as an "Uplink". On the "Network" page, you will need to select the interface with the Internet connection (example eth0). This Node should also probably be configured to act as a DHCP server, so you'll need to give it an IP address and netmask that doesn't conflict with whatever network you are linking too. For instance, if you use 192.168.1.* for your internal network, you could maybe set your Uplink node to 192.168.199.1 and set the netmask too 255.255.255.0. You'll also need to set the IP Start and End Ranges for the IPv4 addresses to give out (example 192.168.199.100 and 192.168.199.200, respectiviely). Save these settings and reboot.

On all your non uplink nodes, simply go to the “Network” settings, and set the "Act as DHCP" too “client”. IP Address and Netmask should be empty as they will now get their IP settings from the Uplink node. Save and reboot. After reboot, they should have IP addresses in the IP range you set in the DHCP Server settings on the Uplink node. The Uplink node should also be ping-able. If there is an internet connection, you should be able to ping internet addresses and hosts.

## Debugging

### Batman Meshes

The first thing to look at is if the batman-adv interface was brought up. If you run "ip a" in a terminal on the node, you should see that "bat0" has been associated with your wireless interface, and a new "bat0" interface:

    ...
    3: wlxc4e984095d7f: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq master bat0 state UP group default qlen 1000
    link/ether c4:e9:84:09:5d:7f brd ff:ff:ff:ff:ff:ff
    inet6 fe80::c6e9:84ff:fe09:5d7f/64 scope link
    valid_lft forever preferred_lft forever
    4: bat0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default qlen 1000
    link/ether 62:8a:fc:22:21:17 brd ff:ff:ff:ff:ff:ff
    inet6 fe80::608a:fcff:fe22:2117/64 scope link
    valid_lft forever preferred_lft forever
    ...

If that's okay, and you have more than one node, you should be able to run "sudo batctl n" and see your neighbors:

    [B.A.T.M.A.N. adv 2018.3, MainIF/MAC: wlxc4e984095d7f/c4:e9:84:09:5d:7f (bat0/62:8a:fc:22:21:17 BATMAN_IV)]
    IF Neighbor last-seen
    wlxc4e984095d7f dc:85de6d:7d:72 0.164s

If you don't see any neighbors, than the interface is associated with batman-adv, but the nodes are not meshing. If you see and error about no interface, then the wireless interface hasn't been associated with the bat0 interface.

If you do see the neighbors, then you should be able to ping the bat0 ipv4 or ipv6 ip on the other node. Here is the bat0 interface settings for my second node:

    jgstratton@meshtest2:~$ ip a
    ...
    4: bat0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default qlen 1000
    link/ether 0a:ce:70:5e:63:b3 brd ff:ff:ff:ff:ff:ff
    inet6 fe80::8ce:70ff:fe5e:63b3/64 scope link
    valid_lft forever preferred_lft forever

    jgstratton@meshtest1:~$ ping -I bat0 fe80::8ce:70ff:fe5e:63b3
    ping6: Warning: source address might be selected on device other than bat0.
    PING fe80::8ce:70ff:fe5e:63b3(fe80::8ce:70ff:fe5e:63b3) from :: bat0: 56 data bytes
    64 bytes from fe80::8ce:70ff:fe5e:63b3%bat0: icmp_seq=1 ttl=64 time=4.93 ms
    ....

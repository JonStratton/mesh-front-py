# mesh-front-py
mesh-front-pi is basically a flask front-end for some command line mesh networking configurations. Basically, any old Debian based Laptop or single board computer you have laying around should be easy to turn into a mesh node with very little work or knowledge of mesh networking software. And if you dont like it, you should be able to remove it and have a working system without doing an entire reinstall. 

It takes inspiration (and indeed some configuration templates) from HSMM-pi (https://github.com/urlgrey/hsmm-pi). The defunct "Project Byzantium" was also heavily in mind when I created this. 

## Goals
1. Allow joining an existing mesh network fairly easily. If it sees an Ad Hoc network with an ESSID or Address it recognizes, it should be a matter of hitting the "Mesh" button on the "Scan" page. 
1. As few dependencies as possible. Just ideally Python-flask(2 or 3), OLRS, and GNU/Linux system commands.
1. Use the most common, light and shallow version of external dependencies as possible. 
	1. Common so they will be supported as packages in most Distros for a while
	1. Light/shallow so one unused inclusion doesn't cause a rewrite. I
1. Have a front-end that is usable without JavaScript. Lynx, ancient Netscape, Mothra... 
1. Installs and Uninstalls as cleanly as possible on the file system. 
1. Allows auto recondition and joining popular meshes (hsmm, aredn, LibreMesh(batman-adv))

## Possible Future Enhancements
1. Clean up the Mesh Network detection, and populate it with a configuration file.
1. Work better with batman-adv.
1. Add sysV init process, so it can run on Devuan and old versions of Debian.
1. An optional CJDNS layer.
1. A configuration option that allows the downloading of mesh-front-pi via the web frontend. 

## How to install
Before installing on the system, you should test it out under a user account (with generic sudo access). 

`./install.sh`

If you run this as root, you will be prompted for a non root username. If you run it as a normal user, you might need to log off and on to make sure you have been added to the new "mesh-front" group.

The installer will attempt to back up some current system files, and make new version that are editable by users in the "mesh-front" group. Once the installer finishes (and you optionally log out and on again), you should be able to run the web front-end with the following command:

`$ ./mesh_front_web.py`

If everything launches properly, you should see something like the following:

`New Password Set. Log in with user 'admin' and password 'g{8sLvuzI3'.

 * Serving Flask app "mesh_front_web" (lazy loading)
 * Environment: production
   WARNING: Do not use the development server in a production environment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://0.0.0.0:8080/ (Press CTRL+C to quit)`

If this is the first run, it will try to automatically generate an admin password. You should see the password during the first run. You can change this any time from the web front-end, or you can modify it from command line with:

`./mesh_front_web.py -p "Super Secret Password"`

You can then visit http://localhost:8080 on the local machine, or connect to http://*IP ADDRESS*:8080 on another machine connected to the same network. This listen port and IP Address can be configured later.

If everything looks fine, you can install mesh-front-py on the system with the following command:

`./install.sh system`

This will attempt to copy the install, salt, and configuration db to /var/www/mesh-front-py/, lock down the permissions a little, and install the boot service file. If you ever want to remove mesh-front-py from the system, it should be as simple as:

`./install.sh uninstallsystem`

This will remove the service and the files in /var/www/mesh-front-py. If you want to remove mesh-front-py from the system and restore the original system configuration files, you will also need to run:

`./install.sh uninstall`

## Notes on using

If you have an Ad Hoc mesh in your area you want to join, it should simply be a matter of going to the "Scan" page, and hitting the "Mesh" button. 

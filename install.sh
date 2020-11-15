#!/bin/sh

myname=mesh-front
package_list="batctl python3-flask iptables-persistent dnsmasq iw ifupdown wireless-tools"
package_list_build="" # These will be cleaned out (if new) after install
controlled_system_files="/etc/network/interfaces /etc/iptables/rules.v4 /etc/hosts /etc/hostname /etc/dnsmasq.d/mesh-front-dnsmasq.conf /etc/sysctl.d/mesh-front-sysctl.conf"

###########
# Install #
###########
install_mesh_front()
{
# Build lists of packages and files
if [ $YGGDRASIL = 1 ]; then
   package_list="$package_list dirmngr"
   controlled_system_files="$controlled_system_files /etc/yggdrasil.conf"
fi
if [ $CJDNS = 1 ]; then
   package_list_build="$package_list_build build-essential nodejs python2.7"
   controlled_system_files="$controlled_system_files /etc/cjdroute.conf"
fi

# Install Deps
sudo apt-get update
new_packages="" # When we cleanup, we only want to remove packages we freshly installed
for package in $package_list; do
   if [ `sudo DEBIAN_FRONTEND=noninteractive apt-get install -y $package | grep "is already the newest version" | wc -l` -eq 0 ]; then
      new_packages="$new_packages $package"
   fi
done
echo $new_packages > ./new_packages.txt

# Install Temp Deps for building
packages_to_delete=""
for package in $package_list_build; do
   if [ `sudo DEBIAN_FRONTEND=noninteractive apt-get install -y $package | grep "is already the newest version" | wc -l` -eq 0 ]; then
      packages_to_delete="$packages_to_delete $package"
   fi
done

# New Group and Sudo Access
sudo groupadd $myname
installuser=`whoami`
if [ $installuser = 'root' ]; then
    read -p "Run as root. Please enter the name of a non root user to gran $myname access too: " installuser
fi
sudo usermod -a -G $myname $installuser
sudo cp install/mesh-front-sudoers /etc/sudoers.d/mesh-front-sudoers
sudo chmod 440 /etc/sudoers.d/mesh-front-sudoers

# Install Optional Overlay Networks
if [ $YGGDRASIL ]; then
   install_yggdrasil
fi
if [ $CJDNS ]; then
   install_cjdns
fi

# Roll everything up in a tarball for other people to download
if [ ! -e static/mesh-front-py.tgz ]; then
   tar -czf static/mesh-front-py.tgz \
      --exclude=static/mesh-front-py.tgz \
      --exclude=salt.txt \
      --exclude=db.sqlite3 \
      --exclude=__pycache__ \
     ../mesh-front-py
fi

# Remove Temp Deps, autoremove and clean
sudo DEBIAN_FRONTEND=noninteractive apt-get remove --purge -y $packages_to_delete
sudo apt-get autoremove -y
sudo apt-get clean -y

# Change perms on and backup controlled files
for system_file in $controlled_system_files
do
   if [ -e $system_file ]; then
      sudo cp $system_file $system_file.$myname-backup
   else
      sudo touch $system_file
   fi
   sudo chown :$myname $system_file
   sudo chmod g+w $system_file
done

# Turn off Network Manager if its installed
if [ -d '/etc/NetworkManager' ]; then
   sudo systemctl stop NetworkManager
   sudo systemctl disable NetworkManager
fi

# Hint so we dont have to log out maybe
echo "Run the following command: newgrp $myname"
}

# Install yggdrasil
install_yggdrasil()
{
# https://yggdrasil-network.github.io/installation-linux-deb.html
gpg --fetch-keys https://neilalexander.s3.dualstack.eu-west-2.amazonaws.com/deb/key.txt
gpg --export 569130E8CA20FBC4CB3FDE555898470A764B32C9 | sudo apt-key add -
echo 'deb http://neilalexander.s3.dualstack.eu-west-2.amazonaws.com/deb/ debian yggdrasil' | sudo tee /etc/apt/sources.list.d/yggdrasil.list
sudo apt-get update
sudo apt-get install -y yggdrasil
sudo systemctl enable yggdrasil
sudo systemctl start yggdrasil
sudo chmod 660 /etc/yggdrasil.conf
}

# Download and build cjdns
install_cjdns()
{
if [ ! -e static/cjdns-master.tar.gz ]
then
   wget https://github.com/cjdelisle/cjdns/archive/master.tar.gz -O static/cjdns-master.tar.gz
fi
tar xzf static/cjdns-master.tar.gz
cd cjdns-master
. ./do
sudo mv cjdroute /usr/bin/cjdroute
sudo cp contrib/systemd/cjdns.service /etc/systemd/system/
cd ..
sudo sh -c '(umask 007 && /usr/bin/cjdroute --genconf > /etc/cjdroute.conf )'
rm -rf cjdns-master

sudo systemctl daemon-reload
sudo systemctl start cjdns.service
sudo systemctl enable cjdns.service
}

#############
# Uninstall #
#############
uninstall_mesh_front()
{
# Unstall Optional Apps
if [ $YGGDRASIL ]; then
   uninstall_yggdrasil
fi
if [ $CJDNS ]; then
   uninstall_cjdns
fi

# Restore old system files
for system_file in $controlled_system_files; do
   sudo rm $system_file
   if [ -e $system_file.$myname-backup ]
   then
      sudo mv $system_file.$myname-backup $system_file
   else
      sudo rm $system_file.$myname-backup
   fi
done

# Remove Packages
sudo DEBIAN_FRONTEND=noninteractive apt-get remove --purge -y `cat ./new_packages.txt`
rm ./new_packages.txt
sudo apt-get autoremove -y
sudo apt-get clean -y

# Delete group and sudo access
sudo groupdel $myname
sudo rm /etc/sudoers.d/mesh-front-sudoers

# Enable NetworkManager if installed
if [ -d '/etc/NetworkManager' ]; then
   sudo systemctl start NetworkManager
   sudo systemctl enable NetworkManager
fi
}

uninstall_yggdrasil()
{
sudo apt-get remove --purge -y yggdrasil
sudo rm /etc/apt/sources.list.d/yggdrasil.list
sudo apt-get update
}

uninstall_cjdns()
{
sudo systemctl disable cjdns.service
sudo rm /etc/systemd/system/cjdns.service
sudo rm /usr/bin/cjdroute
sudo rm /etc/cjdroute.conf
sudo rm /etc/cjdroute.conf.mesh-front-backup
}

##################
# Install System #
##################
install_mesh_front_system()
{
# Create location in /var and copy files too it
sudo mkdir -p /var/www/mesh-front-py/
sudo cp -r . /var/www/mesh-front-py/

# Make sure the permissions are good
sudo chown -R root:root /var/www/mesh-front-py/
sudo chmod -R go-w /var/www/mesh-front-py/

# DB should be read write by root and mesh front only. Other shouldnt be able to read
sudo chown :mesh-front /var/www/mesh-front-py/db.sqlite3
sudo chmod g+w /var/www/mesh-front-py/db.sqlite3
sudo chmod o-r /var/www/mesh-front-py/db.sqlite3

# Salt should be rw for root, readable by mesh front. Other shouldnt have access
sudo chmod go-rwx /var/www/mesh-front-py/salt.txt
sudo chown :mesh-front /var/www/mesh-front-py/salt.txt
sudo chmod g+r /var/www/mesh-front-py/salt.txt

# Install service
sudo cp install/mesh-front.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start mesh-front.service
sudo systemctl enable mesh-front.service
}

####################
# Uninstall System #
####################
uninstall_mesh_front_system()
{
# Stop Service and uninstall
sudo systemctl stop mesh-front.service
sudo systemctl disable mesh-front.service
sudo rm /etc/systemd/system/mesh-front.service

# Remove base directory
sudo rm -rf /var/www/mesh-front-py/

# Generic Warning about OLSR still possibly running.
echo "Warning, mesh network services are still installed and enables. Run 'uninstall' to remove those too."
}

########
# Test #
########
test_mesh_front()
{
python3 -m unittest -v mesh_front_lib_test.TestUtils
}

########
# Main #
########

if [ $1 ]
then
   case $1 in
      uninstall)
         uninstall_mesh_front
      ;;
      system)
         install_mesh_front_system
      ;;
      uninstallsystem)
         uninstall_mesh_front_system
      ;;
      test)
         test_mesh_front
      ;;
   esac
else
   install_mesh_front
   test_mesh_front
fi

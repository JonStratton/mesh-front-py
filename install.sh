#!/bin/sh

myname=mesh-front
system_files="/etc/network/interfaces /etc/olsrd/olsrd.conf /etc/olsrd/olsrd.key /etc/default/olsrd /etc/iptables/rules.v4 /etc/hosts /etc/hostname /etc/dnsmasq.d/mesh-front-dnsmasq.conf"

###########
# Install #
###########
install_mesh_front()
{
# 0. Install dependancies
sudo apt-get update
sudo apt-get install -y \
	python-flask \
	olsrd \
	iptables-persistent

# 1. Back up system files.
for system_file in $system_files
do
   if [ -e $system_file ]
   then
      sudo cp $system_file $system_file.$myname-backup
   else
      sudo touch $system_file
   fi
done

# 2. Create Group if it doesnt exist
sudo groupadd $myname

# 3. Add group to running user
installuser=`whoami`
if [ $installuser = 'root' ]
then
    read -p "Run as root. Please enter the name of a non root user to gran $myname access too: " installuser
fi
sudo usermod -a -G $myname $installuser
#newgrp $myname

# 4. Add sudo access to group, and other generic install files
sudo cp install/mesh-front-sudoers /etc/sudoers.d/mesh-front-sudoers
sudo chmod 440 /etc/sudoers.d/mesh-front-sudoers
sudo cp install/olsrd /etc/default/olsrd

# 5. Open System files to group
for system_file in $system_files
do
   sudo chown :$myname $system_file
   sudo chmod g+w $system_file
done
}

#############
# Uninstall #
#############
uninstall_mesh_front()
{
# 0. Restore old system files
for system_file in $system_files
do
   sudo rm $system_file
   if [ -e $system_file.$myname-backup ]
   then
      sudo mv $system_file.$myname-backup $system_file
   else
      sudo rm $system_file.$myname-backup
   fi
done

# 1. Install dependancies
sudo apt-get remove --purge -y \
	python-flask \
	olsrd \
	iptables-persistent
sudo sudo apt autoremove -y

# 2. Create Group if it doesnt exist
if [ `grep $myname /etc/group | wc -l` ]
then
   sudo groupdel $myname
fi

# 3. remove access to group
sudo rm /etc/sudoers.d/mesh-front-sudoers
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
python -m unittest -v mesh_front_lib_test.TestUtils
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

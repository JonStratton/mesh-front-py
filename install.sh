#!/bin/sh

myname=mesh-front
system_files="/etc/network/interfaces /etc/olsrd/olsrd.conf /etc/default/olsrd"

###########
# Install #
###########
install_mesh_front()
{
# 0. Back up system files.
for system_file in $system_files
do
   if [ -e $system_file ]
   then
      sudo cp $system_file $system_file.$myname
   fi
done

# 1. Install dependancies
sudo apt-get update
sudo apt-get install -y \
	python-flask \
	olsrd

# 2. Create Group if it doesnt exist
sudo groupadd $myname

# 3. Add group to running user
installuser=`whoami`
if [ $installuser = 'root' ]
then
    read -p "Run as root. Please enter the name of a non root user to gran $myname access too: " installuser
fi
sudo usermod -a -G $myname $installuser

# 4. Add sudo access to group, and other generic install files
sudo cp install/mesh-front-sudoers /etc/sudoers.d/mesh-front-sudoers
sudo chmod 440 /etc/sudoers.d/mesh-front-sudoers
sudo cp install/olsrd /etc/default/olsrd

# 5. Make db defaulting with current settings.
#    make_config.py probably needs to be done as root until our new group is available
python bin/make_db.py
sudo python bin/make_config.py

# 6. Open System files to group
for system_file in $system_files
do
   if [ -e $system_file ]
   then
      sudo chown :$myname $system_file
      sudo chmod g+w $system_file
   fi
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
   if [ -e $system_file.$myname ]
   then
      sudo rm $system_file
      sudo mv $system_file.$myname $system_file
   fi
done

# 1. Install dependancies
sudo apt-get remove --purge -y \
	python-flask \
	olsrd
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
sudo chown :mesh-front /var/www/mesh-front-py/db.sqlite3
sudo chmod g+w /var/www/mesh-front-py/db.sqlite3

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
# 1. Cache cwd and cd into test dir
mycwd=`pwd`
cd `dirname $0`/test

# 2. run tests
python -m unittest -v mesh_front_util_test.TestUtils

# 3. cd back
cd $mycwd
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

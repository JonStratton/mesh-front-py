#!/bin/sh

myname=mesh-front
install_packages="python-flask iptables-persistent dnsmasq iw build-essential bison flex libgps-dev"
system_files="/etc/network/interfaces /etc/olsrd/olsrd.conf /etc/olsrd/olsrd.key /etc/default/olsrd /etc/iptables/rules.v4 /etc/hosts /etc/hostname /etc/dnsmasq.d/mesh-front-dnsmasq.conf"
init="systemd"

# Which init system do we use?
if [ ! -e '/usr/bin/systemctl' ]
then
   init="sysV"
fi

if [ `cat /etc/issue | grep -i ubuntu | wc -l` -ne 0 ]
then
   install_packages="python3-flask iptables-persistent dnsmasq iw build-essential bison flex libgps-dev python-is-python3"
fi

###########
# Install #
###########
install_mesh_front()
{
# 0. Install dependancies
sudo apt-get update
if [ -e ./new_packages.txt ]
then
   rm ./new_packages.txt
fi
for install_package in $install_packages
do
   if [ `sudo DEBIAN_FRONTEND=noninteractive apt-get install -y $install_package | grep "is already the newest version" | wc -l` -eq 0 ]
   then
      echo $install_package >> ./new_packages.txt
   fi
done

# Download and build olrsd
if [ ! -d share ]
then
   mkdir share
fi
if [ ! -e share/olsrd-master.tar.gz ]
then
   wget https://github.com/OLSR/olsrd/archive/master.tar.gz -O share/olsrd-master.tar.gz
fi
tar xzf share/olsrd-master.tar.gz
cd olsrd-master
make
sudo make install
make libs
sudo make libs_install
cd ..
sudo cp install/olsrd.init /etc/init.d/olsrd
sudo cp install/olsrd.default /etc/default/olsrd
if [ $init = "systemd" ]
then
    systemctl enable olsrd
elif [ $init = "sysV" ]
then
    sudo update-rc.d olsrd defaults
    sudo update-rc.d olsrd enable
fi

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
if [ -e ./new_packages.txt ]
then
    install_packages=`cat ./new_packages.txt | tr '\n' ' '`
fi

for new_package in $install_packages
do
   sudo DEBIAN_FRONTEND=noninteractive apt-get remove --purge -y $new_package
done
sudo apt autoremove -y
rm ./new_packages.txt

# 2. Create Group if it doesnt exist
if [ `grep $myname /etc/group | wc -l` ]
then
   sudo groupdel $myname
fi

# 3. remove access to group
sudo rm /etc/sudoers.d/mesh-front-sudoers

# 4. remove olsrd
if [ $init = "systemd" ]
then
    systemctl disable olsrd
elif [ $init = "sysV" ]
then
    sudo update-rc.d olsrd remove
fi
cd olsrd-master
sudo make uninstall
sudo make libs_uninstall
sudo rm /etc/init.d/olsrd
sudo rm /etc/default/olsrd
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
if [ $init = "systemd" ]
then
    sudo cp install/mesh-front.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl start mesh-front.service
    sudo systemctl enable mesh-front.service
elif [ $init = "sysV" ]
then
    sudo useradd $myname --no-user-group --groups $myname --shell /usr/sbin/nologin
    sudo cp install/mesh-front.init /etc/init.d/mesh-front
    sudo chmod +x /etc/init.d/mesh-front
    sudo update-rc.d mesh-front defaults
    sudo update-rc.d mesh-front enable
    sudo service mesh-front start
fi
}

####################
# Uninstall System #
####################
uninstall_mesh_front_system()
{
# Stop Service and uninstall

if [ $init = "systemd" ]
then
    sudo systemctl stop mesh-front.service
    sudo systemctl disable mesh-front.service
    sudo rm /etc/systemd/system/mesh-front.service
elif [ $init = "sysV" ]
then
    sudo service mesh-front stop
    sudo update-rc.d mesh-front disable
    sudo update-rc.d mesh-front remove
    sudo rm /etc/init.d/mesh-front
    sudo userdel $myname
fi

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

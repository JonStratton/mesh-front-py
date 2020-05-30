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

# 3. Add sudo access to group

# 4. Add group to running user
sudo usermod -a -G $myname `whoami`

# 5. Open System files to group
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
   if [ -e $system_file ]
   then
      sudo rm $system_file
      sudo mv $system_file.$myname $system_file
   fi
done

# 1. Install dependancies
sudo apt-get remove -y \
	python-flask \
	olsrd

# 2. Create Group if it doesnt exist
if [ `grep $myname /etc/group` ]
then
   sudo groupdel $myname
fi

# 3. Add sudo access to group
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
python -m unittest -v mesh_front_util_test.TestSimpleUtils

# 3. cd back
cd $mycwd
}

########
# Main #
########

if [ $1 ]
then
   if [ $1 = "uninstall" ]
   then
      uninstall_mesh_front
   elif [ $1 = "test" ]
   then
      test_mesh_front
   fi
else
   install_mesh_front
   test_mesh_front
fi

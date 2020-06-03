#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sys, os
run_dir = os.path.dirname(os.path.realpath(__file__))
lib_loc = os.path.realpath('%s/../lib/' % run_dir)
sys.path.insert(1, lib_loc )
import mesh_front_template as mft
import mesh_front_db as mfdb

interfaces = mfdb.get_interface_configs()
mft.make_interface_config(interfaces)

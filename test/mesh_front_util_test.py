#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sys, os, unittest
run_dir = os.path.dirname(os.path.realpath(__file__))
lib_loc = os.path.realpath('%s/../lib/' % run_dir)
sys.path.insert(1, lib_loc)
import mesh_front_util as mfu
import mesh_front_db as mfdb

class TestTemplates(unittest.TestCase):
    "TODO"

class TestSudoCommands(unittest.TestCase):
    "TODO"
    #def test_network_scan(self): # Probably should be turned off for normal testing
    #    networks = mfu.get_available_networks('wlx60e32715d618')
    #    self.assertTrue(networks)
    #    for network in networks:
    #        for key in network:
    #            print('%s: %s' % (key, network[key]))


class TestDB(unittest.TestCase):
    "TODO"
    #def test_settings(self):
    #    listen_port = mfdb.get_setting('listen_port')
    #    print('Listen Port: %s' % (listen_port))
    #    self.assertTrue(listen_port)

class TestUtils(unittest.TestCase):
    def test_interfaces(self):
        interfaces = mfu.get_interface_list()
        self.assertTrue(interfaces)
        for interface in interfaces:
            interface_state = mfu.get_interface_state(interface)
            self.assertTrue(interface_state)
            #print('Interface: %s(%s)' % (interface, interface_state))
    
    def test_hostname(self):
        hostname = mfu.get_hostname()
        #print('Hostname: %s' % (hostname))
        self.assertTrue(hostname)

    def test_gen_ip(self):
        generated_ip = '10.%s' % ('.'.join(mfu.get_bg_by_string('test1', 3)))
        #print('Generated IP(test1): %s' % (generated_ip))
        self.assertEqual(generated_ip, '10.1.249.109')

if (__name__ == '__main__'):
    unittest.main()

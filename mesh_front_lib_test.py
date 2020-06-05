#!/usr/bin/env python
__author__ = 'Jon Stratton'
import sys, os, unittest
sys.path.insert(1, 'lib/')
import mesh_front_util as mfu

class TestTemplates(unittest.TestCase):
    "TODO"

class TestSudoCommands(unittest.TestCase):
    "TODO"

class TestDB(unittest.TestCase):
    "TODO"

class TestUtils(unittest.TestCase):
    def test_interfaces(self):
        interfaces = mfu.get_interface_list()
        self.assertTrue(interfaces)
        #for interface in interfaces:
        #    interface_state = mfu.get_interface_state(interface)
        #    self.assertTrue(interface_state)
        #    print('Interface: %s(%s)' % (interface, interface_state))
    
    def test_hostname(self):
        hostname = mfu.get_hostname()
        self.assertTrue(hostname)

    def test_gen_ip(self):
        generated_ip = '10.%s' % ('.'.join(mfu.get_bg_by_string('test1', 3)))
        self.assertEqual(generated_ip, '10.1.249.109')

if (__name__ == '__main__'):
    unittest.main()

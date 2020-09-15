#!/usr/bin/env python3
__author__ = 'Jon Stratton'
import sys, os, unittest
sys.path.insert(1, 'lib/')
import mesh_front_lib as mfl

class TestTemplates(unittest.TestCase):
    "TODO"

class TestSudoCommands(unittest.TestCase):
    "TODO"

class TestDB(unittest.TestCase):
    "TODO"

class TestUtils(unittest.TestCase):
    def test_interfaces(self):
        interfaces = mfl.system_interfaces()
        self.assertTrue(interfaces)

    #def test_interface_settings(self):
    #    interfaces = mfl.system_interface_settings('lo') # Returns empty
    #    self.assertTrue(interfaces)
    
    def test_hostname(self):
        hostname = mfl.system_hostname()
        self.assertTrue(hostname)

    def test_gen_ip(self):
        generated_ip = '10.%s' % ('.'.join(mfl.get_bg_by_string('test1', 3)))
        self.assertEqual(generated_ip, '10.1.249.109')

if (__name__ == '__main__'):
    unittest.main()

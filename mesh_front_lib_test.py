#!/usr/bin/env python3
__author__ = 'Jon Stratton'
import sys, os, unittest, tempfile
sys.path.insert(1, 'lib/')
import mesh_front_lib as mfl

# These tests possibly write files to the fs
class TestFileSystem(unittest.TestCase):
    def test_salt(self):
        salt = mfl.salt('/dev/null')
        self.assertTrue(salt)

    def test_json_conf(self):
        test_file = tempfile.NamedTemporaryFile().name
        mfl.make_json_conf(test_file, {'test':'1'})
        test_file_contents = mfl.read_json_conf(test_file)
        self.assertEqual(test_file_contents['test'], '1')

# These tests read system commands and fs
class TestSystem(unittest.TestCase):
    def test_system_debug(self):
        command_returns = mfl.system_debug(['echo hello'])
        self.assertEqual(command_returns[0]['command'], 'echo hello')
        self.assertEqual(command_returns[0]['output'][0], 'hello')

    def test_system_get_interface_state(self):
        lo_state = mfl.system_get_interface_state('lo')
        self.assertTrue(lo_state, 'unknown')

    def test_interfaces(self):
        interfaces = mfl.system_interfaces()
        self.assertTrue(interfaces)

    def test_interface_settings(self):
        interfaces = mfl.system_interface_settings('lo') # Returns empty
        self.assertTrue(interfaces)
    
    def test_hostname(self):
        hostname = mfl.system_hostname()
        self.assertTrue(hostname)

# Test of simple util type functions
class TestUtil(unittest.TestCase):
    def test_clean_network(self):
        clean_network = mfl.clean_network({'DS Parameter set': 'XX10XX', 'capability': 'IBSS XXXX'})
        self.assertEqual(clean_network['Mode'], 'Ad-Hoc')
        self.assertEqual(clean_network['Channel'], '10')

    def test_avahi_service_file(self):
        avahi_service_file = mfl.avahi_service_file({'port': 'XX22XX', 'protocol': ';s*s\'h\\'})
        self.assertEqual(avahi_service_file, '/etc/avahi/services/22_ssh.service')

    def test_hash_password(self):
        hashed_password = mfl.hash_password('123456').hexdigest()
        hashed_password2 = mfl.hash_password('123456', '123456').hexdigest()
        self.assertEqual(hashed_password, 'e10adc3949ba59abbe56e057f20f883e')
        self.assertEqual(hashed_password2, 'ea48576f30be1669971699c09ad05c94')

    def test_randomword(self):
        randomword10 = mfl.randomword(10)
        self.assertEqual(len(randomword10), 10)

if (__name__ == '__main__'):
    unittest.main()

#!/usr/bin/env python
__author__ = 'Jon Stratton'
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'))

def make_interface_config(interfaces):
    config_file = '/etc/network/interfaces'

    template = env.get_template('interfaces')
    output_from_parsed_template = template.render(ifaces=interfaces)

    print(output_from_parsed_template)
    #with open(config_file, 'w') as f:
    #    f.write(output_from_parsed_template)
    return(0)

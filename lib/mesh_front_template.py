#!/usr/bin/env python
__author__ = 'Jon Stratton'
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'))

def make_header(config_file):
    header = []
    header.append('# Created by mesh-front-py')
    header.append('# Moved to %s' % config_file)
    return("\n".join(header))

def make_interface_config(interfaces):
    config_file = '/etc/network/interfaces'
    contents = []
    contents.append(make_header(config_file))
    for interface in interfaces:
        contents.append(make_interface(interface))

    with open(config_file, 'w') as f:
        f.write("\n".join(contents))
    return(0)

def make_interface(interface):
    template = env.get_template('interfaces')
    output_from_parsed_template = template.render(interface)
    return(output_from_parsed_template)

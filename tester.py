#!/usr/bin/env python

from netmiko import ConnectHandler
import xmltodict
import pprint
import json


pp = pprint.PrettyPrinter(indent=2)

test_device = {
  'device_type': 'juniper_junos',
  'ip': '192.168.30.200',
  'username': 'rfit',
  'password': "K&Mbpa71"
}

net_connect = ConnectHandler(**test_device)

xml = net_connect.send_command('show ospf neighbor instance all | display xml')

output = xmltodict.parse(xml)

#print(json.dumps(output["rpc-reply"]["ospf-neighbor-information-all"]))

instances = {}

cur_instance = ""
for key, value in output["rpc-reply"]["ospf-neighbor-information-all"]["ospf-instance-neighbor"].items():

  if key == u'ospf-instance-name':
    instances[value] = []
    cur_instance = value
    print(cur_instance + ":\n")
  if key == u'ospf-neighbor':
    for neighborinfo in value:

      if neighborinfo["ospf-neighbor-state"] == "Full":
        instances[cur_instance].append(neighborinfo["neighbor-address"])

pp.pprint(instances)

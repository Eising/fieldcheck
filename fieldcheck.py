#!/usr/bin/env python

from netmiko import ConnectHandler
import xmltodict
import json
import sys
import subprocess
import os
import argparse


class FieldTester(object):

  __version__ = "0.9"

  def __init__(self, username, keyfile, ip):
    self.ip = ip
    self.username = username
    self.keyfile = keyfile
    self.handler = False

  def connect(self, pass_exceptions=False):
    test_device = {
      'device_type': 'juniper_junos',
      'ip': self.ip,
      'username': self.username,
      'use_keys': True,
      'key_file': self.keyfile
    }
    if pass_exceptions:
      handler = ConnectHandler(**test_device)
    else:
      try:
        handler = ConnectHandler(**test_device)
      except:  # get possible exceptions
        print("Error: ", sys.exc_info()[0])
        raise

    return handler

  def test_ping(self):
    try:
      response = subprocess.call(
        ["ping", "-c1", self.ip], stdout=open(os.devnull, 'wb')
      )
      return True
    except subprocess.CalledProcessError:
      return False

  def test_connect(self):
    try:
      self.connect(True)
    except (EOFEerror, SSHException):
      return False
    return True

  def test_ospf_neighbors(self):
    # Returns the number of full OSPF neighbors

    output = self.get_output("show ospf neighbor instance all")
    neighbors = []
    if "ospf-neighbor-information-all" in output:
      for neighbor in output["ospf-neighbor-information-all"]["ospf-instance-neighbor"]["ospf-neighbor"]:
        if neighbor["ospf-neighbor-state"] == "Full":
          neighbors.append(neighbor["interface-name"])

    return len(set(neighbors))

  def test_default_route(self):
    output = self.get_output("show route 0.0.0.0/0 exact")
    if "route-table" in output["route-information"]:
      return True
    else:
      return False

  def get_output(self, command):
    if self.handler:
      handler = self.handler
    else:
      self.handler = self.connect()
      handler = self.handler

    # send and get as xml
    full_command = "{} | display xml".format(command)
    xml = handler.send_command(full_command)
    output = xmltodict.parse(xml)["rpc-reply"]
    return output

  def run_tests(self):
    # Run tests and output in json
    # intended for script execution

    # Prepare dict for JSON output
    output = {"tests": [], "result": ""}
    # Run tests
    if self.test_ping():
      output["tests"].append({
        "test_name": "Ping test",
        "result": "OK"
      })
      if self.test_connect():
        output["tests"].append({
          "test_name": "SSH Connectivity test",
          "result": "OK"
        })
        neighbors = self.test_ospf_neighbors()
        if neighbors == 1:
          output["tests"].append({
            "test_name": "OSPF Neighbor test",
            "result": "Partial",
            "info": "Found 1 OSPF neighbor. Requires 2 or more to pass test"
          })
        elif neighbors > 1:
          output["tests"].append({
            "test_name": "OSPF Neighbor test",
            "result": "OK"
          })
        elif neighbors == 0:
          output["tests"].append({
            "test_name": "OSPF Neighbor test",
            "result": "Failed",
            "info": "Found 0 OSPF neighbors."
          })
        if self.test_default_route():
          output["tests"].append({
            "test_name": "Default route test",
            "result": "OK"
          })
        else:
          output["tests"].append({
            "test_name": "Default route test",
            "result": "Failed"
          })

      else:
        output["tests"].append({
          "test_name": "SSH Connectivity test",
          "result": "Failed"
        })

    else:
      output["tests"].append({
        "test_name": "Ping test",
        "result": "Failed"
      })

    results = {"OK": 0, "Partial": 0, "Failed": 0}
    for test in output["tests"]:
      results[test["result"]] += 1
    if results["OK"] == len(output["tests"]):
      output["result"] = "OK"
    elif (results["OK"] > 0 and results["OK"] < len(output["tests"])):
      output["result"] = "Partial"
    else:
      output["result"] = "Failed"

    return json.dumps(output, indent=4)


if __name__ == '__main__':

  # Load arguments
  parser = argparse.ArgumentParser()
  parser.add_argument(
    '-u', '--username', action="store", dest="username", help="SSH Username"
  )
  parser.add_argument(
    '-k', '--keyfile', action="store",
    dest="keyfile", help="SSH Private Key file"
  )
  parser.add_argument('node', nargs=1, help="IP or hostname to check")
  args = parser.parse_args()

  if not args.username or not args.keyfile or not args.node:
    parser.print_help()
    sys.exit()

  ft = FieldTester(args.username, args.keyfile, args.node.pop())
  print(ft.run_tests())

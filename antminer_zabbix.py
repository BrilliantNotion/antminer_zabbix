#!/usr/bin/env python3

import argparse
import json
import os
import socket
import subprocess

### Constants.
typesValid = ["A3", "D3", "L3+", "S9", "T9+"]
metricsValid = ["averageSpeed", "averageSpeed5s", "chainFailures", "chipTemp", "errorRate", "fanFront", "fanRear", "pcbTemp", "speed"]

### Calculation functions.
def metric_to_api_command(metric):
    """Returns the associated API command for the specified metric.""" 
    switcher = {
        "averageSpeed": "summary",
        "averageSpeed5s": "summary",
        "chainFailures": "stats",
        "chipTemp": "stats",
        "errorRate": "summary",
        "fanFront": "stats",
        "fanRear": "stats",
        "pcbTemp": "stats",
        "speed": "summary",
    }
    return switcher.get(metric, None)

def metric_to_keys(metric):
    """Returns the associated key for the specified metric.""" 
    switcher = {
        "averageSpeed": "GHS av",
        "averageSpeed5s": "GHS 5s",
        "chainFailures": "chain_acs[i]",
        "chipTemp": "temp2_[i]",
        "errorRate": "Device Hardware%",
        "fanFront": "fan1,fan3",
        "fanRear": "fan2,fan6",
        "pcbTemp": "temp3_[i],temp[i]",
        "speed": "GHS 5s",
    }
    return switcher.get(metric, None)

def metric_failure_default(metric):
    """Returns the default failue value for the specified metric."""
    return "0"

def metric_count_failures(result, baseKey, count):
    """Counts the number of chain failures ("x") for the specified keys."""
    failures = 0
    baseKeys = baseKey.split(",")
    for baseKey in baseKeys:
        for i in range(1, count):
            key = baseKey.replace("[i]", str(i))
            if key in result:
                failures += str(result[key]).count('x')
    return failures

def max_value_for_keys(result, baseKey, count):
    """Finds the maximum value for the specified keys."""
    values = []
    baseKeys = baseKey.split(",")
    for baseKey in baseKeys:
        for i in range(1, count):
            key = baseKey.replace("[i]", str(i))
            if key in result:
                values.append(result[key])
    return max(values)

def calculate_value(miner_type, metric, api_result):
    """Calculate the value for the specified metric and type using the resulting API data."""
    try:
        if metric == "averageSpeed":
            result = api_result["SUMMARY"][0][metric_to_keys(metric)]
        elif metric == "averageSpeed5s":
            result = api_result["SUMMARY"][0][metric_to_keys(metric)]
        elif metric == "chainFailures":
            result = metric_count_failures(api_result["STATS"][1], metric_to_keys(metric), 64)
        elif metric == "chipTemp":
            result = max_value_for_keys(api_result["STATS"][1], metric_to_keys(metric), 64)
        elif metric == "errorRate":
            result = api_result["SUMMARY"][0][metric_to_keys(metric)]
        elif metric == "fanFront":
            result = max_value_for_keys(api_result["STATS"][1], metric_to_keys(metric), 64)
        elif metric == "fanRear":
            result = max_value_for_keys(api_result["STATS"][1], metric_to_keys(metric), 64)
        elif metric == "pcbTemp":
            result = max_value_for_keys(api_result["STATS"][1], metric_to_keys(metric), 64)
        elif metric == "speed":
            result = api_result["SUMMARY"][0][metric_to_keys(metric)]
    except:
        result = metric_failure_default(metric)

    return result

### Argument functions.
def validate_argument_type(value):
    """Validator for type argument."""
    if value not in typesValid:
         raise argparse.ArgumentTypeError('"%s" is not a valid Antminer type.' % value)
    return value

def validate_argument_metric(value):
    """Validator for metric argument."""
    if value not in metricsValid:
         raise argparse.ArgumentTypeError('"%s" is not a valid metric.' % value)
    return value

def validate_argument_ip(value):
    """Validator for IP argument."""
    try:
        socket.inet_aton(value)
    except socket.error:
         raise argparse.ArgumentTypeError('"%s" is not a valid IP address.' % value)
    return value

def parse_arguments():
    """Initialize argument parser and validate."""
    parser = argparse.ArgumentParser(description="Query a Bitmain Antminer and return Zabbix compatible data.")
    parser.add_argument("-ep", "--enable-ping", help="Enable an initial ping check on host before query.", action="store_true")
    parser.add_argument("-p", "--port", help="Change the API port. (Default: 4028)", type=int, default=4028)
    parser.add_argument("-t", "--timeout", help="Set the timeout in seconds. (Default: 1)", type=int, default=1)
    parser.add_argument("-v", "--verbose", help="Increases the level of debugging verbosity.", action="count")
    parser.add_argument("type", help="The type of Antminer. Valid options: " + ", ".join(typesValid), type=validate_argument_type)
    parser.add_argument("ip", help="The IP address of the Antminer. eg: 192.168.0.42", type=validate_argument_ip)
    parser.add_argument("metric", help="The desired metric. Valid options: " + ", ".join(metricsValid), type=validate_argument_metric)
    return parser.parse_args()

### Network functions.
def api(host, port, command, timeout=1):
    """Performs an API connection to the Antminer and returns the data received."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((host, port))
    sock.send(json.dumps({"command": command}).encode())

    result = ""
    while True:
        buf = sock.recv(4096)
        if buf:
            result += buf.decode("utf-8")
        else:
            break

    data = str(result[:-1]) # Remove trailing new line.
    data = data.replace('}{','},{') # Fix for broken JSON in Antminer output.
    data = json.loads(data) # Parse string to dictionary.
    return data

def ping(host):
    """Pings the selected host and returns true or false depending on the result."""
    try:
        code = subprocess.call(["/bin/ping", "-c 1", "-W 1", host], stdout=open(os.devnull, "w"), stderr=subprocess.STDOUT)
        return True if code == 0 else False
    except:
        return False

### Main entrypoint.
# Parse arguments.
args = parse_arguments()
if args.verbose is not None and args.verbose >= 1:
    print(args)

# Check if host is online.
if args.enable_ping == True and ping(args.ip) == False:
    print("Antminer \"" + args.ip + "\" failed to respond to ping.")
    exit(1)

# Query API.
try:
    api_result = api(args.ip, args.port, metric_to_api_command(args.metric), timeout=args.timeout)
except Exception as exception:
    if args.verbose is not None and args.verbose >= 1:
        print(exception)
    print(metric_failure_default(args.metric))
    exit(1)

# Calculate final result.
result = calculate_value(args.type, args.metric, api_result)

# Return values.
print(result)

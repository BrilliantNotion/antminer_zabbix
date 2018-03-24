#!/usr/bin/env python3

import argparse
import json
import os
import socket
import subprocess
try:
    import redis
except ImportError:
    pass

### Constants. (See parse_arguments() for additional defaults.)
types_valid = ["NA", "A3", "D3", "L3+", "S9", "T9+"]
metrics_valid = ["averageSpeed", "averageSpeed5s", "chainFailures", "chipTemp", "errorRate", "fanFront", "fanRear", "pcbTemp", "speed"]

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

def metric_count_failures(result, base_key, count):
    """Counts the number of chain failures ("x") for the specified keys."""
    failures = 0
    base_keys = base_key.split(",")
    for base_key in base_keys:
        for i in range(1, count):
            key = base_key.replace("[i]", str(i))
            if key in result:
                failures += str(result[key]).count('x')
    return failures

def max_value_for_keys(result, base_key, count):
    """Finds the maximum value for the specified keys."""
    values = []
    base_keys = base_key.split(",")
    for base_key in base_keys:
        for i in range(1, count):
            key = base_key.replace("[i]", str(i))
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
    if value not in types_valid:
         raise argparse.ArgumentTypeError('"%s" is not a valid Antminer type.' % value)
    return value

def validate_argument_metric(value):
    """Validator for metric argument."""
    if value not in metrics_valid:
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
    parser.add_argument("-r", "--redis", help="Enable Redis caching for multiple subsequent API calls.", action="store_true")
    parser.add_argument("-rh", "--redis-host", help="Set the Redis host. (Default: localhost)", default="localhost")
    parser.add_argument("-rd", "--redis-database", help="Set the Redis database. (Default: 0)", type=int, default=0)
    parser.add_argument("-rp", "--redis-prefix", help="Set the Redis key prefix. (Default: \"antminerZabbix:\")", default="antminerZabbix:")
    parser.add_argument("-rt", "--redis-ttl", help="Set the Redis TTL in seconds. (Default: 30)", type=int, default=30)
    parser.add_argument("-t", "--timeout", help="Set the timeout in seconds. (Default: 1)", type=int, default=1)
    parser.add_argument("-v", "--verbose", help="Increases the level of debugging verbosity.", action="count")
    parser.add_argument("type", help="The type of Antminer. Valid options: " + ", ".join(types_valid), type=validate_argument_type)
    parser.add_argument("ip", help="The IP address of the Antminer. eg: 192.168.0.42", type=validate_argument_ip)
    parser.add_argument("metric", help="The desired metric. Valid options: " + ", ".join(metrics_valid), type=validate_argument_metric)
    return parser.parse_args()

### Network functions.
def api(host, port, command, timeout=1, use_redis=False, redis_ttl=30, redis_host="localhost", redis_database=0, redis_prefix=""):
    """Performs an API connection to the Antminer and returns the data received."""
    # Check for Redis cached instance.
    if use_redis:
        redis_key = redis_prefix+host+"-"+command
        r = redis.StrictRedis(host=redis_host, port=6379, db=redis_database)
        data = r.get(redis_key)
        if data != None:
            return api_data_decode(data)

    # Request data via API.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((host, port))
    sock.send(json.dumps({"command": command}).encode())

    # Gather result data.
    result = ""
    while True:
        buf = sock.recv(4096)
        if buf:
            result += buf.decode("utf-8")
        else:
            break

    # Cache to Redis.
    if use_redis:
        r.setex(redis_key, redis_ttl, result)

    return api_data_decode(result)

def api_data_decode(data):
    """Decodes the data from the API returning a dictionary."""
    try:
        dataout = data.decode("utf-8")
    except:
        dataout = str(data)
    dataout = dataout.strip(' \t\r\n\0') # Remove trailing new line.
    dataout = dataout.replace('}{','},{') # Fix for broken JSON in Antminer output.
    dataout = json.loads(dataout) # Parse string to dictionary.

    return dataout

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
    api_result = api(args.ip, args.port, metric_to_api_command(args.metric), timeout=args.timeout, use_redis=args.redis, redis_ttl=args.redis_ttl, redis_host=args.redis_host, redis_database=args.redis_database, redis_prefix=args.redis_prefix)
except Exception as exception:
    if args.verbose is not None and args.verbose >= 1:
        print(exception)
    print(metric_failure_default(args.metric))
    exit(1)

# Calculate final result.
result = calculate_value(args.type, args.metric, api_result)

# Return values.
print(result)

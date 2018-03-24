# antminer_zabbix.py
A Python script that allows Zabbix to interface with Bitmain Antminers.

Currently supported Antminer models: A3+, D3, L3+, S9, and T9+.

## Command Line Usage
From the command line, you can type `./antminer_zabbix.py -h` at any time to get online help.

The three required arguments are: TYPE, IP, and METRIC

- TYPE is the Antminer type: A3+, D3, L3+, S9, T9+, or NA (Not Applicable)
- IP is the IP of the Antminer. eg: 192.168.0.42
- METRIC is the value you want to query: averageSpeed, averageSpeed5s, chainFailures, chipTemp, errorRate, fanFront, fanRear, pcbTemp, speed

Usage Example:
```
$ ./antminer_zabbix.py S9 192.168.0.42 speed
13708.70
```

## Basic Usage
- Clone the Git repo or download the file `antminer_zabbix.py` from Github.
- Place the `antminer_zabbix.py` file in Zabbix's `externalscripts` folder. This may vary from system to system, but is commonly `/usr/lib/zabbix/externalscripts/`.
- Update the file ownership and permissions so that Zabbix can execute it. Note: You must give the script the execute permission! `chmod ugo+x antminer_zabbix.py`
- From the Zabbix configuration interface, create items that use antminer_zabbix.py as an external script.

![Zabbix Screenshot](zabbix-screenshot-01.png)

## Metric Descriptions
- averageSpeed (float): The calculated average hashrate of the Antminer in GH/s. Note: Due to a bug in some Antminer firmwares, this value is sometimes incorrectly reported as a positive value when hashing has completely stopped. It is recommended that averageSpeed5s be used instead.
- averageSpeed5s (float): The calculated average hashrate of the Antminer in GH/s during the last 5 seconds. 
- chainFailures (integer): The number of chain failures reported in the ASIC status. (Shown as "x" during failure.) 
- chipTemp (integer): The highest reported chip temperature in celsius.
- errorRate (float): The calculated error percentage provided by the Antminer. Note: Some Antminer firmwares sometimes report this value as > 100% when there are a high amount of errors.
- fanFront (integer): The RPM of the front fan.
- fanRear (integer): The RPM of the rear fan.
- pcbTemp (integer): The highest reported PCB board temperature in celsius.
- speed (float): An alias for averageSpeed5s.



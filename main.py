#!/usr/bin/python3
import patched_speedtest_cli.speedtest as speedtest
import argparse
import os
import time
import network_manager

# Parse input arguments.
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--num_tests",
                        default=10,
                        type=int,
                        help="Number of speed tests to perform.")
arg_parser.add_argument("--log_dir",
                        default="/var/log/speedtest",
                        type=str,
                        help="Number of speed tests to perform.")
arg_parser.add_argument("--source_address",
                        default=None,
                        type=str,
                        help="Source IP address used for testing."
                        "Used to distinguish which network interface."
                        "If not specified, it picks any one of interfaces.")
args = arg_parser.parse_args()

network_manager = network_manager.NetworkManager.get_instance(None, None, [])
print('Wi-Fi IP is ', network_manager.get_ethernet_ip())
print('Wi-Fi IP is ', network_manager.get_wifi_ip())

# The log file name will be the current time in seconds since unix epoch.
log_filepath = os.path.join(args.log_dir, str(time.time()))

# Do the actual speedtest.
print('Start speed testing.')
result_strs = []
s = speedtest.Speedtest(source_address=args.source_address)
s.get_servers()
result_strs.append(s.results.csv_header())
for _ in range(args.num_tests):
    s.get_best_server()
    s.download()
    s.upload()
    result_strs.append(s.results.csv())
print('Speed testing done.')

# Write result to file.
print('Saving result to ', log_filepath)
result_str = '\n'.join(result_strs)
with open(log_filepath, 'w') as f:
    f.write(result_str)
print('Done.')

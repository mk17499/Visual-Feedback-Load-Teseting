#!/bin/bash

# Set the server IP address and port
SERVER_IP="10.129.131.233"
SERVER_PORT="5000"

# Set the number of concurrent clients
NUM_CLIENTS=10

# Set the duration of the test in seconds
TEST_DURATION=60

# Start tcpdump to capture packets
tcpdump -i any udp port $SERVER_PORT -w netperf_packets.pcap &

# Loop to start netperf clients
for ((i=1; i<=$NUM_CLIENTS; i++)); do
    netperf -H $SERVER_IP -p $SERVER_PORT -l $TEST_DURATION -t UDP_STREAM -- -P 0 &
done

# Wait for all clients to finish
wait

# Stop tcpdump
pkill tcpdump

import socket
import time

# Configuration
server_ip = '127.0.0.1'
server_port = 5201
packet_size = 1024
delay_between_packets = 0.05  # 50 milliseconds

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Packet data
message = b'A' * packet_size

try:
    while True:
        sock.sendto(message, (server_ip, server_port))
        time.sleep(delay_between_packets)
except KeyboardInterrupt:
    print("Stopped by user")
finally:
    sock.close()

import socket
import json
import threading
import time
import random
import psutil
import resource
import signal
import sys
import statistics

# Increase the file descriptor limit
soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (hard_limit, hard_limit))

# Dictionary to store port information for each thread
port_info_dict = {}
total_sent_packets = 0
total_received_packets = 0
total_join_time = []  # List to store join time for each thread
total_sent_bytes = 0
total_received_bytes = 0
clients_in_rooms = {}
terminate_event = threading.Event()

# Function to send audio data over UDP
def send_audio_data(audio_socket, audio_port, audio_file, ack_socket, ack_port, thread_name):
    try:
        start_time = time.time()
        with open(audio_file, "rb") as f:
            while not terminate_event.is_set():
                f.seek(0)  # Rewind the file to the beginning
                while not terminate_event.is_set():
                    chunk = f.read(1024)  # Read 1024 bytes of audio data
                    if not chunk:
                        break  # End of file
                    packet = thread_name.encode() + b'|' + chunk  # Include sender's identity in the packet
                    audio_socket.sendto(packet, ('127.0.0.1', int(audio_port)))  # Send audio data to the data forwarding server
                    port_info_dict[thread_name]["total_sent_packets"] += 1
                    global total_sent_packets, total_sent_bytes
                    total_sent_packets += 1
                    total_sent_bytes += len(chunk)
                    
                    # Wait for ACK
                    ack_socket.settimeout(4)  # Set timeout for ACK reception
                    try:
                        ack, _ = ack_socket.recvfrom(1024)
                        if ack.decode() == "ACK":
                            port_info_dict[thread_name]["total_received_acks"] += 1
                            total_received_packets += 1
                    except socket.timeout:
                        pass
                    
                    time.sleep(0.05)  # Adjust sleep time as needed
                if time.time() - start_time >= 15:
                    break
    except Exception as e:
        print(f"Exception in audio sending thread: {e}")

# Function to receive audio data over UDP
def receive_audio_data(audio_socket, ack_socket, ack_port, duration, thread_name):
    start_time = time.time()
    while time.time() - start_time <= duration and not terminate_event.is_set():
        data, sender_address = audio_socket.recvfrom(2048)  # Adjust buffer size as needed
        sender_name, chunk = data.split(b'|', 1)
        sender_name = sender_name.decode()
        port_info_dict[thread_name]["total_received_packets"] += 1
        global total_received_bytes
        total_received_bytes += len(chunk)
        
        # Send ACK back to sender
        ack_socket.sendto(b"ACK", (sender_address[0], int(ack_port)))

# Function to send data to the server
def send_data_to_server(request, room_name, room_pass, port):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Connect the socket to the server address
    server_address = ('127.0.0.1', port)
    sock.connect(server_address)

    try:
        # Join request, room name, and room pass into a single string
        packet_data = " ".join([request, room_name, room_pass])
        
        # Convert packet data to bytes
        packet_bytes = packet_data.encode()

        # Calculate length of packet data and convert it to bytes (4 bytes)
        len_bytes = len(packet_bytes).to_bytes(4, byteorder='big')

        # Construct the packet: length (4 bytes) + packet data
        packet = len_bytes + packet_bytes

        # Record the time before sending the request
        start_time = time.time()

        # Send the packet to the server
        sock.sendall(packet)

        # Receive response from the server
        response = sock.recv(4096)

        # Record the time after receiving the response
        end_time = time.time()

        # Calculate the time taken for the join request
        join_time = end_time - start_time
        total_join_time.append(join_time)

        response_obj = json.loads(response)

        if response_obj["status"] == "success":
            # print("Operation successful")
            audio_port = int(response_obj["ports_info"]["audio_port"])  # Ensure ports are integers
            ack_port = int(response_obj["ports_info"]["ack_port"])  # Ensure ports are integers
            rr_port = int(response_obj["ports_info"]["rr_port"])  # Ensure ports are integers
            
            port_info_dict[threading.current_thread().name] = {
                "audio_port": audio_port,
                "ack_port": ack_port,
                "rr_port": rr_port,
                "total_sent_packets": 0,  # Initialize total_sent_packets
                "total_received_packets": 0,  # Initialize total_received_packets
                "total_received_acks": 0  # Initialize total_received_acks
            }
            return audio_port, ack_port, rr_port  

        else:
            print("Operation failed:", response_obj["message"])
            
    finally:
        sock.close()

# Function to send dummy packets
def send_dummy_packets(audio_socket, ack_socket, rr_socket, audio_port, ack_port, rr_port):
    audio_dummy = "audio_dummy"
    ack_dummy = "ack_dummy"
    rr_dummy = "rr_dummy"
    
    audio_dummy_packet = audio_dummy.encode()
    ack_dummy_packet = ack_dummy.encode()
    rr_dummy_packet = rr_dummy.encode()
    
    # Send dummy packets
    audio_socket.sendto(audio_dummy_packet, ('127.0.0.1', int(audio_port)))
    ack_socket.sendto(ack_dummy_packet, ('127.0.0.1', int(ack_port)))
    rr_socket.sendto(rr_dummy_packet, ('127.0.0.1', int(rr_port)))

# Function to create a client thread
def create_client(request, room_name, room_pass, port, is_join_client):
    try:
        audio_port, ack_port, rr_port = send_data_to_server(request, room_name, room_pass, 8080)
        
        audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rr_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        audio_socket.bind(('127.0.0.1', 0))  
        ack_socket.bind(('127.0.0.1', 0))
        rr_socket.bind(('127.0.0.1', 0))
        
        send_dummy_packets(audio_socket, ack_socket, rr_socket, audio_port, ack_port, rr_port)
        
        port_info_dict[threading.current_thread().name] = {
            "audio_port": audio_port,
            "ack_port": ack_port,
            "rr_port": rr_port,
            "total_sent_packets": 0,  # Initialize total_sent_packets
            "total_received_packets": 0,  # Initialize total_received_packets
            "total_received_acks": 0  # Initialize total_received_acks
        }
        if room_name in clients_in_rooms:
            clients_in_rooms[room_name].append(threading.current_thread().name)
        else:
            clients_in_rooms[room_name] = [threading.current_thread().name]
        
        if is_join_client:
            audio_file = "audio.pcm"  
            send_audio_data(audio_socket, audio_port, audio_file, ack_socket, ack_port, threading.current_thread().name)
        else:
            receive_audio_data(audio_socket, ack_socket, ack_port, 15, threading.current_thread().name)

        # print(f"Thread {threading.current_thread().name} finished its task.")

    except Exception as e:
        print(f"Exception in thread {threading.current_thread().name} : {e}")

# Function to monitor CPU and memory utilization
def monitor_system(interval):
    with open('system_monitoring.txt', 'w') as txtfile:
        while not terminate_event.is_set():
            timestamp = time.time()
            cpu_percent = psutil.cpu_percent(interval=interval)
            memory_percent = psutil.virtual_memory().percent
            
            # Write to file or print to console
            # txtfile.write(f"Timestamp: {timestamp}, CPU Percent: {cpu_percent}%, Memory Percent: {memory_percent}%\n")
            print("Timestamp:", timestamp, "CPU Percent:", cpu_percent, "Memory Percent:", memory_percent)
            
            # Check if termination event is set
            if terminate_event.is_set():
                break
            
            # Sleep for specified interval
            # time.sleep(interval)

def signal_handler(sig, frame):
    end_time = time.time()
    total_time = end_time - start_time
    print("Total Time in Load Testing:", total_time)
    print("Average Join Time:", sum(total_join_time) / len(total_join_time) if total_join_time else 0)
    print("Total Packets sent =", total_sent_packets)
    print("Total packets Received =", total_received_packets)
    
    # Calculate total number of clients across all rooms
    total_clients = sum(len(clients) for clients in clients_in_rooms.values())
    
    # List to store packet loss percentages for all rooms
    packet_loss_percentages = []
    
    # Calculate packet loss percentage for each room
    for room_name, clients in clients_in_rooms.items():
        clients_in_room = len(clients)
        packets_sent_in_room = 0
        packets_received_in_room = 0
        for client in clients:
            packets_sent_in_room += port_info_dict[client]["total_sent_packets"]
            packets_received_in_room += port_info_dict[client]["total_received_acks"]
        
        # Calculate packet loss percentage for the room using the provided function
        packet_loss_percentage = ((packets_sent_in_room - packets_received_in_room) / packets_sent_in_room) * 100 if packets_sent_in_room else 0
        packet_loss_percentages.append(packet_loss_percentage)
    
    # Calculate and print average packet loss percentage and standard deviation
    average_packet_loss_percentage = statistics.mean(packet_loss_percentages)
    standard_deviation = statistics.stdev(packet_loss_percentages) if len(packet_loss_percentages) > 1 else 0
    print("Average Packet Loss Percentage:", average_packet_loss_percentage)
    print("Standard Deviation of Packet Loss Percentage:", standard_deviation)

    sent_throughput = (total_sent_bytes * 8) / total_time  # in bps
    received_throughput = (total_received_bytes * 8) / total_time  # in bps
    print("Sent Throughput (bps):", sent_throughput)
    print("Received Throughput (bps):", received_throughput)

    terminate_event.set()
    sys.exit(0)

def calculate_packet_loss_percentage(total_clients, clients_in_room):
    packet_loss_percentage = 0
    for i in range(clients_in_room):
        loss_probability = 1 - (clients_in_room / (total_clients - i))
        packet_loss_percentage += loss_probability * (1 / clients_in_room)
    return packet_loss_percentage * 100

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

# Example usage with parameters
if __name__ == "__main__":
    num_create_clients = 30  # Number of clients to send "create" requests
    num_join_clients = 400    # Number of clients to send "join" requests
    starting_port = 8082    # Starting port number for clients

    create_threads = []
    for i in range(num_create_clients):
        create_thread = threading.Thread(target=create_client, args=("Create", f"example_room{i+1}", f"example_password{i+1}", starting_port + i, False))
        create_thread.name = f"Create_Client_{i+1}"  
        create_threads.append(create_thread)
    
    join_threads = []
    for i in range(num_join_clients):
        x = random.randint(1, num_create_clients)
        join_thread = threading.Thread(target=create_client, args=("Join", f"example_room{x}", f"example_password{x}", starting_port + num_create_clients + i, True))
        join_thread.name = f"Join_Client_{i+1}"  
        join_threads.append(join_thread)

    # Start monitoring system
    monitoring_thread = threading.Thread(target=monitor_system, args=(3,))
    monitoring_thread.start()

    start_time = time.time()

    auto_terminate_time = 30  # time in seconds
    threading.Timer(auto_terminate_time, signal.raise_signal, args=[signal.SIGINT]).start()

    for thread in create_threads:
        thread.start()
    
    time.sleep(1.7)
    
    for thread in join_threads:
        thread.start()

    for thread in create_threads:
        thread.join()

    for thread in join_threads:
        thread.join()
    
    terminate_event.set()
    monitoring_thread.join()

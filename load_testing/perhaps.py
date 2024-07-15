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
total_clients_joined = 0
total_join_time = []  # List to store join time for each thread
total_sent_bytes = 0
total_received_bytes = 0
clients_in_rooms = {}
terminate_event = threading.Event()
start_time_of_client = {}
client_activity = {}

# Dictionary to store client activity timestamps
client_activity = {}

# Function to send audio data over UDP
def send_audio_data(audio_socket, audio_port, audio_file, thread_name):
    try:
        start_time1 = time.time()
        client_activity[thread_name]["start_sending_time"] = start_time1
        with open(audio_file, "rb") as f:
            while not terminate_event.is_set():
                f.seek(0)  # Rewind the file to the beginning
                while not terminate_event.is_set():
                    chunk = f.read(1024)  # Read 1024 bytes of audio data
                    if not chunk:
                        break  # End of file
                    audio_socket.sendto(chunk, ('127.0.0.1', int(audio_port)))  # Send audio data to the data forwarding server
                    port_info_dict[thread_name]["total_sent_packets"] += 1
                    global total_sent_packets, total_sent_bytes
                    total_sent_packets += 1
                    total_sent_bytes += len(chunk)
                    time.sleep(0.05)  # Adjust sleep time as needed
                if time.time() - start_time1 >= 15:
                    break
        client_activity[thread_name]["stop_sending_time"] = time.time()
    except Exception as e:
        print(f"Exception in audio sending thread: {e}")

# Function to receive audio data over UDP
def receive_audio_data(audio_socket, duration, thread_name):
    start_time2 = time.time()
    while time.time() - start_time2 <= duration and not terminate_event.is_set():
        data, _ = audio_socket.recvfrom(1024)  # Adjust buffer size as needed
        global total_received_packets, total_received_bytes
        port_info_dict[thread_name]["total_received_packets"] += 1
        total_received_packets += 1
        total_received_bytes += len(data)

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
        start_time3 = time.time()

        # Send the packet to the server
        sock.sendall(packet)

        # Receive response from the server
        response = sock.recv(4096)

        # Record the time after receiving the response
        end_time = time.time()

        # Calculate the time taken for the join request
        join_time = end_time - start_time3
        total_join_time.append(join_time)

        response_obj = json.loads(response)

        if response_obj["status"] == "success":
            audio_port = response_obj["ports_info"]["audio_port"]
            ack_port = response_obj["ports_info"]["ack_port"]
            rr_port = response_obj["ports_info"]["rr_port"]
            
            port_info_dict[threading.current_thread().name] = {
                "audio_port": audio_port,
                "ack_port": ack_port,
                "rr_port": rr_port,
                "total_sent_packets": 0,  # Initialize total_sent_packets
                "total_received_packets": 0  # Initialize total_received_packets
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
            "total_received_packets": 0  # Initialize total_received_packets
        }
        if room_name in clients_in_rooms:
            clients_in_rooms[room_name].append(threading.current_thread().name)
        else:
            clients_in_rooms[room_name] = [threading.current_thread().name]
        
        client_activity[threading.current_thread().name] = {
            "join_time": time.time(),
            "start_sending_time": None,
            "stop_sending_time": None
        }

        if is_join_client:
            audio_file = "audio.pcm"  
            global total_clients_joined
            total_clients_joined += 1
            global start_time_of_client
            start_time_of_client[threading.current_thread().name] = time.time()
            send_audio_data(audio_socket, audio_port, audio_file, threading.current_thread().name)
        else:
            receive_audio_data(audio_socket, 40, threading.current_thread().name)

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
            txtfile.write(f"Timestamp: {timestamp}, CPU Percent: {cpu_percent}%, Memory Percent: {memory_percent}%\n")
            
            if terminate_event.is_set():
                break

def signal_handler(sig, frame):
    end_time = time.time()
    total_time = end_time - start_time
    print("Total Number of Rooms : ",num_create_clients)
    print("Total Number of Clients : ",num_join_clients)
    print("Total Time in Load Testing:", total_time)
    print("Average Join Time:", sum(total_join_time) / len(total_join_time) if total_join_time else 0)
    
    # Calculate total number of clients across all rooms
    total_clients = sum(len(clients) for clients in clients_in_rooms.values())
    
    # List to store packet loss percentages for all rooms
    packet_loss_percentages = []
    all_packets = 0
    all_packets_rcv = 0
    # Calculate packet loss percentage for each room
    for room_name, clients in clients_in_rooms.items():
        clients_in_room = len(clients)
        packets_sent_in_room = 0
        packets_received_in_room = 0
        for client in clients:
            packets_sent_in_room += port_info_dict[client]["total_sent_packets"]
            packets_received_in_room += port_info_dict[client]["total_received_packets"]
        all_packets += packets_sent_in_room
        all_packets_rcv += packets_received_in_room
        packet_loss_percentage = (packets_sent_in_room - packets_received_in_room) / packets_sent_in_room * 100 if packets_sent_in_room else 0
        packet_loss_percentages.append(packet_loss_percentage)
    
    average_packet_loss_percentage = sum(packet_loss_percentages) / len(packet_loss_percentages) if packet_loss_percentages else 0
    std_dev_packet_loss_percentage = statistics.stdev(packet_loss_percentages) if len(packet_loss_percentages) > 1 else 0
    print("Average Packet Loss Percentage:", average_packet_loss_percentage)
    print("Standard Deviation of Packet Loss Percentage:", std_dev_packet_loss_percentage)
    global start_time_of_client
    time_list = list(start_time_of_client.items())
    second_elements = [pair[1] for pair in time_list]
    difference = max(second_elements) - min(second_elements)
    print("All packets = ", all_packets, " total_sent_packets = ", total_sent_packets)
    print("Total Packets Received: ", all_packets_rcv)
    print("Time difference b/w first and last client = ", difference)
    # print("Total packets sent in this time interval = ", (difference / 0.05) * len(second_elements))
    # print("Packets lost according to stats = ", ((average_packet_loss_percentage/100) * total_sent_packets) + ((std_dev_packet_loss_percentage/100) * total_sent_packets))
    
    # Calculate throughput and standard deviation
    client_throughputs = []
    avg_active_time = 0
    for client, times in client_activity.items():
        if times["start_sending_time"] and times["stop_sending_time"]:
            active_time = times["stop_sending_time"] - times["start_sending_time"]
            avg_active_time += active_time
            sent_bytes = port_info_dict[client]["total_sent_packets"] * 1024  # assuming each packet is 1024 bytes
            throughput = (sent_bytes * 8) / (active_time) / (1024 * 1024)  # throughput in Mbps
            client_throughputs.append(throughput)
    avg_active_time = avg_active_time/num_join_clients
    print("avergae active time: ",avg_active_time)
    if client_throughputs:
        average_throughput = sum(client_throughputs) / len(client_throughputs)
        std_dev_throughput = statistics.stdev(client_throughputs) if len(client_throughputs) > 1 else 0
    else:
        average_throughput = 0
        std_dev_throughput = 0
    
    packet_size = 1024  # bytes
    packets_per_second = 1 / 0.05  # packets per second
    duration = avg_active_time  # seconds

    total_packets_per_client = duration * packets_per_second
    total_bytes_per_client = total_packets_per_client * packet_size

    total_bytes = total_bytes_per_client * num_join_clients
    total_bits = total_bytes * 8  # convert bytes to bits

    throughput_mbps = (total_bits / duration) / (1024 * 1024)
    print("Throughput of the Data Forwarding Server (Mbps):", average_throughput*num_join_clients)
    print("Ideal Throughput for ",num_join_clients," : ",throughput_mbps)
    
    terminate_event.set()
    sys.exit(0)


# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    num_create_clients = 10  # Number of clients to send "create" requests
    num_join_clients = 300  # Number of clients to send "join" requests
    starting_port = 8082    # Starting port number for clients

    start_time = time.time()

    auto_terminate_time = 60  # time in seconds
    threading.Timer(auto_terminate_time, signal.raise_signal, args=[signal.SIGINT]).start()
    create_threads = []
    for i in range(num_create_clients):
        create_thread = threading.Thread(target=create_client, args=("Create", f"example_room{i+1}", f"example_password{i+1}", starting_port + i, False))
        create_thread.name = f"Create_Client_{i+1}"  
        create_threads.append(create_thread)
    
    join_threads = []
    for i in range(num_join_clients):
        x = random.randint(1, num_create_clients)
        join_thread = threading.Thread(target=create_client, args=("Join", f"example_room{x}", f"example_password{x}", starting_port + num_create_clients + x, True))
        join_thread.name = f"Join_Client_{i+1}"  
        join_threads.append(join_thread)

    # Start monitoring system
    monitoring_thread = threading.Thread(target=monitor_system, args=(3,))
    monitoring_thread.start()

    for thread in create_threads:
        thread.start()
    
    time.sleep(5)
    
    for thread in join_threads:
        thread.start()

    for thread in create_threads:
        thread.join()

    for thread in join_threads:
        thread.join()
    
    terminate_event.set()
    monitoring_thread.join()

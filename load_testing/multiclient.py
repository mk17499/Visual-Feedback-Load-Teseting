import socket
import json
import threading
import time
import random

# Dictionary to store port information for each thread
port_info_dict = {}
# Function to send audio data over UDP
def send_audio_data(audio_socket, audio_port, audio_file):
    try:
        start_time = time.time()
        while True:
            with open(audio_file, "rb") as f:
                # index = 1
                while True:
                    chunk = f.read(1024)  # Read 1024 bytes of audio data
                    if not chunk:
                        break  # End of file
                    audio_socket.sendto(chunk, ('127.0.0.1', int(audio_port)))  # Send audio data to the data forwarding server
                    # print(index,") Sent audio data, packet size",len(chunk))
                    # index = index+1
                    time.sleep(0.01)  # Adjust sleep time as needed
                    # print()
                    if time.time() - start_time >= 15:
                        print("************************Times UP !!***************************")
                        return    
                    
            print("Audio sending completed.")
    except Exception as e:
        print(f"Exception in audio sending thread: {e}")

def receive_audio_data(audio_socket):
    index = 1
    while True:
        data, _ = audio_socket.recvfrom(1024)  # Adjust buffer size as needed
        # print(index,") Received audio data, packet size: ", len(data))
        index = index + 1


def send_data_to_server(request, room_name, room_pass, port):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Connect the socket to the server address
    server_address = ('127.0.0.1', port)
    # print('Connecting to {} port {}'.format(*server_address))
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

        # Send the packet to the server
        sock.sendall(packet)

        # Receive response from the server (if any)
        response = sock.recv(4096)
        print(response)
        # response_json = response.decode('utf-8')
        response_obj = json.loads(response)

        # Check the status of the response
        if response_obj["status"] == "success":
            print("Operation successful")
            # Access the port information
            audio_port = response_obj["ports_info"]["audio_port"]
            ack_port = response_obj["ports_info"]["ack_port"]
            rr_port = response_obj["ports_info"]["rr_port"]
            # print("Audio Port:", audio_port)
            # print("Ack Port:", ack_port)
            # print("RR Port:", rr_port)
            
            # Store port information in the port_info_dict
            port_info_dict[threading.current_thread().name] = {
                "audio_port": audio_port,
                "ack_port": ack_port,
                "rr_port": rr_port
            }
            return audio_port, ack_port, rr_port  # Return port information

        else:
            print("Operation failed:", response_obj["message"])
            
    finally:
        # print('Closing socket')
        # print()
        sock.close()

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
    # print("Dummy data sent successfully")



# Function to create a client thread
def create_client(request, room_name, room_pass, port,is_join_client):
    try:
        audio_port, ack_port, rr_port = send_data_to_server(request, room_name, room_pass, 8080)
        # Store port information in the local data structure (if needed)
        # You can access the port_info_dict to retrieve this information later
        # print(f"Thread {threading.current_thread().name} - Audio Port: {audio_port}, Ack Port: {ack_port}, RR Port: {rr_port}")
        audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rr_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Bind the sockets to their respective ports
        audio_socket.bind(('127.0.0.1', 0))  # 0 for a random available port
        ack_socket.bind(('127.0.0.1', 0))
        rr_socket.bind(('127.0.0.1', 0))
        
        # Send dummy packets from each socket
        send_dummy_packets(audio_socket, ack_socket, rr_socket, audio_port, ack_port, rr_port)
        
        # Store the sockets in a dictionary or list for later use if needed
        port_info_dict[threading.current_thread().name] = {
                    "audio_port": audio_port,
                    "ack_port": ack_port,
                    "rr_port": rr_port
                }
        # If this client is the sender, start sending audio data
        if is_join_client:
        # if threading.current_thread().name == "Create_Client_1":
            audio_file = "audio.pcm"  # Path to the PCM audio file
            send_audio_data(audio_socket, audio_port, audio_file)
        else:
            # Start receiving audio data
            receive_audio_data(audio_socket)

        print(f"Thread {threading.current_thread().name} finished its task.")

    except Exception as e:
        print(f"Exception in thread {threading.current_thread().name} : {e}")
    

# Example usage with parameters
if __name__ == "__main__":
    num_create_clients = 1  # Number of clients to send "create" requests
    num_join_clients = 1    # Number of clients to send "join" requests
    starting_port = 8082    # Starting port number for clients

    # Create threads for create client requests
    create_threads = []
    for i in range(num_create_clients):
        create_thread = threading.Thread(target=create_client, args=("Create", f"example_room{i+1}", f"example_password{i+1}", starting_port + i,False))
        create_thread.name = f"Create_Client_{i+1}"  # Assign a unique name to each create client thread
        create_threads.append(create_thread)

    # Create threads for join client requests
    join_threads = []
    for i in range(num_join_clients):
        x = random.randint(1,num_create_clients)
        join_thread = threading.Thread(target=create_client, args=("Join", f"example_room{x}", f"example_password{x}", starting_port + num_create_clients + i,True))
        join_thread.name = f"Join_Client_{i+1}"  # Assign a unique name to each join client thread
        join_threads.append(join_thread)

    # Start the threads for create clients
    for thread in create_threads:
        thread.start()

    # Start the threads for join clients after a delay
    time.sleep(1.7)
    for thread in join_threads:
        thread.start()

    time.sleep(1)
    # Wait for all threads to finish
    print("Joining the threads")
    for thread in create_threads:
        thread.join()
    print("All create threads closed")
    for thread in join_threads:
        thread.join()
    print("All join threads closed")
    # Print the port information stored in port_info_dict
    print("Port Information:")
    for item in port_info_dict:
        print(item,port_info_dict[item])

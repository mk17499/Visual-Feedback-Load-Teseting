import socket
import json

def send_data_to_server(request, room_name, room_pass):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Connect the socket to the server address
    server_address = ('127.0.0.1', 8080)
    print('Connecting to {} port {}'.format(*server_address))
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
        # response = sock.recv(4096)
        # # print(response.decode('ascii'))
        # hex_string = response
        # # ascii_string = hex_string.decode('ascii', errors='ignore')
        # print(response)
        response = sock.recv(4096)
        response_json = response.decode('utf-8')
        response_obj = json.loads(response_json)

        # Check the status of the response
        if response_obj["status"] == "success":
            print("Operation successful")
            # Access the port information
            audio_port = response_obj["ports_info"]["audio_port"]
            ack_port = response_obj["ports_info"]["ack_port"]
            rr_port = response_obj["ports_info"]["rr_port"]
            print("Audio Port:", audio_port)
            print("Ack Port:", ack_port)
            print("RR Port:", rr_port)
        else:
            print("Operation failed:", response_obj["message"])
            
    finally:
        print('Closing socket')
        sock.close()


# Example usage
if __name__ == "__main__":
    request = "Create"  # or "Join" depending on the scenario
    room_name = "example_room2"
    room_pass = "example_password"
    send_data_to_server(request, room_name, room_pass)
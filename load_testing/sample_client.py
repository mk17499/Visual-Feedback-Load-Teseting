import socket

def send_get_request(host, port):
    # Create a socket object
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Connect to the server
        s.connect((host, port))
        
        # Prepare the HTTP GET request
        request = "GET / HTTP/1.1\r\nHost: {}\r\n\r\n".format(host)
        
        # Send the HTTP GET request
        s.sendall(request.encode())
        
        # Receive the response from the server
        response = s.recv(4096)
        
        # Print the response
        print("Response from server:")
        print(response.decode())

if __name__ == "__main__":
    # Replace 'example.com' and 80 with your server's hostname and port
    host = '106.208.67.220'
    port = 7940
    
    send_get_request(host, port)

import socket
import select
import json
from threading import Thread
from queue import Queue
import signal
# import firebase_admin
# from firebase_admin import credentials
# from pyfcm import FCMNotification


# Initialize FCM (Firebase Cloud Messaging)
# sender= "53030408402"
# server_key = "AAAADFjb0NI:APA91bEYJSmIIO2eJDTWmzpXnnsJcyH4O0rk038tsbAtrJH4pY4IE8NlD68rDXjK2JiuTUQ7DwVjMtdxEgK1TwPP03-eBIxuXzHXzWPDbMAw-v4c5CIu6Ut20vLzTBDrkMpV46Axif_-" #server key of cloud messaging api (legacy)
# push_service = FCMNotification(api_key=server_key)

def handle_sigpipe(signum, frame):
    print("SIGPIPE received. Ignoring.")

signal.signal(signal.SIGPIPE, handle_sigpipe)

class Server:
    def __init__(self, host, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Set the reuse option
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        self.epoll = select.epoll()
        self.epoll.register(self.server_socket.fileno(), select.EPOLLIN)
        self.connections = {}
        self.table = {}
        # Create a dictionary to store FCM tokens associated with roomName and roomPass
        self.fcm_tokens = {}

    def run(self):
        while True:
            events = self.epoll.poll()  # Wait for events

            for fileno, event in events:
                if fileno == self.server_socket.fileno():
                    client_socket, client_address = self.server_socket.accept()
                    print(f"New connection from {client_address}")
                    client_socket.setblocking(0)
                    self.epoll.register(client_socket.fileno(), select.EPOLLIN)
                    #self.connections[client_socket.fileno()] = client_socket
                    self.connections[client_socket.fileno()] = (client_socket, client_address)
                elif event & select.EPOLLIN:
                    client_socket, client_address = self.connections[fileno]
                    try:
                        received_data = client_socket.recv(1024)
                        print(f"Received data length: {len(received_data)}")  # Add this line
                        whatdata = received_data.decode('utf-8')
                        print("received_data:", whatdata)
                        if not received_data:
                            print(f"Connection closed by {client_address}")
                            self.epoll.unregister(fileno)
                            del self.connections[fileno]
                            client_socket.close()
                            
                        else:
                            self.handle_connection(received_data, client_address, client_socket)
                    
                    except ConnectionResetError:
                        print(f"Connection reset by {client_address}")
                        self.epoll.unregister(fileno)
                        del self.connections[fileno]
                        client_socket.close()
    
                    except Exception as e:
                        print(f"An error occurred: {e}")

    def handle_connection(self, received_data, client_address, client_socket):
        # print("Received data in bytes:", end=' ')
        # for byte_value in received_data:
        #     print(byte_value, end=' ')
        print()  # Add a newline for better formatting



#-------------------implementation of FCM token---------------------------------------------------------------------
        
        # Find the delimiter (e.g., '|') to split the data
        delimiter = b'|'  # Use the delimiter without spaces
        delimiter_index = received_data.find(delimiter)
        if delimiter_index != -1:
            # Extract the FCM token and data
            data = received_data[:delimiter_index]  # Data comes before the delimiter
            token = received_data[delimiter_index + len(b'|'):].decode("utf-8").strip()  # Token comes after the delimiter
            print("Received token:", token)
        else:
            # Data does not contain a token, handle as needed
            data = received_data
            token = None
            print("came here")

#-------------------implementation of FCM token---------------------------------------------------------------------

        #remove the 4 bytes before splitting
        data = data [4:len(data)]
        data =  data.decode('utf-8')
        data = data.split()
        roomName = data[1]
        if (data[0] != "Endcall"): #because endcall request doesn't send pwd
            passwd = data[2]
        print(data)
        # client_address contains IP and Port.... ('10.96.24.137', 47714)
        print("Client addr:", client_address)

        print("Request received: ", data[0])
        four_bytes = b'1234' #for adding extra 4 bytes ...not neccessary as if converted to string hacker can see the content

        if data[0] == "Create": #Check if the request is create
            #check if room_id and pswd already exist
            if roomName in self.table.keys() and self.table [roomName][0][1] == passwd:
                port = 65536
                port_byte = port.to_bytes(4, 'big')
                print("Room already exists")
                ports_info = port_byte + port_byte + port_byte
                msg_bytes = four_bytes + ports_info
                #send(self.request, port_byte, encode= False) 
                client_socket.send(msg_bytes) 
            else:
                self.table[roomName] = client_address #map the room_id along with it's host (IP and port)

                self.table[roomName] = [self.table[roomName], passwd] #add password to table

                print("Active rooms = ", self.table)

                #send client's info to data forwarder by calling the IPC...for this create a new thread
                client_info = data + list(client_address) #client_info = ['Request type', 'room id', 'password', 'client ip', client port]
                #print("Client_info= ", client_info)

                ports_info = self.DIPC(client_info) 
                    # ports_info:  ('audio', 'ack', 'port')....ports_info:  ('52602', '46326', '45666')
                #Add the ports_info to the table

                if ports_info:
                    print("ports info inside 'create' condition", ports_info)
                    self.table[roomName] = [self.table[roomName], ports_info]
                    # print(self.table[roomName])
                    response = {
                        "status": "success",
                        "message": "Room created",
                        "ports_info": {
                            "audio_port": ports_info[0],
                            "ack_port": ports_info[1],
                            "rr_port": ports_info[2]
                        }
                    }
                else:
                    response = {
                        "status": "error",
                        "message": "Failed to obtain ports info"
                    }
            #Send the response to the client
            response_json = json.dumps(response)
            client_socket.send(response_json.encode())    

#-------------------implementation of FCM token---------------------------------------------------------------------

            # if the roomName and passwd is sam, add the extracted token to the fcm token list
            # if roomName == "sam" and passwd == "sam":
            #     self.fcm_tokens[(roomName, passwd)] = token
            #     print("tokens:", self.fcm_tokens)

#-------------------implementation of FCM token---------------------------------------------------------------------


        elif data[0] == "Join":
            print("Join Request for: ", roomName)
            if roomName in self.table.keys() and self.table[roomName][0][1] == passwd:
                # Check if room exists

                # Send client's info to data forwarder by calling the IPC
                client_info = roomName
                print(self.table[roomName][1])
                ports_info = self.table[roomName][1]

                # Prepare response in JSON format
                response = {
                    "status": "success",
                    "message": f"Joined room '{roomName}' successfully",
                    "ports_info": {
                        "audio_port": ports_info[0],
                        "ack_port": ports_info[1],
                        "rr_port": ports_info[2]
                    }
                }

                response_json = json.dumps(response)
                client_socket.send(response_json.encode())  

                # Check if the room has an associated token
                # if (roomName, passwd) in self.fcm_tokens:
                #     # Send a notification to the FCM token associated with this room
                #     registration_id = self.fcm_tokens[(roomName, passwd)]
                #     message_data = {
                #         "Nick": "Mario",
                #         "body": "great match!",
                #         "Room": roomName
                #     }
                #     result = push_service.notify_single_device(
                #         registration_id=registration_id,
                #         data_message=message_data
                #     )
                #     print("Notification sent to FCM token:", registration_id)
                #     print("FCM Notification Result:", result)

            else:
                # Room does not exist or password is incorrect
                port = 65536  # Send a wrong port number specifying that room does not exist or password is wrong
                # port_byte = port.to_bytes(4, 'big')
                msg_bytes = four_bytes + port_byte
                client_socket.send(msg_bytes)


#-------------------implementation of FCM token---------------------------------------------------------------------

        elif data[0] == "Endcall": #room_id needs to be send too when pressing end call button
            #check if self.table.keys is empty

            #check if room is active
            if roomName in self.table.keys():
                client_info = data #client info = ['room id']
            else:
                print("Room not active")
                #and send error msg back to client
                port = 65536   #Send a wrong port number specifying that room non-existing or passwd wrong.
                port_byte = port.to_bytes(4, 'big')
                msg_bytes = four_bytes + port_byte
                client_socket.send(msg_bytes)

                return #don't continue further down
                  

            #check if the client is the host
            ip_port = client_address #extract the ip and port
            if ip_port == self.table[roomName][0][0]: #check if the ip and port matches with the one stored in table .....Surround with try catch because if host ends first and later other participant tries to end it gives error....or this can be solved if the leave request is directed to data forwarder
                #check if tokens exist
                passwd = "sam" #this is temporary
                if (roomName, passwd) in self.fcm_tokens:
                    print()
                    print("Available tokens:", self.fcm_tokens)
                else:
                    #if it is a host forward to data forwarder
                    self.IPC(client_info)
                    #And clear the room
                    del self.table[roomName]
                if not self.table:
                    print("No active rooms currently")
                else:
                    print("Active rooms after clearing = ", self.table)

            else:           
                #else send error 
                print("You are not the host") #temp line


    def IPC(self, client_info): #This function deals with the inter process communication between control server and data forwarder server
        queue = Queue()

        ports = {}
        self.s = socket.socket()
        port = 5000  # Port where the data forwarder is listening
        print("IPC_client_info =", client_info)
        self.s.connect(('localhost', port))
        client_info_str = json.dumps(client_info)
        self.s.send(client_info_str.encode('utf-8'))  # Sends client info to data forwarder

        # Receive the response from the data forwarder
        response_str = self.s.recv(1024).decode('utf-8')

        response = json.loads(response_str)
        print("Response form the server ", response)
        # print("Response type: ", type(response))


        # Extract the Room_id from the response
        # EndMeeting = response["Room_id"]
        # print("Room id received:", EndMeeting) # this is the room id of which the meeting has ended
        # self.clear_room(EndMeeting)
        # print("Active rooms after clearing =", self.table)
        if (response!=None):
            #Now extract the audio port and ack port
            audio_port = response["audio_port"]
            ack_port = response["ack_port"]
            rr_port = response ["rr_port"]

            #convert the ports(string) to int
            audio_port = int(audio_port)
            ack_port = int(ack_port)
            rr_port = int(rr_port)

            #convert to bytes
            audio_port_byte = audio_port.to_bytes(4,'big')
            ack_port_byte = ack_port.to_bytes(4,'big')
            rr_port_byte = rr_port.to_bytes(4,'big')


            #return audio_port, ack_port #include rr_port too
            ports_info = audio_port_byte + ack_port_byte + rr_port_byte
            # # Line number 299, trying to send audio_port integer instead of audio_port_byte
            # ports_info = str (str(audio_port) + str(ack_port) + str(rr_port))
             
            #print("ports_info: ", ports_info)
            print("Ports info in IPC function:" , ports_info)
            return ports_info
        
        else: 
            return 0

        
    def DIPC(self, client_info): #This function deals with the inter process communication between control server and data forwarder server
        queue = Queue()

        ports = {}
        self.s = socket.socket()
        port = 5000  # Port where the data forwarder is listening
        print("IPC_client_info =", client_info)
        self.s.connect(('localhost', port))
        client_info_str = json.dumps(client_info)
        self.s.send(client_info_str.encode('utf-8'))  # Sends client info to data forwarder

        # Receive the response from the data forwarder
        response_str = self.s.recv(1024).decode('utf-8')

        response = json.loads(response_str)
        print("Response form the server ", response)
        # print("Response type: ", type(response))


        # Extract the Room_id from the response
        # EndMeeting = response["Room_id"]
        # print("Room id received:", EndMeeting) # this is the room id of which the meeting has ended
        # self.clear_room(EndMeeting)
        # print("Active rooms after clearing =", self.table)
        if (response!=None):
            #Now extract the audio port and ack port
            audio_port = response["audio_port"]
            ack_port = response["ack_port"]
            rr_port = response ["rr_port"]

            #return audio_port, ack_port #include rr_port too
            ports_info = [audio_port, ack_port, rr_port]
            # # Line number 299, trying to send audio_port integer instead of audio_port_byte
            # ports_info = str (str(audio_port) + str(ack_port) + str(rr_port))
             
            #print("ports_info: ", ports_info)
            print("Ports info in IPC function:" , ports_info)
            return ports_info
        
        else: 
            return 0

        # Close the socket
        self.s.close()

if __name__ == "__main__":
    PORT = 8000
    IP = '127.0.0.1'

    server = Server(IP, PORT)
    print("Listening for connection")
    server.run()



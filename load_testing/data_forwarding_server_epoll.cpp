#include <iostream>
#include <iostream>
#include <fstream>
#include <cstring>
#include <string>
#include <vector>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <fcntl.h>
#include <sys/epoll.h>
// #include "/home/mkdluffy/Desktop/Audio communication/Visual_feedback_for_audio_communication/json-develop/single_include/nlohmann/json.hpp"
#include "nlohmann/json.hpp"
#include <queue>
#include <thread>
#include <mutex>
#include <arpa/inet.h>
#include <time.h>
#include <csignal>
#include <cstdlib>
#include <atomic>
#include <arpa/inet.h>
#define PORT 5000
#define MAX_BUFFER_SIZE 1024
using namespace std;
mutex queueMutex;
const int MAX_EVENTS = 100;
// for audio and ack sockets
int is_host = 1;
int server_fd, new_socket, valread;
atomic<int> audio_packet_count(0);
float packets_forwarded = 0, packets_acknowledged=0;
map<string, pair<string, int>> hostClients;                        // This is used to store the clients in a room
map<string, string> roomID_Hosts;                                  // This is a map that stores all the call hosts of a particular room
map<string, vector<pair<string, pair<int, int>>>> roomID_IP_ports; // This is a mapping between all the IPs associated with each roomID
map<string, vector<pair<string, int>>> ack_IP_ports;               // new // temp mapping for ack ip and port
map<string, pair<int, int>> roomID_ports;                          // This is a mapping of roomID with ports.This needs to be changed. Another port needs to be added, for the reception report.
map<string, pair<int, pair<int, int>>> roomIDPorts;                // This is just another variable which adds another port of receiption report added to audio socket and acknowlegdement port.
map<string, pair<int, pair<int, int>>> roomIDSockets;              // This is to store the sockets corresponding to each room so that it can be closed when 'Endcall' is pressed.
map<int, string> audioSocket_RoomID;                               // This is to have a reverse mapping of sockets and room ID so that the audio packets can be transferred to the respective rooms.
map<int, string> ackSocket_RoomID;                                 // Reverse mapping from ack socket to roomID.
map<int, string> rrSocket_RoomID;                                  // Reverse mapping from rr_socket socket to roomID.
struct sockaddr_in address;
int opt = 1;
int addrlen = sizeof(address);
char buffer[1024] = {0};
struct epoll_event event;
struct epoll_event events[MAX_EVENTS];
map<int, pair<pair<string, int>, pair<pair<string, int>, pair<string, int>>>> reference_table; // (ssrc-----------> ((audio_ip_address,audio_port number),((ack_ip,ack_port),(rr_ip,rr_port))))

map<int, int> socket_type;

int audio_send, audio_send_host, ack_send, rr_send; // create fd for sending out respective data
// ofstream outputFile("data_to_send.pcm", std::ios::binary);

int handleTCPSocketEvent(int socket_fd, int epoll_fd)
{
    int audio_socket, ack_socket, rr_socket;
    int audio_port, ack_port, rr_port; // initialization for audio and ack ports
    struct sockaddr_in client_address;
    socklen_t client_address_len = sizeof(client_address);

    // Receive data from the client
    valread = recv(socket_fd, buffer, sizeof(buffer), 0);
    cout << "Buffer = " << buffer << "valread = " << valread << endl;
    // Convert received data to a string
    string received_data;
    received_data = string(buffer);
    //memset(buffer, 0, sizeof(buffer));
    cout << "Received_data = " << received_data << "\n";
    cout<<"----Line Number 65\n-------------";
    memset(buffer,0,sizeof(buffer));

    // cout << "Received data: " << received_data << endl; // For debugging

    // Parse the JSON string into a list
    using json = nlohmann::json;
    json client_info;

    try
    {
        cout<<"Parsing JSON data\n";
        client_info = json::parse(received_data);
    }
    catch (const json::exception &e)
    {
        cerr << "Error parsing JSON: " << e.what() << endl;
        // Handle the error gracefully
        // ...
        return 1; // Or return an appropriate error code
    }

    // Send the response back to the client
    // send(new_socket, response.c_str(), response.length(), 0);

    // Access the values in the client_info list
    string ReqType = client_info[0]; // request type
    string Pwd;
    string ip_address;
    string Room_id = client_info[1];
    if (ReqType != "Endcall")
    {
        Pwd = client_info[2];
        ip_address = client_info[3];
    }
    // Pwd = client_info[2];
    // ip_address = client_info[3];

    // Extract the IP address and port

    // string port = client_info[4];

    // Prepare the response based on the received values
    //------------------------------------------------------------------------------------------------------------------------------
    cout << "printing the extracted info"<< " " << ReqType << " " << Room_id << " " << Pwd << " " << ip_address << endl;
    json response;
    if (ReqType == "Create")
    {
        time_t my_time = time(NULL);
        printf("%s", ctime(&my_time));
        packets_acknowledged = 0;
        packets_acknowledged = 0;

        // step 1: add entry in table X (roomid and hosts)
        // roomID_Hosts.insert(Room_id, ip_address);
        // step 2: add entry in table y (list of IPs assiciated with each room)
        vector<string> placeholder;
        placeholder.push_back(ip_address);
        // roomID_IP_ports[Room_id].push_back(make_pair(ip_address, client_port)); // This is TCP's port number, we need to extract UDP port number.
        //  This is possible via the dummy packet sent by the client.
        //  between the create and join calls, there needs to be a dummy packet sent, and then after every join call,
        //  there needs to be an audio packet sent to the client.

        struct sockaddr_in udp_address1, udp_address2, udp_address3, udp_address4, udp_address5;
        // Create a third port (TCP) for Recieption report.

        // Create the first UDP socket
        if ((audio_socket = socket(AF_INET, SOCK_DGRAM, 0)) == 0)
        {
            perror("socket failed");
            exit(EXIT_FAILURE);
        }

        // Create the second UDP socket
        if ((ack_socket = socket(AF_INET, SOCK_DGRAM, 0)) == 0)
        {
            perror("socket failed");
            exit(EXIT_FAILURE);
        }

        // Create the third UDP socket
        if ((rr_socket = socket(AF_INET, SOCK_DGRAM, 0)) == 0)
        {
            perror("socket failed");
            exit(EXIT_FAILURE);
        }

        // for forwarding audio
        if ((audio_send = socket(AF_INET, SOCK_DGRAM, 0)) == 0)
        {
            perror("socket failed");
            exit(EXIT_FAILURE);
        }
        if ((audio_send_host = socket(AF_INET, SOCK_DGRAM, 0)) == 0)
        {
            perror("socket failed");
            exit(EXIT_FAILURE);
        }

        // Set socket options to reuse address and port
        if (setsockopt(audio_socket, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt)))
        {
            perror("setsockopt failed");
            exit(EXIT_FAILURE);
        }
        // Set socket options to reuse address and port
        if (setsockopt(ack_socket, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt)))
        {
            perror("setsockopt failed");
            exit(EXIT_FAILURE);
        }
        // Set socket options to reuse address and port
        if (setsockopt(rr_socket, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt)))
        {
            perror("setsockopt failed");
            exit(EXIT_FAILURE);
        }

        // Set socket options to reuse address and port
        if (setsockopt(audio_send, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt)))
        {
            perror("setsockopt failed");
            exit(EXIT_FAILURE);
        }

        if (setsockopt(audio_send_host, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt)))
        {
            perror("setsockopt failed");
            exit(EXIT_FAILURE);
        }

        // Add another port for reception report.

        udp_address1.sin_family = AF_INET;
        udp_address1.sin_addr.s_addr = INADDR_ANY;
        udp_address1.sin_port = 0; // Automatically choose a free port for audio.

        udp_address2.sin_family = AF_INET;
        udp_address2.sin_addr.s_addr = INADDR_ANY;
        udp_address2.sin_port = 0; // Automatically choose a free port for ack.

        udp_address3.sin_family = AF_INET;
        udp_address3.sin_addr.s_addr = INADDR_ANY;
        udp_address3.sin_port = 0; // Automatically choose a free port for reception report.

        udp_address4.sin_family = AF_INET;
        udp_address4.sin_addr.s_addr = INADDR_ANY;
        udp_address4.sin_port = 0; // Automatically choose a free port for forwarding audio.

        udp_address5.sin_family = AF_INET;
        udp_address5.sin_addr.s_addr = INADDR_ANY;
        udp_address5.sin_port = 0; // Automatically choose a free port for forwarding audio.

        // Bind the first UDP socket
        if (bind(audio_socket, (struct sockaddr *)&udp_address1, sizeof(udp_address1)) < 0)
        {
            perror("bind failed");
            exit(EXIT_FAILURE);
        }

        // Bind the second UDP socket
        if (bind(ack_socket, (struct sockaddr *)&udp_address2, sizeof(udp_address2)) < 0)
        {
            perror("bind failed");
            exit(EXIT_FAILURE);
        }
        // Bind the third UDP socket
        if (bind(rr_socket, (struct sockaddr *)&udp_address3, sizeof(udp_address3)) < 0)
        {
            perror("bind failed");
            exit(EXIT_FAILURE);
        }

        // Bind the 4th UDP socket
        
        // socket_type.insert(audio_socket, ack_socket); // adding the audio socket to the map so that it can be used to distinguish among the different function to be performed among the

        event.events = EPOLLIN; // Monitor read events
        event.data.fd = audio_socket;
        if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, audio_socket, &event) == -1)
        {
            cerr << "Failed to register audio socket with epoll." << endl;
            close(audio_socket);
            close(epoll_fd);
            return -1;
        }
        event.events = EPOLLIN;
        event.data.fd = ack_socket;
        if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, ack_socket, &event) == -1)
        {
            cerr << "Failed to register ack socket with epoll." << endl;
            close(ack_socket);
            close(epoll_fd);
            return -1;
        }
        event.events = EPOLLIN;
        event.data.fd = rr_socket;
        if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, rr_socket, &event) == -1)
        {
            cerr << "Failed to register audio socket with epoll." << endl;
            close(rr_socket);
            close(epoll_fd);
            return -1;
        }

        // Get the port numbers of the UDP sockets
        socklen_t len1 = sizeof(udp_address1);
        socklen_t len2 = sizeof(udp_address2);
        socklen_t len3 = sizeof(udp_address3);
        if (getsockname(audio_socket, (struct sockaddr *)&udp_address1, &len1) == -1)
        {
            perror("getsockname failed");
            exit(EXIT_FAILURE);
        }
        if (getsockname(ack_socket, (struct sockaddr *)&udp_address2, &len2) == -1)
        {
            perror("getsockname failed");
            exit(EXIT_FAILURE);
        }
        if (getsockname(rr_socket, (struct sockaddr *)&udp_address3, &len3) == -1)
        {
            perror("getsockname failed");
            exit(EXIT_FAILURE);
        }

        audio_port = ntohs(udp_address1.sin_port);
        ack_port = ntohs(udp_address2.sin_port);
        rr_port = ntohs(udp_address3.sin_port);

        // step 3 : Add the ports in table Z.
        roomID_ports[Room_id] = make_pair(audio_port, ack_port);
        roomIDPorts[Room_id].first = audio_port;
        roomIDPorts[Room_id].second.first = ack_port;
        roomIDPorts[Room_id].second.second = rr_port;

        roomIDSockets[Room_id].first = audio_socket;
        roomIDSockets[Room_id].second.first = ack_socket;
        roomIDSockets[Room_id].second.second = rr_socket;

        // step 4 : Add the reverse mapping in another table

        audioSocket_RoomID[audio_socket] = Room_id;
        ackSocket_RoomID[ack_socket] = Room_id;
        rrSocket_RoomID[rr_socket] = Room_id;

        // Store the UDP port numbers and room id in the response
        response["Room_id"] = Room_id;
        response["audio_port"] = to_string(audio_port); // converting audio port to string
        response["ack_port"] = to_string(ack_port);
        response["rr_port"] = to_string(rr_port);

        cout << "Response in json: " << response << endl;
        // Send the response back to the control server
        string response_str = response.dump(); // Convert response to string

        // Remove whitespace from the response string
        response_str.erase(remove(response_str.begin(), response_str.end(), ' '), response_str.end());
        // new socket needs to be defined properly.. it should rather be sendto function rather than send
        cout << "Sending the response to the control server\n";
        send(socket_fd, response_str.c_str(), response_str.length(), 0);
    }
    else if (ReqType == "Endcall")
    {

        //     // close all the ports associated with that room.
        //     close(roomIDSockets[Room_id].first);
        //     close(roomIDSockets[Room_id].second.first);
        //     close(roomIDSockets[Room_id].second.second);

        //     // Prepare a response to be sent to the control server
        //     //  json response;
        //     //  response["Room_id"] = "call_terminated";

        string response_str = response.dump(); // Convert response to string
        cout << "Response for Endcall: " << response << endl;

        vector<pair<string,pair<int,int>>>::iterator it;

        for(const auto ip : roomID_IP_ports[Room_id])
            close(ip.second.first);


        // Remove whitespace from the response string
        response_str.erase(remove(response_str.begin(), response_str.end(), ' '), response_str.end());
        // new socket needs to be defined properly.. it should rather be sendto function rather than send
        send(socket_fd, response_str.c_str(), response_str.length(), 0);

        cout<<"Total number of packets forwarder = "<<packets_forwarded<<" Total number of packets packets acknowledged = "<<packets_acknowledged<<endl;
        cout<<"Loss rate = "<<float(1-(packets_acknowledged/packets_forwarded))*100<<endl;

    }

    return 0;
}
void handleUDPSocketEvent(int room_fd) // room sockets include audio, ack and rr sockets
{
    // remove the queue used to store the client's IP adress along with the data present.
    //  Try to implement the forwarding function without using a queue

    // while parsing each packet that I receive, I need to extract the IP address and then forward the packet to
    // all the clients other than the sender.
    char buffer[MAX_BUFFER_SIZE] = {0};
    char ack_buffer[MAX_BUFFER_SIZE] = {0};
    struct sockaddr_in udp_address;
    socklen_t udp_address_len = sizeof(udp_address);
    char senderIP[INET_ADDRSTRLEN];
    // while (true)
    //{
    // Receive data from audio_socket
    int audio_valread = recvfrom(room_fd, buffer, sizeof(buffer), SOCK_NONBLOCK, reinterpret_cast<struct sockaddr *>(&udp_address), &udp_address_len);
    // cout << "audio_valread = " << audio_valread << " Buffer = " << buffer << endl;

    if (audio_valread > 0)
    {
        // Retrieve the IP address of the sender
        senderIP[INET_ADDRSTRLEN] = {0};
        inet_ntop(AF_INET, &(udp_address.sin_addr), senderIP, INET_ADDRSTRLEN);
    }
    else
    {
        // cout << "Buffer = " << buffer << endl;
        //  handle error or connection closed.
    }

    // Extract the sender IP address and port number
    char sender_ip[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &(udp_address.sin_addr), sender_ip, INET_ADDRSTRLEN);
    int sender_port = ntohs(udp_address.sin_port);

    // The application data needs to be ckecked. There are 4 possiblities; i.e. audio packet, audio dummy, ack dummy, rr dummy.

    char test_audio[] = "audio_dummy"; // similar to audio dummy, we need to add ack dummy and reception report dummy
    char test_ack[] = "ack_dummy";     // dummy packet for acks.
    char test_rr[] = "rr_dummy";       // dummy rr dummy
    char ack = '1';                    // new
    // Extract buffer[0]
    char temp = buffer[0]; // new

    

    // To get all the clients associated with a particular roomID, we can traverse it via the map of roomIDs and the corresponding list of IP addresses and port numbers from the room_fd.
    map<int, string>::iterator it;
    string roomid;
    it = audioSocket_RoomID.find(room_fd);
    if (it != audioSocket_RoomID.end())
    {
        roomid = audioSocket_RoomID[room_fd];
    }
    // There should be a fixed format of dummy packets so that the meta data about the dummy packet can be extracted properly.
    // Once we extract the ssrc, it can be used as a key. Later, the ack ip and port, rr ip and port will be mapped to the key.
    // assuming that the ssrc is an integer field

    int ssrc = 100;                  // this will be changed later when we actually extract the ssrc from the packet.
    if (!strcmp(test_audio, buffer)) // Checking if it is a dummy packet.There needs to be some mechanism to filter out whether it is a dummy packet.
                                     // also, it won't be the entire audio buffer, only a part that contains the meta_data about the packet.
    {
        cout << "audio_dummy\n";
        roomID_IP_ports[roomid].push_back(make_pair(sender_ip, make_pair(sender_port, is_host)));
        is_host = 0;
        for (const auto &clientIP : roomID_IP_ports[roomid])
        {
            cout << "client_ip: " << clientIP.first << " client_port: " << clientIP.second.first << "is_host bit = " << clientIP.second.second << endl;
        }
        reference_table[ssrc].first.first = sender_ip;
        reference_table[ssrc].first.second = sender_port;
    }
    else if (!strcmp(test_ack, buffer))
    {
        // map<int,pair<pair<string,int>,pair<pair<string,int>,pair<string,int> > > > reference_table; // (ssrc-----------> ((audio_ip_address,audio_port number),((ack_ip,ack_port),(rr_ip,rr_port))))
        cout << "ack_dummy\n";
        ack_IP_ports[roomid].push_back(make_pair(sender_ip, sender_port));
        reference_table[ssrc].second.first.first = sender_ip;
        reference_table[ssrc].second.first.second = sender_port;
    }
    else if (!strcmp(test_rr, buffer))
    {
        cout << "rr_dummy\n";
        reference_table[ssrc].second.second.first = sender_ip;
        reference_table[ssrc].second.second.second = sender_port;
    }

    else if (ack == buffer[0])
    {
        //cout << "ack received\n";

        int index = 0;
        for (const auto &clientIP : ack_IP_ports[roomid])
        {
            index++;
            // cout<<"sender ip,port = "<<sender_ip<<" "<<sender_port<<" checking for "<<clientIP.first <<" "<<clientIP.second<<endl;
            //  cout<<"Inside for loop\n";
            if (clientIP.second != sender_port || clientIP.first != senderIP) // now checking whether or not the IP address and the port number both are different.
            {
                // cout<<"entering if condition\n";
                struct sockaddr_in clientAddress // specifying the address of the destination
                {
                };
                clientAddress.sin_family = AF_INET;
                clientAddress.sin_port = htons(clientIP.second); // Replace with the appropriate port
                // clientAddress.sin_port = htons(22222);
                // clientAddress.sin_addr.s_addr = inet_addr("10.96.2.5");
                clientAddress.sin_addr.s_addr = inet_addr(clientIP.first.c_str());
                //cout << index << ") client_ip: " << clientIP.first << " clientAck_port: " << clientIP.second << endl;

                // cout << "\nforwarding data \n";
                // outputFile.write(buffer, audio_valread);
                ssize_t bytesSent = sendto(room_fd, buffer, audio_valread, 0,
                                           reinterpret_cast<struct sockaddr *>(&clientAddress), sizeof(clientAddress));
                if(bytesSent >0)
                    packets_acknowledged++;
                if (bytesSent == -1)
                {
                    cerr << "Failed to forward data to " << clientIP.first << endl;
                    return;
                }
            }
        }
    }
    // {

    // }
    // else if( it is a rr packet)
    // {

    // }

    else // it is an audio packet
    {
        // cout<<"audio packet\n";
        //  extracting the list of IP addresses in that particular room. First we get the roomID from the port number using the reverse mapping.
        // cout<<"After adding hosts, size of roomID buffer is "<<sizeof(roomID_IP_ports[roomid])<<endl;
        int index = 0;
        for (const auto &clientIP : roomID_IP_ports[roomid])
        {
            index++;
            // cout<<"sender ip,port = "<<sender_ip<<" "<<sender_port<<" checking for "<<clientIP.first <<" "<<clientIP.second<<endl;
            //  cout<<"Inside for loop\n";
            if (clientIP.second.first != sender_port || clientIP.first != senderIP) // now checking whether or not the IP address and the port number both are different.
            {
                // cout<<"entering if condition\n";
                struct sockaddr_in clientAddress // specifying the address of the destination
                {
                };
                clientAddress.sin_family = AF_INET;
                clientAddress.sin_port = htons(clientIP.second.first); // Replace with the appropriate port
                // clientAddress.sin_port = htons(22222);
                // clientAddress.sin_addr.s_addr = inet_addr("10.96.2.5");
                clientAddress.sin_addr.s_addr = inet_addr(clientIP.first.c_str());
               cout << index << ") client_ip: " << clientIP.first << " client_port: " << clientIP.second.first << endl;

                cout << "\nforwarding data \n";
                // outputFile.write(buffer, audio_valread);
                ssize_t bytesSent = sendto(room_fd, buffer, audio_valread, 0,
                                               reinterpret_cast<struct sockaddr *>(&clientAddress), sizeof(clientAddress));
                if(bytesSent>0)
                    packets_forwarded++;

                if (bytesSent == -1)
                {
                    cerr << "Failed to forward data to " << clientIP.first << endl;
                    return;
                }
            }
        }
    }
}
int main()
{
    int epoll_fd = epoll_create1(0);
    if (epoll_fd == -1)
    {
        cerr << "Failed to create epoll instance." << endl;
        return -1;
    }

    // Create a TCP socket for IPC
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0)
    {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }
    int flags = fcntl(server_fd, F_GETFL, 0);
    fcntl(server_fd, F_SETFL, flags | O_NONBLOCK); // fcntl is used to modify a socket descriptor.
    // Set socket options to reuse address and port
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt)))
    {
        perror("setsockopt failed");
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    // Bind the socket to localhost and port 5000
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0)
    {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 10) == -1)
    {
        cerr << "Listen failed" << std::endl;
        close(server_fd);
        return 1;
    }
    cout << "listening to new connection" << endl;
    event.events = EPOLLIN | EPOLLET;
    event.data.fd = server_fd;

    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, server_fd, &event) == -1)
    {
        cerr << "First tag : Failed to register TCP socket with epoll." << endl;
        close(server_fd);
        close(epoll_fd);
        return -1;
    }

    // int accepted = 0; // To check if TCP connection is accepted or not. Once the connection is accepted, we will set it to 1 so that we can distinguish between the connection accept event and data receiving event on the TCP socket.
    int num_events;
    while (true)
    {
        num_events = epoll_wait(epoll_fd, events, MAX_EVENTS, -1);
        if (num_events == -1)
        {
            cerr << "Failed to wait for events" << endl;
            break;
        }
        for (int i = 0; i < num_events; ++i)
        {
            if (events[i].data.fd == server_fd)
            {
                int new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t *)&addrlen);
                cout << "Accept call unblocked\n";
                if (new_socket < 0)
                {
                    cerr << "Error accepting request from client!" << endl;
                    exit(1);
                }

                event.events = EPOLLIN | EPOLLET;
                event.data.fd = new_socket;
                if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, new_socket, &event) == -1)
                {
                    cerr << "Second tag : Failed to register TCP socket with epoll." << endl;
                    close(new_socket);
                    close(epoll_fd);
                    return -1;
                }

                int code = handleTCPSocketEvent(new_socket, epoll_fd);
            }
            else
            {
                handleUDPSocketEvent(events[i].data.fd);
            }
        }
    }
    close(new_socket);
    close(server_fd);
    // outputFile.close();
    return 0;
}
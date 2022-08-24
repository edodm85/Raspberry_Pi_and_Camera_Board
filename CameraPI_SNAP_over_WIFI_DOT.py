import sys
import socket
import Camera
import DataOverTcp
import numpy as np
import select
import queue        #Python3
import time
import struct
import math
from time import sleep


SERVER_TCP_PORT = 2000
BUFFER_SIZE = 10000
BYTE_SEND = 9000


# object camera
cam = Camera.Camera()

# object protocol
pot = DataOverTcp.DataOverTcp()
dataRisp = DataOverTcp.Output()


# Parser
def parser_task():
    global dataRisp
    global pos
    global replyPkt

    while True:
        if dataRisp.newData:

            if dataRisp.payload_id_type == DataOverTcp.Type.CMD:
                print('Cmd riceived')

                # Setup camera
                if dataRisp.cmd_payload == DataOverTcp.Cmd.SET_IMAGE_SIZE:
                    pos = 0

                    # Init
                    cam.initCamera(dataRisp.width, dataRisp.height, dataRisp.format)

                    # preparo risposta
                    replyPkt = pot.create_dot_packet(struct.pack("B", DataOverTcp.Type.CMD_REPLY), [DataOverTcp.Cmd.SET_IMAGE_SIZE, 0xEE])
                    dataRisp.newData = False

                # Acquire One Image
                if dataRisp.cmd_payload == DataOverTcp.Cmd.SINGLE_SNAP:

                    if pos == 0:
                        replyPkt = pot.create_dot_packet(struct.pack("B", DataOverTcp.Type.CMD_REPLY), [DataOverTcp.Cmd.SINGLE_SNAP, 0xEE])
                        pos = 2

                    elif pos == 2:
                        image_payload = cam.snapCamera()

                        bw = dataRisp.width.to_bytes(2, byteorder='big')
                        bh = dataRisp.height.to_bytes(2, byteorder='big')

                        bf = b'\x00'
                        if format == "YUV":
                            bf = b'\x02'

                        y = bw + bh + bf
                        decoded = np.fromstring(y, dtype=np.uint8)
                        payload = np.concatenate((decoded, image_payload), axis=None)

                        replyPkt = pot.create_dot_packet(struct.pack("B", DataOverTcp.Type.IMAGE), payload)
                        sleep(1)
                        pos = 0
                        dataRisp.newData = False

            print('done')

            if len(replyPkt) > 0:
                if len(replyPkt) > BYTE_SEND:
                    data_split = np.array_split(replyPkt, math.ceil(replyPkt.size / BYTE_SEND))
                    for data in data_split:
                        message_queues[s].put(data)
                else:
                    message_queues[s].put(replyPkt)

                if s not in outputs:
                    outputs.append(s)

        else:
            break




def set_keepalive_linux(sock, after_idle_sec=1, interval_sec=3, max_fails=5):
    """Set TCP keepalive on an open socket.

    It activates after 1 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 3 seconds (interval_sec),
    and closes the connection after 5 failed ping (max_fails), or 15 seconds
    """
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)




def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


# MAIN
if __name__ == "__main__":


    # Create an INET (Internet Protocol v4 addresses), STREAMing socket (SOCK_STREAM for TCP and SOCK_DGRAM for UDP)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Make socket reusable
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    IP = get_ip()
    print("Starting up on %s port %s" % (IP, SERVER_TCP_PORT))
    server_socket.bind((IP, SERVER_TCP_PORT))

    # Listen for incoming connections
    # The integer argument is the number of connections the system should queue up in the background before rejecting new clients.
    server_socket.listen(1)

    inputs = [server_socket]
    outputs = []
    message_queues = {}

    while inputs:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)

        for s in readable:
            if s is server_socket:
                # accept() returns an open connection between the server and client
                connection, client_address = s.accept()
                print("Connection address:", client_address)

                set_keepalive_linux(connection)

                # socket nonblocking
                connection.setblocking(0)
                inputs.append(connection)
                message_queues[connection] = queue.Queue()
            else:
                data = s.recv(BUFFER_SIZE)
                if data:
                    # decode
                    dataRisp = pot.decode_dot_packet(data)

                    parser_task()

                    if s not in outputs:
                        outputs.append(s)
                else:
                    if s in outputs:
                        outputs.remove(s)
                    inputs.remove(s)
                    s.close()
                    print("Connection disconnect")

                    cam.killAll()
                    del message_queues[s]

        for s in writable:
            try:
                next_msg = message_queues[s].get_nowait()
            except queue.Empty:
                outputs.remove(s)
            else:
                #print("send..." + str(len(next_msg)))
                s.send(next_msg)

        for s in exceptional:
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()
            print("Connection disconnect ex")
            cam.killAll()
            del message_queues[s]









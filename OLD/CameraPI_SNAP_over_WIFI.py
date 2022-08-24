import sys
import socket
import picamera
import numpy as np
import select
import queue        #Python3


width = 160
height = 120
format = "BaW"

TCP_PORT = 2000
BUFFER_SIZE = 1024
BYTE_SEND = 9000

camera = picamera.PiCamera()



# Init Camera
def comandInit(cmd):
    global width
    global height
    global format

    strOk = b"OK"

    # Parse resolution
    if b"19200" in cmd:
        width = 160
        height = 120
    elif b"76800" in cmd:
        width = 320
        height = 240
    elif b"307200" in cmd:
        width = 640
        height = 480
    elif b"921600" in cmd:
        width = 1280
        height = 720
    elif b"2073600" in cmd:
        width = 1920
        height = 1080
    elif b"5038848" in cmd:
        width = 2592
        height = 1944
    else:
        strOk = b"Not Supported"

    # Set B&W or YUV
    if b"BAW" in cmd:
        format = "BAW"
    elif b"YUV420" in cmd:
        format = "YUV"
    else:
        strOk = b"Not Supported"

    return strOk


def comandCamera():
    # Set camera resolution
    camera.resolution = (width, height)

    # Start acquisition
    camera.start_preview()

    return




def cameraSnap():

    # Create stream
    stream = open('image.data', 'w+b')

    camera.capture(stream, 'yuv')
    # "Rewind" the stream to the beginning so we can read its content
    stream.seek(0)

    fwidth = (width + 31) // 32 * 32
    fheight = (height + 15) // 16 * 16

    # Load the Y (luminance) data from the stream (numpy array)
    Y = np.fromfile(stream, dtype=np.uint8, count=fwidth * fheight)
    OUT_Y = Y[:width*height]

    # Load U
    U = np.fromfile(stream, dtype=np.uint8, count=(fwidth // 2) * (fheight // 2))
    OUT_U = U[:(int)((width * height) / 4)]

    # Load V
    V = np.fromfile(stream, dtype=np.uint8, count=(fwidth // 2) * (fheight // 2))
    OUT_V = V[:(int)((width * height) / 4)]


    # output color array
    OUT = np.concatenate((OUT_Y, OUT_U, OUT_V), axis=None)

    if format == "BAW":
        return OUT_Y
    if format == "YUV":
        return OUT


# Command reader
def parseCMD(cmd, conn):
    str = b"HELLO"

    if b"init" in cmd:
        camera.stop_preview()
        ack = comandInit(cmd)
        comandCamera()
        if ack in b"OK":
            str = b"OV Init OK\n"
        else:
            str = ack + b"\n"

    if cmd == b"snap":
        conn.send(b"sRt")
        str = cameraSnap()

    return str


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


# MAIN TCP socket
if __name__ == "__main__":
    # Create an INET (Internet Protocol v4 addresses), STREAMing socket (SOCK_STREAM for TCP and SOCK_DGRAM for UDP)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Make socket reusable
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    IP = get_ip()
    print("Starting up on %s port %s" % (IP, TCP_PORT))
    server_socket.bind((IP, TCP_PORT))

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
                    print("received data:", data)
                    dataRisp = parseCMD(data, s)

                    if len(dataRisp) > BYTE_SEND:
                        data_split = np.array_split(dataRisp, (dataRisp.size / BYTE_SEND))
                        for data in data_split:
                            message_queues[s].put(data)
                    else:
                        message_queues[s].put(dataRisp)
                    if s not in outputs:
                        outputs.append(s)
                else:
                    if s in outputs:
                        outputs.remove(s)
                    inputs.remove(s)
                    s.close()
                    print("Connection disconnect")
                    camera.stop_preview()
                    del message_queues[s]

        for s in writable:
            try:
                next_msg = message_queues[s].get_nowait()
            except queue.Empty:
                outputs.remove(s)
            else:
                s.send(next_msg)

        for s in exceptional:
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()
            print("Connection disconnect ex")
            camera.stop_preview()
            del message_queues[s]


import sys
import socket
import picamera
import numpy as np
import select


is_py2 = sys.version[0] == '2'
if is_py2:
    import Queue
else:
    import Queue as queue



width = 160
height = 120
format = "BaW"

TCP_IP = '192.168.43.172'
TCP_PORT = 2000
BUFFER_SIZE = 1024
BYTE_SEND = 9000

camera = picamera.PiCamera()



# Init Camera
def comandInit(cmd):
    global width
    global height
    global format

    strOk = "OK"

    # Parse resolution
    if "19200" in cmd:
        width = 160
        height = 120
    elif "76800" in cmd:
        width = 320
        height = 240
    elif "307200" in cmd:
        width = 640
        height = 480
    elif "921600" in cmd:
        width = 1280
        height = 720
    elif "2073600" in cmd:
        width = 1920
        height = 1080
    elif "5038848" in cmd:
        width = 2592
        height = 1944
    else:
        strOk = "Not Supported"

    # Set B&W or YUV
    if "BAW" in cmd:
        format = "BAW"
    elif "YUV420" in cmd:
        format = "YUV"
    else:
        strOk = "Not Supported"

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
    OUT_U = U[:(width * height) / 4]

    # Load V
    V = np.fromfile(stream, dtype=np.uint8, count=(fwidth // 2) * (fheight // 2))
    OUT_V = V[:(width * height) / 4]


    # output color array
    OUT = np.concatenate((OUT_Y, OUT_U, OUT_V), axis=None)

    if format == "BAW":
        return OUT_Y
    if format == "YUV":
        return OUT


# Command reader
def parseCMD(cmd, conn):
    str = "HELLO"

    if "init" in cmd:
        camera.stop_preview()
        ack = comandInit(cmd)
        comandCamera()
        if ack in "OK":
            str = "OV Init OK\n"
        else:
            str = ack + "\n"

    if cmd == "snap":
        conn.send("sRt")
        str = cameraSnap()

    return str




# TCP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((TCP_IP, TCP_PORT))
server_socket.listen(1)


inputs = [server_socket]
outputs = []
message_queues = {}

while inputs:
    readable, writable, exceptional = select.select(inputs, outputs, inputs)

    for s in readable:
        if s is server_socket:
            connection, client_address = s.accept()
            print ('Connection address:', client_address)
            # socket nonblocking
            connection.setblocking(0)
            inputs.append(connection)
            message_queues[connection] = Queue.Queue()
        else:
            data = s.recv(BUFFER_SIZE)
            if data:
                print ("received data:", data)
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
                print ('Connection disconnect')
                camera.stop_preview()
                del message_queues[s]

    for s in writable:
        try:
            next_msg = message_queues[s].get_nowait()
        except Queue.Empty:
            outputs.remove(s)
        else:
            s.send(next_msg)

    for s in exceptional:
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        s.close()
        print ('Connection disconnect')
        camera.stop_preview()
        del message_queues[s]


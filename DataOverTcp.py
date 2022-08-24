import sys
import numpy as np
import struct



class Type:
    CMD = 1
    CMD_REPLY = 2
    IMAGE = 5
    IMAGE_ACK = 6


class Cmd:
    SINGLE_SNAP = 16            # b'\10'
    START_GRAB = 17             # b'\11'
    STOP_GRAB = 18              # b'\12'

    SET_IMAGE_SIZE = 21         # b'\15'

    GET_FLASH_STATUS = 37       # b'\25'
    GET_FOCUS_STATUS = 53       # b'\35'

    SET_FLASH_OFF = 32          # b'\20'
    SET_FLASH_ON = 33           # b'\21'
    SET_FOCUS_OFF = 48          # b'\30'
    SET_FOCUS_ON = 49           # b'\31'

    ACK = 238                   # b'\EE'



class Output:
    newData = False
    payload_id_type = 0
    cmd_payload = 0
    width = 0
    height = 0
    format = ''


DOT_START = b'\xAA'
DOT_STOP = b'\x55'
DOT_VERSION = b'\x01'




class DataOverTcp:
    def __init__(self):
        print('INIT')


    def create_dot_packet(self, type, payload):
        ln = len(payload) + 2
        length = struct.pack('>I', ln)
        packet = DOT_START + DOT_VERSION + length + type + bytes(payload) + DOT_STOP

        print('out: ', end='')
        print(payload)

        decoded = np.fromstring(packet, dtype=np.uint8)
        return decoded



    def decode_dot_packet(self, array):
        global width
        global height
        global format
        global replyImagePkt

        for x in array:
            print(hex(x)[2:].zfill(2) + ':', end='')

        start = array[0]
        version = array[1]
        length = array[2:6]
        payload_id_type = array[6]

        payload_length = struct.unpack('>I', length)[0] - 2
        payload = array[7: 7 + payload_length]
        print("Payload len: %s" % payload_length)

        stop = array[6 + 1 + payload_length]

        if (start == int.from_bytes(DOT_START, "big")) and (stop == int.from_bytes(DOT_STOP, "big")):
            out = Output()

            if payload_id_type == Type.CMD:
                cmd_payload = array[7]

                # Setup camera
                if cmd_payload == Cmd.SET_IMAGE_SIZE:
                    width = struct.unpack('>H', array[8:10])[0]
                    height = struct.unpack('>H', array[10:12])[0]
                    image_format = array[12]

                    # Set B&W or YUV
                    if image_format == 0:
                        format = "BAW"
                    elif image_format == 2:
                        format = "YUV"

                    out.payload_id_type = payload_id_type
                    out.cmd_payload = cmd_payload
                    out.width = width
                    out.height = height
                    out.format = format
                    out.newData = True
                    return out

                # Acquire One Image
                if cmd_payload == Cmd.SINGLE_SNAP:
                    out.payload_id_type = payload_id_type
                    out.cmd_payload = cmd_payload
                    out.width = width
                    out.height = height
                    out.format = format
                    out.newData = True
                    return out


            elif payload_id_type == Type.CMD_REPLY:
                print('CMD REPLY')
            elif payload_id_type == Type.IMAGE:
                print('IMAGE')
            elif payload_id_type == Type.IMAGE_ACK:
                print('ACK IMAGE')
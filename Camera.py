import sys
import picamera
import numpy as np



class Camera:
    def __init__(self):
        self.camera = picamera.PiCamera()
        self.width = 0
        self.height = 0
        self.format = 'NONE'


    def initCamera(self, w, h, f):
        self.width = w
        self.height = h
        self.format = f

        # Stop acquisition
        self.camera.stop_preview()

        # Set camera resolution
        self.camera.resolution = (self.width, self.height)

        # Start acquisition
        self.camera.start_preview()


    def snapCamera(self):

        # Create stream
        stream = open('image.data', 'w+b')

        self.camera.capture(stream, 'yuv')
        # "Rewind" the stream to the beginning so we can read its content
        stream.seek(0)

        fwidth = (self.width + 31) // 32 * 32
        fheight = (self.height + 15) // 16 * 16

        # Load the Y (luminance) data from the stream (numpy array)
        Y = np.fromfile(stream, dtype=np.uint8, count=fwidth * fheight)
        OUT_Y = Y[:self.width * self.height]

        # Load U
        U = np.fromfile(stream, dtype=np.uint8, count=(fwidth // 2) * (fheight // 2))
        OUT_U = U[:(int)((self.width * self.height) / 4)]

        # Load V
        V = np.fromfile(stream, dtype=np.uint8, count=(fwidth // 2) * (fheight // 2))
        OUT_V = V[:(int)((self.width * self.height) / 4)]


        # output color array
        OUT = np.concatenate((OUT_Y, OUT_U, OUT_V), axis=None)

        if self.format == "BAW":
            return OUT_Y
        elif self.format == "YUV":
            return OUT

    def killAll(self):
        # Stop acquisition
        self.camera.stop_preview()
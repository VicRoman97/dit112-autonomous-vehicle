from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import numpy as np
import cv2 as cv
import time
import threading
import serial
import logging
import multiprocessing as mp
import struct

class ContourRectangle():

    def __init__(self, shape, rectangle):
        self.shape = shape
        self.rectangle = rectangle
        
class Camera(mp.Process):

    #Initialize camera
    camera = PiCamera()

    #Set camera settings
    camera.resolution = (320, 240)
    camera.framerate = 30

    #Use an array of pixels for better performance
    camera_array = PiRGBArray(camera, size=(320, 240))

    #color boundaries
    lower_green = np.array([50, 100, 100])
    upper_green = np.array([70, 255, 255])

    lower_blue = np.array([100, 99, 2])
    upper_blue = np.array([120, 119, 82])

    lower_red = np.array([82, 53, 179])
    upper_red = np.array([102, 73, 259])
                
    def __init__(self, serial):
        #mp.Process.__init__(self)
        self.serial = serial
        #Allow camera to start
        time.sleep(0.1)
        #self.processCamera()

    #A function to compare contour vertices to recognize the shape
    def shape_compare(self, c):

            #turn curves into lines
            shape = cv.arcLength(c, True)
            #Approximate polygon curves to get better idea on straight lines
            approx = cv.approxPolyDP(c, 0.04 * shape, True)
            
            #Compare vertices of approximated shapes
            if len(approx) == 3:
                return "triangle"

            elif len(approx) == 4:

                (x, y, w, h) = cv.boundingRect(approx)
                ar = w / float(h)
                        
                if ar >= 0.95 and ar <= 1.05:
                    return "square"
                else: 
                    return "rectangle"
            elif len(approx) == 8:
                return "stop sign"
            else:
                return "none"


    #Function to detect shapes in real time
    def detectShapes(self, frame, cont):
        lst = []
        for c in cont:
            #Calculate center of contours
            moment = cv.moments(c)
            if (moment["m00"] == 0):
                moment["m00"]=1
            cX = int(moment["m10"] / moment["m00"])
            cY = int(moment["m01"] / moment["m00"])

            #Call the method we made above to decide what the shape of a contour is
            thishape = self.shape_compare(c)
            if(cv.contourArea(c)>130):
                cv.drawContours(frame, [c], -1, (0, 255, 0), 2)
                        
                cv.putText(frame, thishape, (cX - 20, cY - 20),
                cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                if(thishape != "none"):
                    x, y, w, h = cv.boundingRect(c)
                    roi = frame[y:y+h, x:x+h]
                    lst.append(ContourRectangle(thishape, roi))
        return lst
    def detectColor(self, mask_green, mask_blue, mask_red, color):
        green = cv.countNonZero(mask_green)
        blue = cv.countNonZero(mask_blue)
        red = cv.countNonZero(mask_red)
        

    def detectSign(self, shapes, serial):
        for s in shapes:
            if(s.shape == "triangle"):
                hsv = cv.cvtColor(s.rectangle, cv.COLOR_BGR2HSV)
                mask = cv.inRange(hsv, Camera.lower_blue, Camera.upper_blue)
                if(cv.countNonZero(mask) > 140):
                    self.serial.write(struct.pack('!B', 191))
                    print("blue triangle")
            elif(s.shape == "square"):
                hsv = cv.cvtColor(s.rectangle, cv.COLOR_BGR2HSV)
                mask = cv.inRange(hsv, Camera.lower_green, Camera.upper_green)
                if(cv.countNonZero(mask) > 140):
                    self.serial.write(struct.pack('!B', 192))
                    print("green square")
            elif(s.shape == "rectangle"):
                img_inv = cv.bitwise_not(s.rectangle)
                hsv = cv.cvtColor(img_inv, cv.COLOR_BGR2HSV)
                mask = cv.inRange(hsv, Camera.lower_red, Camera.upper_red)
                if(cv.countNonZero(mask) > 140):
                    self.serial.write(struct.pack('!B', 193))
                    print("red rectangle")
            else:
                img_inv = cv.bitwise_not(s.rectangle)
                hsv = cv.cvtColor(img_inv, cv.COLOR_BGR2HSV)
                mask = cv.inRange(hsv, Camera.lower_red, Camera.upper_red)
                if(cv.countNonZero(mask) > 140):
                    self.serial.write(struct.pack('!B', 194))
                    print("stop sign")
                
                
        
    def processCamera(self):
        time.sleep(0.1)
        #Perform functions for each frame of the camera capture
        for frame in self.camera.capture_continuous(self.camera_array, format="bgr", use_video_port=True):
                img = frame.array
                img_inv = cv.bitwise_not(img)
                #draw relevant color spaces
                #Use greyscale for easier recognition of contours
                gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
                
                #Guassian blur to smooth out the images
                blurred = cv.GaussianBlur(gray, (5, 5), 0)

                #A generic threshold to decide what we consider contours
                thresh = cv.threshold(blurred, 128, 255, cv.THRESH_BINARY_INV)[1]

                #convert BGR to HSV
                hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
                hsv_inv = cv.cvtColor(img_inv, cv.COLOR_BGR2HSV)

                #
                #Find these contours based on the threshhold
                _, contours, _ = cv.findContours(thresh.copy(), cv.RETR_TREE,
                        cv.CHAIN_APPROX_SIMPLE)
                
                #threshhold the hsv image to get only green
                #mask_green = cv.inRange(hsv, lower_green, upper_green)
                #mask_blue = cv.inRange(hsv, lower_blue, upper_blue)
                #mask_red = cv.inRange(hsv_inv, lower_red, upper_red)
            
                #bitwise-AND mask and original image
                #res = cv.bitwise_and(img, img, mask= mask)

                #
                #checks whether a stop sign and a color are detected. If they are, writes to serial.
                self.detectSign(self.detectShapes(img, contours), serial)
                #
                #draw images & contours
                
                cv.imshow("Image", img)
                #cv.imshow("Mask", res)
                #cv.imshow("Threshold", thresh)
                self.camera_array.truncate(0)
                key = cv.waitKey(1) & 0xFF
                if key==ord("q"):
                    break
                
    #def start(self):
    #    cameraThread = threading.Thread(target=self.startProcess)
    #    cameraThread.start()
    #    print("Thread Started")

try:
        serial_arduino = serial.Serial('/dev/ttyACM0', 9600)
except Exception:
        serial_arduino = serial.Serial('/dev/ttyACM1', 9600)
        
mCamera = Camera(serial_arduino)
mCamera.processCamera()

        

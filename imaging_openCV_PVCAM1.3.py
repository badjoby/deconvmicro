#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 10 08:30:54 2021

@author: joby
"""

import tkinter
import cv2
import PIL.Image, PIL.ImageTk
import matplotlib.pyplot as plt
import numpy as np
import time
import serial
import imutils
from pyvcam import pvc
from pyvcam.camera import Camera
from tkinter import *
import imageio
from tkinter import filedialog


#from io import BytesIO
#import requests

CVorPVCAM = 0     #1 for CV and 0 for PVCAM
arduino = serial.Serial(port='/dev/ttyACM0', baudrate=115200, timeout=0.1)
window_title="Fluoresence Deconvolved Imager"
video_source = 1
FirstLoc = 0
LastLoc = 1
Exp_time_live = 100 #Exposure time in msec
NFramAvg = 20       #Number of frames to average
# pvc.init_pvcam()  # Initialize PVCAM 

LiveViewFLG = 1     #1 means live view on if other conditions are also OK. 
ImStack = []        #To store the sequence of averaged frames
Stak_allslices=[]   #To store the sequence of averaged frames as np_array
FirstLocFLG = 0     #Set to 1 by function FirstLoc when it is set 
LastLocFLG = 0      #Set to 1 by funciton LastLoc when it is set
ScanFLG = 0         #Set to 1 for scanning
SliceStep = 5       #Slice Step in microns. has to be converted to steps before passing to arduino
if CVorPVCAM == 0:
  pvc.init_pvcam()              # Initialize PVCAM 
 

# while True:
#     num = input("Enter a number: ")
#     value = ArduinoCom.write_read(num)
#     print(value)

class App:
    def __init__(self, window, window_title, video_source, CVorPVCAM=CVorPVCAM):
        self.window = window
        self.window.title(window_title)
        self.window.iconphoto(True, PhotoImage(file='/home/joby/UoH/Work/Imaging_Physiology_setup/Deconv_microscope/FDImaging-3.png')) #To put an icon later
        
        #self.ArduinoCom = MyArduinoCom()
        
        self.video_source = video_source  #OpenCV
        # open video source (by default this will try to open the computer webcam) #OpenCV

        self.vid = MyVideoCapture(CVorPVCAM, self.video_source)  #Instantiate MyVideoCapture object as vid
  
  # A camera object named vid has already been created. The vid.cam's variables and functions will depend on which
  # type of cam object you have opened. PVCAM or CV
        
        # Create a canvas that can fit the above video source size
        self.canvas = tkinter.Canvas(window, width = self.vid.width+90, height = self.vid.height+30)
        print("Width and Height", self.vid.width, self.vid.height )
        # self.canvas.pack()
        self.canvas.grid(row=0,column=0,columnspan=4,rowspan=10)
        
        #Entry for exposure time in msec
        self.box_exposureTime=tkinter.Entry(window, width=10)
        self.box_exposureTime.grid(row=1,column=4)
        self.box_exposureTime.insert(0,str(Exp_time_live))
        
        #Button to change the exposure time by updating the variable Exp_time_live
        self.btn_exposureTime=tkinter.Button(window, text="Set Exposure T", width=8, command=self.updateExposureTime)
        self.btn_exposureTime.grid(row=1,column=5)
        
        #Entry for exposure time in msec
        self.box_FrameAvg=tkinter.Entry(window, width=10)
        self.box_FrameAvg.grid(row=2,column=4)
        self.box_FrameAvg.insert(0,str(NFramAvg))
        
        #Button to change the  number of frames to be averaged
        self.btn_FrameAvg=tkinter.Button(window, text="Set Frame Avg", width=8, command=self.updateFrameAvg)
        self.btn_FrameAvg.grid(row=2,column=5)
               
        #Entry for step size in microns
        self.box_slice_step=tkinter.Entry(window, width=10)
        self.box_slice_step.grid(row=4,column=4)
        self.box_slice_step.insert(0,str(SliceStep))
        
        #Button to ask Arduino to sets slice thickness from the slice_step Entry by sending to arduino 
        self.btn_updateScanStepsize=tkinter.Button(window, text="Set Slice Thick", width=8, command=self.updateScanStepsize)
        self.btn_updateScanStepsize.grid(row=4,column=5)
        
        
        # Button that lets the user take a snapshot
        self.btn_snapshot=tkinter.Button(window, text="Snapshot", width=8, command=self.snapshot)
        self.btn_snapshot.grid(row=11,column=0)
        # self.btn_snapshot.pack()
        
        #Button to toggle Live View
        self.btn_LiveViewSet=tkinter.Button(window, text="Live View", width=8, command=self.LiveViewSet)
        self.btn_LiveViewSet.grid(row=0,column=4)
        self.btn_LiveViewSet.configure(fg='Red')
        
        #Button to show a PreView with actual exposure and Average
        self.btn_PreViewSlice=tkinter.Button(window, text="Preview Slice", width=8, command=self.PreViewSlice)
        self.btn_PreViewSlice.grid(row=0,column=5)
       # self.btn_PreViewSlice.configure(fg='Black')
        

        #Button to ask Arduino to send the current z and use it as first slice position
        self.btn_SetFirst=tkinter.Button(window, text="Set first point", width=8, command=self.SetFirst)
        self.btn_SetFirst.grid(row=6,column=4)
        
        #Button to ask Arduino to send the current z and use it as last slice position
        self.btn_SetLast=tkinter.Button(window, text="Set last point", width=8, command=self.SetLast)
        self.btn_SetLast.grid(row=6,column=5)
        
        #Button to ask Arduino to start the scan
        self.btn_Scan=tkinter.Button(window, text="Scan", width=8, command=self.Scan)
        self.btn_Scan.grid(row=11,column=1)
        
        #Quit
        self.btn_Quit=tkinter.Button(window, text="Quit", width=8, command=window.destroy)
        self.btn_Quit.grid(row=11,column=2)
        data = arduino.readline()    #Empty the buffer from arduino?
        
        # After it is called once, the update method will be automatically called every delay milliseconds
        self.delay = 15
        self.update(CVorPVCAM)

        self.window.mainloop()
        
    def LiveViewSet(self):  #toggle live view
        global LiveViewFLG
        if LiveViewFLG==0:
           LiveViewFLG = 1
           self.btn_LiveViewSet.configure(fg='Red')
        else:
           LiveViewFLG = 0
           self.btn_LiveViewSet.configure(fg='Black')
        print(LiveViewFLG)  
        return LiveViewFLG  
    
    def updateExposureTime(self):  #Update Exposure Time
        global Exp_time_live
        Exp_time_live=int(self.box_exposureTime.get())
        
    def updateFrameAvg(self):  #Update Exposure Time
        global NFramAvg
        NFramAvg=int(self.box_FrameAvg.get())    
    
    def FindLimits(self):  # Get a frame from the video source
        global LiveViewFLG
        #Send signal to Arduino
        
    def SetFirst(self):  # Get a frame from the video source
        global FirstLoc
        global FirstLocFLG
        global ScanFLG
        if (ScanFLG==0):
          arduino.write(bytes('1', 'utf-8')) #Asking the Arduino (by sending 1) to set the current position as the First
          while (arduino.inWaiting() <= 0):
            time.sleep(0.1) #jdfkd
          data = arduino.readline() #Getting the z-position as first position
          print(int(data))
          if (int(data)==1):
            FirstLocFLG=1;
        
    def SetLast(self):  # Get a frame from the video source
        global LastLoc
        global LastLocFLG
        global ScanFLG
        if (ScanFLG==0):
          arduino.write(bytes('2', 'utf-8')) #Asking the Arduino (by sending 2) to set the current position as the Last
          while (arduino.inWaiting() <= 0):
            time.sleep(0.1) #jdfkd
          data = arduino.readline() #Getting the z-position as last position
          print(int(data))
          if (int(data)==2):
            LastLocFLG=1
        
    def Scan(self):  # Get a frame from the video source
        global LiveViewFLG
        global ScanFLG

        if (FirstLocFLG & LastLocFLG):
          arduino.write(bytes('3', 'utf-8')) #Asking the Arduino (by sending 3) to set start the scan. Ardino send 0 amd moves
                                #to First position and sends signal 9 and waits for 10 from Python indicating frame complete
          while (arduino.inWaiting() <= 0):
            time.sleep(0.1) #jdfkd
          data = arduino.readline() #Getting the z-position as last position
          print(int(data))
          if (int(data)==3):
            ScanFLG = 1
            LiveViewFLG = 0
          self.ScanStack()  
        else:
          tkinter.messagebox.showinfo("Title", "Please set First and Last slice first")
          
    def PreViewSlice(self):  # Get a frame from the video source
        global LiveViewFLG
        global ScanFLG
        
        LiveViewFLG=0
        ScanFLG=0
        (rAvg, gAvg, bAvg) = (None, None, None)
        (grayAvg) = (None)
        total = 0
       # print('NFramAvg = ' + str(NFramAvg)) 
        for n in range(NFramAvg):    #Capturing FramAvg frames         
          if CVorPVCAM==1:
            ret, frame = self.vid.my_get_frame()
            (B, G, R) = cv2.split(frame.astype("float"))  #Split the frmae into its respective channels
        
            if rAvg is None:    # if the frame averages are None, initialize them
              rAvg = R
              bAvg = B
              gAvg = G
            else:  # otherwise, compute the weighted average between the history of frames and the current frames
              rAvg = ((total * rAvg) + (1 * R)) / (total + 1.0)
              gAvg = ((total * gAvg) + (1 * G)) / (total + 1.0)
              bAvg = ((total * bAvg) + (1 * B)) / (total + 1.0)
              # print('Total='+ str(total))
            avg = cv2.merge([bAvg, gAvg, rAvg]).astype("uint8")
            np_frame = np.array(avg)
            # cv2.imwrite(args["output"], avg)
            # np_frame = cv2.imread('video', avg)
          
            # if ret:
            #   self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(frame))
            # self.canvas.create_image(0, 0, image = self.photo, anchor = tkinter.NW)
            # print("Reached", ret)
          else:
            print('Exp_time_live' + str(Exp_time_live))
            frame = self.vid.cam.get_frame(exp_time=Exp_time_live)
            if grayAvg is None:    # if the frame averages are None, initialize them
              grayAvg = frame.astype("float")
            else:
              grayAvg = ((total * grayAvg) + (1 * frame.astype("float"))) / (total + 1.0)
         #   self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(frame)
            
         
          total += 1  # increment the total number of frames read thus far
          
        if CVorPVCAM==0:
          grayAvg=grayAvg/8.0;
          tmp_frame = grayAvg.astype("uint8")
          Gframe = tmp_frame.copy()
          Bframe = tmp_frame.copy()
          Rframe = tmp_frame.copy()
          # color_find = [0,0,255]
          indexes=np.where(tmp_frame <= 0)  # Find zero value pixels to make blue
          Bframe[indexes]=255 # Make all those blue
          Rframe[indexes]=0 #  Make all the locations 0 for red
          Gframe[indexes]=0 # Make all the locations 0 for greeen
          indexes=np.where(tmp_frame == 255 )  # Find zero value pixels to make blue
          Bframe[indexes]=0 # Make all those zero for blue
          Rframe[indexes]=255 #  Make all the locations 255 for red
          Gframe[indexes]=0 # Make all the locations 0 for greeen
          np_frame = cv2.merge([Bframe, Gframe, Rframe]).astype("uint8")
          
          
       # if ret:
        self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(np_frame))
        self.canvas.create_image(0, 0, image = self.photo, anchor = tkinter.NW)

        
        

    def updateScanStepsize(self):  #Update stepsize
        global SliceStep
     #   global FirstLocFLG
        SliceStep=self.box_slice_step.get()
        print('Raw ' + SliceStep)
        if SliceStep.isdigit():
          StepSize=int(SliceStep)   #Has to be caliberated and converted from microns to stepper motor stepsize
          print(StepSize)
          if (ScanFLG==0):
            print('Here')
            arduino.write(bytes('4', 'utf-8')) #Asking the Arduino (by sending 1) to set the current position as the First
            while (arduino.inWaiting() <= 0):
              time.sleep(0.1) #jdfkd
            data = arduino.readline() #Getting the z-position as first position
            print(int(data))
            if (int(data)==4):
     #         FirstLocFLG=1;
              arduino.write(bytes(str(StepSize), 'utf-8')) #Asking the Arduino (by sending 1) to set the current position as the First
              while (arduino.inWaiting() <= 0):
                time.sleep(0.1) #jdfkd
              data = arduino.readline() #Getting the z-position as first position
              print(int(data))
                        
        
    def Quit(self):  # Get a frame from the video source
        quit()
        #Send signal to Arduino to ask it to send  current coordinate and use it as last
         

    def snapshot(self, CVorPVCAM = CVorPVCAM): # Get a frame from the video source
        if CVorPVCAM==1:
          ret, frame = self.vid.my_get_frame()
        else:
          frame = self.vid.cam.get_frame(exp_time=Exp_time_live)
          ret = 1

        if ret:
            cv2.imwrite("frame-" + time.strftime("%d-%m-%Y-%H-%M-%S") + ".jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    def update(self,  CVorPVCAM = CVorPVCAM):
        # Get a frame from the video source
        global LiveViewFLG
        global ScanFLG

        if (LiveViewFLG == 1) & (ScanFLG == 0):     #Live View On
          if CVorPVCAM==1:
            ret, frame = self.vid.my_get_frame()
            if ret:
              self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(frame))
              self.canvas.create_image(0, 0, image = self.photo, anchor = tkinter.NW)
              # print("Reached", ret)
          else:
            frame = self.vid.cam.get_frame(exp_time=Exp_time_live)
            #tmp_frame = np.array(frame)/8;
            grayAvg=frame.astype("float")/8.0;
            tmp_frame = grayAvg.astype("uint8")
            Gframe = tmp_frame.copy()
            Bframe = tmp_frame.copy()
            Rframe = tmp_frame.copy()
          # color_find = [0,0,255]
            indexes=np.where(tmp_frame <= 0)  # Find zero value pixels to make blue
            Bframe[indexes]=255 # Make all those blue
            Rframe[indexes]=0 #  Make all the locations 0 for red
            Gframe[indexes]=0 # Make all the locations 0 for greeen
            indexes=np.where(tmp_frame == 255 )  # Find zero value pixels to make blue
            Bframe[indexes]=0 # Make all those zero for blue
            Rframe[indexes]=255 #  Make all the locations 255 for red
            Gframe[indexes]=0 # Make all the locations 0 for greeen
            np_frame = cv2.merge([Bframe, Gframe, Rframe]).astype("uint8")
            self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(np_frame))
            self.canvas.create_image(0, 0, image = self.photo, anchor = tkinter.NW)
          # self.vid.imgplot.set_data(frame)
          # plt.pause(0.05)
         
          # else:                                       #Scanning 
        self.window.after(self.delay, self.update)   #Called every self.delay msec
          
    def ScanStack(self):
        global LiveViewFLG
        global ScanFLG
        global NFramAvg
        global ImStack
        global Stak_allslices
        global FirstLocFLG
        global LastLocFLG
      #  cnt=0;
        while ScanFLG:  #Will exit when Arduino says scan steps over
          WAITFLG=1
          while WAITFLG:
            while (arduino.inWaiting() <= 0):
              time.sleep(0.1) #jdfkd
            data=arduino.readline()
            print(int(data))
            print('Here0')
            if int(data) == 11:   #If the stack is complete
              print('Here1')
              Stak_allslices = np.array(ImStack)
              print('Here2')
              Fname=tkinter.filedialog.asksaveasfile()
              imageio.mimwrite(Fname.name + '.tiff',Stak_allslices)
    #          imwrite(Fname.name + '.tiff', Stak_allslices, imagej=True, resolution=(1./2.6755, 1./2.6755), metadata={'spacing': 3.947368, 'unit': 'um', 'axes': 'ZYX'})
              ImStack = [];
              WAITFLG=0    #Movement over because scan of stack over
              ScanFLG = 0  #Scan of all slices over. Live view can be started if needed
              FirstLocFLG = 0 #Conveying that the first and last needs to be set 
              LastLocFLG = 0  #Conveying that the last needs to be set
            if int(data) == 10:     #Waiting for movement over to start the read of frames for the next slice.
              WAITFLG=0       
          if (ScanFLG==1):    
            (rAvg, gAvg, bAvg) = (None, None, None)
            (grayAvg) = (None)
            total = 0
       # print('NFramAvg = ' + str(NFramAvg)) 
            for n in range(NFramAvg):    #Capturing FramAvg frames         
              if CVorPVCAM==1:
                ret, frame = self.vid.my_get_frame()
                (B, G, R) = cv2.split(frame.astype("float"))  #Split the frmae into its respective channels
        
                if rAvg is None:    # if the frame averages are None, initialize them
                  rAvg = R
                  bAvg = B
                  gAvg = G
                else:  # otherwise, compute the weighted average between the history of frames and the current frames
                  rAvg = ((total * rAvg) + (1 * R)) / (total + 1.0)
                  gAvg = ((total * gAvg) + (1 * G)) / (total + 1.0)
                  bAvg = ((total * bAvg) + (1 * B)) / (total + 1.0)
              # print('Total='+ str(total))
                avg = cv2.merge([bAvg, gAvg, rAvg]).astype("uint8")
                np_frame = np.array(avg)
            # cv2.imwrite(args["output"], avg)
            # np_frame = cv2.imread('video', avg)
          
            # if ret:
            #   self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(frame))
            # self.canvas.create_image(0, 0, image = self.photo, anchor = tkinter.NW)
            # print("Reached", ret)
              else:
                frame = self.vid.cam.get_frame(exp_time=Exp_time_live)
                if grayAvg is None:    # if the frame averages are None, initialize them
                  grayAvg = frame.astype("float")
                else:
                  grayAvg = ((total * grayAvg) + (1 * frame.astype("float"))) / (total + 1.0)
                np_frame = grayAvg.astype("uint16")
                     
              total += 1  # increment the total number of frames read thus far
                
            print(total)
            ImStack.append(np_frame)
               
                # while 1:
            arduino.write(bytes('12', 'utf-8'))  #Telling arduino slice complete.
            while (arduino.inWaiting() <= 0):  
              time.sleep(0.1) #jdfkd
              print('waiting')
            data=arduino.readline()
            print(int(data))
        
       

class MyVideoCapture:
    def __init__(self, CVorPVCAM, video_source):
        # Open the video source
        
        if CVorPVCAM == 1:  #WebCam openCV
          # print("Reached")
          self.cam = cv2.VideoCapture(video_source)
        
          if not self.cam.isOpened():
            raise ValueError("Unable to open video source", video_source)

        # Get video source width and height
          self.width = self.cam.get(cv2.CAP_PROP_FRAME_WIDTH)
          self.height = self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT)
        else:   #PVCAM
          # print("Reached")
          self.cam = next(Camera.detect_camera()) # Use generator to find first camera.  PVCAM
          self.cam.open()                         # Open the camera.  PVCAM
          self.width = 512
          self.height = 512
          self.exp_time=self.cam.exp_time         #Getting the exposure time
          # frame = self.cam.get_frame(exp_time=Exp_time_live)
          # self.imgplot = plt.imshow(frame)
          # plt.ion()
          
    def my_get_frame(self):
        if self.cam.isOpened():
            ret, frame = self.cam.read()
            if ret:
                # Return a boolean success flag and the current frame converted to BGR
                return (ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            else:
                return (ret, None)
        else:
            return (ret, None)
        
    # Release the video source when the object is destroyed
    def __del__(self):
        if self.cam.isOpened():
            self.cam.release()
            

# Create a window and pass it to the Application object App() with the arguments
App(tkinter.Tk(), window_title, video_source)

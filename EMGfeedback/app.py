from PyQt5.QtWidgets import QPushButton, QWidget, QLineEdit, QLabel
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal
from PyQt5.QtCore import Qt, QObject
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush

import os
os.add_dll_directory(r'C:/Program Files (x86)/VideoLAN/VLC')       # vlc directory for simple mp3 support
import vlc

import serial                       # serial port IO
import math
import pyaudio                      # audio generation
import numpy as np
from scipy import signal            # used for real-time lowpass butterworth-filter
import time                         # timer used for frequency modulation
#import matplotlib.pyplot as plt    # data plotting
import csv


def lowpass_butterworth(data):
    # create an order 3 lowpass butterworth filter
    b, a = signal.butter(3, 0.15)
    z = signal.lfilter_zi(b, a)
    result = np.zeros(data.size)
    for i, x in enumerate(data):
        result[i], z = signal.lfilter(b, 1, [x], zi=z)
    return np.ndarray.tolist(result)


''' Separate thread for audio pulse playback '''
class audioPlayer(QObject):
    
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.parent.playSound.connect(self.play)
    
    @pyqtSlot(str)
    def play(self, file):
        p = vlc.MediaPlayer(file)
        p.play()


''' Serial and audio IO in separate thread to keep GUI usable and responsive '''
class Loop(QObject):
    
    # signal slots for thread communication
    finished = pyqtSignal()
    update_button = pyqtSignal(list)
    output = pyqtSignal(int)
    variables = pyqtSignal(list)
    playSound = pyqtSignal(str)
    
    # sound playback variables
    CHUNK = 4096
    RATE = 44100
    _phase = 0

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.variables.connect(self.getVars)
        
        # initialize separate audioplayer thread for smoother feedback signal playback
        self.audioThread = QThread()
        self.player = audioPlayer(self)
        self.player.moveToThread(self.audioThread)
        self.audioThread.start()
        
        self.runStatus = False
        self.play_sound = True
        self.frequency = 1000
        self.modeTable = ['continuous frequency-modulated signal', 'discrete frequency-modulated signal',
                           'pulse-modulated signal', 'temporal frequency-modulated pattern signal']
        self.mode = 0
        self.target = 255
        self.margin = 10
        self.levels = 4
        
        self.frame = 0
        self.TT = time.time()
        self.oldfreq = 1000
        self.phase = 0
    
    # generate chunkwise sinewave of given frequency

    def callback(self, in_data, frame_count, time_info, status):
        if self.frequency != self.oldfreq:
            # start new sinewave from the same phase as where the previous left off
            self.phase = 2*np.pi*self.TT*(self.oldfreq-self.frequency)+self.phase
            self.oldfreq=self.frequency
        left = (np.sin(self.phase+2*np.pi*self.oldfreq*(self.TT+np.arange(frame_count)/float(self.RATE))))
        data = np.zeros((left.shape[0]*2,),np.float32)
        data[::2] = left
        data[1::2] = left
        self.TT+=frame_count/float(self.RATE)
        return (data, pyaudio.paContinue)

    
    @pyqtSlot(list)
    def getVars(self, varsLs):
        self.runStatus, self.mode, self.target, self.levels = varsLs[0], varsLs[1], varsLs[2], varsLs[3]
        self.run()

    def run(self):
        print("Thread start")
        self.update_button.emit(["Running...", False])
        p = pyaudio.PyAudio()
        fin_tone = "file:///tone.mp3"
        # continuous frequency-modulated audio stream
        stream = p.open(format = pyaudio.paFloat32,
                    channels = 2,
                    rate = self.RATE,
                    output = True,
                    stream_callback = self.callback) 
        if self.mode == 2:
            pulse = "file:///single_pulse.mp3"
            stream.stop_stream()
            self.frequency = 1000
        elif self.mode == 3:
            pulse = "file:///pulses.mp3"
            stream.stop_stream()
        ser = serial.Serial('COM3', 9600)
        count = np.int64(0)
        data = [0 for i in range(100)]              # for data filtering, windowed to 100 samples
        final = []                                  # for saving results
        mode = self.mode
        time_to_find = -1
        if self.levels > 10:
            self.levels = 10
        target_upper = (self.target+1) * (256/self.levels)
        target_lower = target_upper - (256/self.levels)
        
        # targetWPosL = wCenter + 1.6 * target_upper
        # targetWPosR = 1.6 * 256/self.levels
        print("upper: {}, lower: {}\ntarget: {}, levels: {}".format(target_upper, target_lower, self.target, self.levels))
        
        level_factor = 256 // self.levels
        pulseDelay = 1
        target_time = time.time()
        start = time.time()
        fin = time.time()
        while True:
            
            if self.parent.runLoop == False:
                break
            # read serial data
            line = ser.readline().decode().strip()
            try:
                # moving average smoothing done on controller
                output = int(line)
            except (ValueError, TypeError) as e:
                print("{}: Invalid data - {}", e, line)
                break
            
            if len(data) >= 99:
                data.pop(0)
            data.append(output)
            # apply low-pass filter
            data = lowpass_butterworth(np.array(data))
            # amplify and clamp signal after filtering
            output = np.multiply(data[-1], 150)
            if output > 255:
                output = 255
            if output < -255:
                output = -255
            final.append(output)
            self.output.emit(output)
            print(output)
            
            # change audio feedback parameters based on serial output
            if mode == 0:      # continuous frequency-modulated signal
                self.frequency = (1000 + output)/2
            elif mode == 1:    # discrete frequency-modulated signal
                self.frequency = (1000 + 50 * (output // level_factor))/2
                
            elif mode == 2 or mode == 3:    # temporal frequency-modulated signal   
                Aoutput = abs(output)
                if mode == 2 and Aoutput > 256 - (256/self.levels):
                    pulseDelay = 100
                    stream.start_stream()
                else:
                    if mode == 2:
                        stream.stop_stream()
                    if Aoutput == 0 or Aoutput// level_factor == 0:
                        pulseDelay = 100
                    else:
                        pulseDelay = (self.levels - (Aoutput // level_factor)) * (1/self.levels)
                    #print("output: {}, output // level_factor: {}, pulseDelay: {}".format(output, output // level_factor, pulseDelay))
                    
                    
            # control feedback pulse delay
            if mode == 2 or mode == 3:
                if time.time() - start > pulseDelay:
                    self.playSound.emit(pulse)
                    start = time.time()
            
            count += 1
            # check and control target intensity
            if output < target_lower or output > target_upper:
                # reset target timer
                target_time = time.time()
            # if target is held for more than 1 second, play tone as sign of success
            if time.time() - target_time >= 1:
                self.playSound.emit(fin_tone)
                time_to_find = time.time() - fin
                QThread.sleep(1)
                break
            
        #plt.plot(data)
        stream.close()
        ser.close()
        self.update_button.emit(["Finished", True])
        print("Thread complete")
        self.parent.runLoop = False
        with open('EMGdata.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([self.modeTable[self.mode], 'target: {}'.format(self.target), 'margin: {}'.format(self.margin),
                             'time to find and hold 1s: {}'.format(time_to_find)])
            writer.writerow(final)
            writer.writerow([])
        self.finished.emit()
        

''' GUI '''
class EMGApp(QWidget):
    
    
    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height
        
        # connect worker thread slots
        self.loop = Loop(self)
        self.loop.finished.connect(self.stop)
        self.loop.update_button.connect(self.updateButton)
        self.loop.output.connect(self.getOutput)
        self.workerThread = QThread()
        self.loop.moveToThread(self.workerThread)
        self.workerThread.start()

        self.initUI()
        
        self.runLoop = False
        self.mode = 0           # mode variable, see keyPressEvent()
        self.output = 0         # used for drawing cursor from worker thread
        self.target = 0         # target value. -100=full extension, 0=neutral position, 100=full flexion
        self.levels = 4         # amount of discrete levels in feedback, default = 4
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.grabKeyboard()
        self.setEnabled(True)
        self.show()
        
        
    def initUI(self):
        btn = QPushButton("Run continuous frequency-modulated signal", self)
        btn.setStyleSheet("QPushButton { background-color: green; color: white }"
                        "QPushButton:disabled { background-color: red; color: white }")
        btn.setGeometry(self.width/2-200, self.height/2-300, 400, 75)
        btn.clicked.connect(self.run)
        self.btn = btn
        
        self.targetTextbox = QLineEdit(self)
        self.targetTextbox.setGeometry(self.width/2-300, self.height/2-275, 50, 25)
        self.targetTextbox.setPlaceholderText('0')
        l1 = QLabel(self)
        l1.setText("Set target level")
        l1.setGeometry(self.width/2-320, self.height/2-300, 100, 25)
        self.levelsTextbox = QLineEdit(self)
        self.levelsTextbox.setGeometry(self.width/2+250, self.height/2-275, 50, 25)
        self.levelsTextbox.setPlaceholderText('4')
        l2 = QLabel(self)
        l2.setText("Set number of feedback levels")
        l2.setGeometry(self.width/2+210, self.height/2-300, 150, 25)

    def run(self):
        if self.runLoop == False:
            self.runLoop = True
            try:
                self.target = int(self.targetTextbox.text())
            except ValueError:
                self.target = 1
            try:
                self.levels = int(self.levelsTextbox.text())
            except ValueError:
                self.levels = 4
            self.loop.variables.emit([self.runLoop, self.mode, self.target, self.levels])
            
        else:
            self.runLoop = False
    
    @pyqtSlot()
    def stop(self):
        self.runLoop = False
        
    @pyqtSlot(int)
    def getOutput(self, output):
        if self.runLoop == True:
            self.output = output
            self.repaint()

    @pyqtSlot(list)
    def updateButton(self, ls):
        self.btn.setText(ls[0])
        self.btn.setEnabled(ls[1])
        
    def paintEvent(self, event):
        #if self.runLoop == False:
        #    return
        wCenter = self.width/2
        hCenter = self.height/2
        cursorWPos = wCenter + 3 * (self.output)
        
        target_upper = self.target * (256/self.levels)
        if self.target >= 0:
            target_lower = target_upper - (256/self.levels)
        else:
            target_lower = target_upper + (256/self.levels)
        targetWPosL = wCenter + 3 * target_upper
        targetWPosR = 3 * 256/self.levels
        
        painter = QPainter(self)
        painter.begin(self)
        brush = QBrush(Qt.darkGray)
        # coloured cursor indicators
        if self.output >= 0:
            painter.setPen(QPen(QColor(0, 255, 0, 64)))
            brush.setColor(QColor(0, 255, 0, 128))
            painter.fillRect(wCenter, hCenter - 50, 3 * (self.output), 100, brush)
        else:
            painter.setPen(QPen(QColor(255, 0, 0, 64)))
            brush.setColor(QColor(255, 0, 0, 128))
            painter.fillRect(cursorWPos, self.height/2 - 50, wCenter-cursorWPos, 100, brush)
        # target intensity area
        brush.setColor(QColor(0, 0, 0, 32))
        painter.setPen(QPen(Qt.black, 2))
        painter.fillRect(targetWPosL, hCenter-50, targetWPosR, 100, brush)
        # line
        painter.setPen(QPen(Qt.black, 4))
        painter.drawLine(140, self.height/2, self.width - 140, hCenter)
        painter.setPen(QPen(Qt.darkGray, 2))
        painter.drawLine(140, self.height/2, self.width - 140, hCenter)
        # cursor
        painter.drawLine(cursorWPos, hCenter + 50, cursorWPos, hCenter - 50)
        
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Space:
            self.run()
        if key == Qt.Key_1:
            self.mode = 0
            self.btn.setText("Run continuous frequency-modulated signal")
        if key == Qt.Key_2:
            self.mode = 1
            self.btn.setText("Run discrete frequency-modulated signal")
        if key == Qt.Key_3:
            self.mode = 2
            self.btn.setText("Run temporal frequency modulated pulse signal")
        if key == Qt.Key_4:
            self.mode = 3
            self.btn.setText("Run temporal frequency modulated pattern signal")

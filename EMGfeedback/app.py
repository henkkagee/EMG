from PyQt5.QtWidgets import QPushButton, QWidget, QLineEdit, QLabel
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal
from PyQt5.QtCore import Qt, QObject
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush

import os
os.add_dll_directory(r'C:/Program Files (x86)/VideoLAN/VLC')       # vlc directory for easy mp3 support
import vlc

import serial                    # serial port IO
import math
import pyaudio                   # audio generation
import numpy as np               # audio generation
import time                      # timer used for frequency modulation
import matplotlib.pyplot as plt  # data plotting
import csv
import wave

''' Separate thread for audio pulse player '''
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
        
    def sine(self, current_time):
    
        length = self.CHUNK
        factor = float(self.frequency) * (math.pi * 2) / self.RATE
        this_chunk = np.arange(length) + current_time
        return np.sin(this_chunk * factor)

    def get_chunk(self):
        data = self.sine(time.time())
        return data * 0.1
        
    def callback(self, in_data, frame_count, time_info, status):
        chunk = self.get_chunk() * 0.25
        data = chunk.astype(np.float32).tostring()
        return (data, pyaudio.paContinue)
    
    @pyqtSlot(list)
    def getVars(self, varsLs):
        self.runStatus, self.mode, self.target, self.margin = varsLs[0], varsLs[1], varsLs[2], varsLs[3]
        self.levels = varsLs[4]
        self.run()

    def run(self):
        print("Thread start")
        self.update_button.emit(["Running...", False])
        p = pyaudio.PyAudio()
        fin_tone = "file:///tone.mp3"
        if 0 <= self.mode <= 1:
            # continuous frequency-modulated audio stream
            stream = p.open(format = pyaudio.paFloat32,
                        channels = 2,
                        rate = self.RATE,
                        output = True,
                        stream_callback = self.callback) 
        elif self.mode == 2:
            start = time.time()
            pulse = "file:///single_pulse.mp3"
        else:
            start = time.time()
            pulse = "file:///pulses.mp3"
        ser = serial.Serial('COM3', 9600)
        count = 0
        data = []
        mv_avg = [0 for i in range(5)]      # moving average
        mv_avg_idx = 0
        #plt.ion()                # used for realtime plotting
        #fig=plt.figure()         # create new figure on each function call
        counter = 0
        time_to_find = -1
        if self.levels > 10:
            self.levels = 10
        level_factor = 256//self.levels
        target_time = time.time()
        start = time.time()
        while True:
            if self.parent.runLoop == False:
                break
            
            # read serial data
            line = ser.readline().decode().split('-')
            try:
                flex, ext = int(line[0]), int(line[1])
                res = flex - ext
                mv_avg[mv_avg_idx] = res
                output = sum(mv_avg) / 5
            except (ValueError, TypeError) as e:
                print("{}: Invalid data", e)
                break
            
            # change audio feedback parameters based on serial output
            if self.mode == 0:      # continuous frequency-modulated signal
                self.frequency = 1000 + output
            elif self.mode == 1:    # discrete frequency-modulated signal
                self.frequency = 1000 + 50 * (output//level_factor)
            elif self.mode == 2:    # temporal frequency-modulated signal         
                if output == 0 or output//level_factor == 0:
                    pipfrequency = 0
                else:
                    pipfrequency = 1 / (output//level_factor)
            elif self.mode == 3:     # temporal frequency-modulated pattern signal
                if output == 0 or output//level_factor == 0:
                    pipfrequency = 0
                else:
                    pipfrequency = 1 / (output//level_factor)
            
            # control feedback pulse delay
            if self.mode == 2 or self.mode == 3:
                if time.time() - start > pipfrequency:
                    self.playSound.emit(pulse)
                    start = time.time()
            
            
            #plt.scatter(count, output, s=1, c='black')        # realtime plotting not needed
            #plt.show()
            #plt.pause(0.0001)
            count += 1
            
            if mv_avg_idx >= 4:
                mv_avg_idx = 0
            else:
                mv_avg_idx += 1
            
            # check and control target intensity
            if self.target - self.margin >= output <= self.target + self.margin:
                # reset target timer
                target_time = time.time()
            # if target is held for more than 1 second, play tone as sign of success
            if time.time() - target_time >= 1:
                self.playSound.emit(fin_tone)
                time_to_find = time.time() - start
            else:
                start = time.time()
            data.append(output)
            self.output.emit(output)
            
        if (0 >= self.mode <= 1):
            stream.close()
        ser.close()
        self.update_button.emit(["Finished", True])
        print("Thread complete")
        self.parent.runLoop = False
        with open('EMGdata.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([self.modeTable[self.mode], 'target: {}'.format(self.target), 'margin: {}'.format(self.margin),
                             'time to find and hold 1s: {}'.format(time_to_find)])
            writer.writerow(data)
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
        self.output = 0       # used for drawing cursor from worker thread
        self.target = 0         # target value. -100=full extension, 0=neutral position, 100=full flexion
        self.margin = 10        # size of target area / 2
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
        l1.setText("Set target intensity")
        l1.setGeometry(self.width/2-320, self.height/2-300, 100, 25)
        self.levelsTextbox = QLineEdit(self)
        self.levelsTextbox.setGeometry(self.width/2+250, self.height/2-275, 50, 25)
        self.levelsTextbox.setPlaceholderText('4')
        l2 = QLabel(self)
        l2.setText("Set amount of feedback levels")
        l2.setGeometry(self.width/2+210, self.height/2-300, 150, 25)

    def run(self):
        if self.runLoop == False:
            self.runLoop = True
            try:
                self.target = int(self.targetTextbox.text())
            except ValueError:
                self.target = 255
            try:
                self.levels = int(self.levelsTextbox.text())
            except ValueError:
                self.levels = 4
            # amount of levels on both flexor and extensor side, hence *2
            self.loop.variables.emit([self.runLoop, self.mode, round(2.55 * self.target), self.margin, self.levels*2])
            
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
        cursorWPos = wCenter + 1.6 * (self.output)
        targetWPosL = wCenter + 1.6 * round(self.target * 2.55) - self.margin*2.55*1.6
        targetWPosR = 2*self.margin*2.55*1.6
        
        painter = QPainter(self)
        painter.begin(self)
        brush = QBrush(Qt.darkGray)
        # coloured cursor indicators
        if self.output >= 0:
            painter.setPen(QPen(QColor(0, 255, 0, 64)))
            brush.setColor(QColor(0, 255, 0, 128))
            painter.fillRect(wCenter, hCenter - 50, 1.6 * (self.output), 100, brush)
        else:
            painter.setPen(QPen(QColor(255, 0, 0, 64)))
            brush.setColor(QColor(255, 0, 0, 128))
            painter.fillRect(cursorWPos, self.height/2 - 50, wCenter-cursorWPos, 100, brush)
        # target intensity area
        brush.setColor(QColor(0, 0, 0, 32))
        painter.setPen(QPen(Qt.black, 2))
        painter.fillRect(targetWPosL, hCenter-50, targetWPosR, 100, brush)        # line
        painter.setPen(QPen(Qt.black, 4))
        painter.drawLine(195, self.height/2, self.width - 195, hCenter)
        painter.setPen(QPen(Qt.darkGray, 2))
        painter.drawLine(195, self.height/2, self.width - 195, hCenter)
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
            self.btn.setText("Run interval-frequency modulated pulse signal")
        if key == Qt.Key_4:
            self.mode = 3
            self.btn.setText("Run interval-frequency modulated pattern signal")

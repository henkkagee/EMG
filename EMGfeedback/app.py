from PyQt5.QtWidgets import QPushButton, QWidget, QLineEdit, QLabel, QCheckBox, QRadioButton
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
import random


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
    
    @pyqtSlot(list)
    def play(self, ls):
        if ls[0] == "visual":
            return
        p = vlc.MediaPlayer(ls[1])
        p.play()


''' Serial and audio IO in separate thread to keep GUI usable and responsive '''
class Loop(QObject):
    
    # signal slots for thread communication
    finished = pyqtSignal()
    update_button = pyqtSignal(list)
    output = pyqtSignal(list)
    variables = pyqtSignal(list)
    playSound = pyqtSignal(list)
    
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
        
        self.play_sound = True
        self.frequency = 1000
        self.modeTable = ['continuous frequency-modulated signal', 'discrete frequency-modulated signal',
                           'pulse-modulated signal', 'temporal frequency-modulated pattern signal']
        self.value = 0
        self.testSuite = "audiovisual"
        
        self.frame = 0
        self.TT = time.time()
        self.oldfreq = 1000
        self.phase = 0
        
        random.seed()
    
    # generate chunkwise sinewave of given frequency

    def callback(self, in_data, frame_count, time_info, status):
        if self.frequency != self.oldfreq:
            # start new sinewave from the same phase as where the previous left off
            self.phase = 2*np.pi*self.TT*(self.oldfreq-self.frequency)+self.phase
            self.oldfreq=self.frequency
        left = (np.sin(self.phase+2*np.pi*self.oldfreq*(self.TT+np.arange(frame_count)/float(self.RATE))))
        if self.testSuite == "visual":
            left = np.zeros(frame_count)
        data = np.zeros((left.shape[0]*2,),np.float32)
        if self.value > 0:
            data[::2] = np.zeros(frame_count)
            data[1::2] = left
        elif self.value  < 0:
            data[::2] = left
            data[1::2] = np.zeros(frame_count)
        else:
            data[::2] = left
            data[1::2] = left
        self.TT+=frame_count/float(self.RATE)
        return (data, pyaudio.paContinue)

    
    @pyqtSlot(list)
    def getVars(self, varsLs):
        mode, target, levels, numberOfTests = varsLs[0], varsLs[1], varsLs[2], varsLs[3]
        targets = []
        test = varsLs[4]
        self.testSuite = varsLs[5]
        # generate array of evenly distributed targets within range
        if test == True:
            k = -levels
            while k <= levels:
                for i in range(0, numberOfTests//(levels * 2)):
                    targets.append(k)
                k += 1
            while len(targets) < 50:
                targets.append(random.randint(-levels, levels))
        else:
            targets = []
        print(targets)
        print("Len: {}".format(len(targets)))
        self.run(mode, target, levels, targets, test)

    def run(self, mode, target, levels, targets, test):
        
        stop = False
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
        if mode == 2:
            pulse = "file:///single_pulse.mp3"
            stream.stop_stream()
            self.frequency = 1000
        elif mode == 3:
            pulse = "file:///pulses.mp3"
            stream.stop_stream()
        ser = serial.Serial('COM3', 9600)
        
        toggle_neutral_target = 0
        ignore = False                  # Ignore every other test for normalizing results
        
        while True:
            if test == True:
                if len(targets) > 0:
                    ''' Every other target is 0 (neutral) '''
                    if toggle_neutral_target % 2 == 0:
                        target = 0
                        ignore = True
                    else:
                        target = targets.pop(random.randint(0, len(targets) - 1))
                        ignore = False
            count = np.int64(0)
            data = [0 for i in range(100)]              # Data filtering, windowed to 100 samples
            final = []                                  # Final results
            final_flex = []
            final_ext = []
            mode = mode
            time_to_find = -1
            if levels > 10:
                levels = 10
            if target == 0:
                target_upper = 20
                target_lower = -20
            else:
                sign = lambda i: (i>0) - (i<0)
                target_upper = target * (256/levels)
                target_lower = target_upper - sign(target) * (256/levels)
            
            print("upper: {}, lower: {}\ntarget: {}, levels: {}".format(target_upper, target_lower, target, levels))
            
            level_factor = 256 // levels
            pulseDelay = 1
            target_time = time.time()
            start = time.time()
            fin = time.time()
            while True:
                
                if self.parent.runLoop == False:
                    stop = True
                    break
                # read serial data
                line = ser.readline().decode().strip().split('x')
                try:
                    # moving average smoothing done on controller
                    output = int(line[0])
                    flex = int(line[1])
                    ext = int(line[2])
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
                if ignore == False:
                    final.append(output)
                    final_flex.append(flex)
                    final_ext.append(ext)
                    
                self.value  = output
                self.output.emit([output, flex, ext, target])
                Aoutput = abs(output)
                print("lower: {}, upper: {}, output: {}, target_time: {}".format(target_lower, target_upper, output, time.time() - target_time))
                # change audio feedback parameters based on serial output
                if mode == 0:      # continuous frequency-modulated signal
                    self.frequency = (1000 + Aoutput)/2
                elif mode == 1:    # discrete frequency-modulated signal
                    self.frequency = (1000 + 50 * (Aoutput // level_factor))/2
                    
                elif mode == 2 or mode == 3:    # temporal frequency-modulated signal   
                    if Aoutput > 256 - (256/levels):
                        pulseDelay = 100
                        stream.start_stream()
                    else:
                        stream.stop_stream()
                        if Aoutput == 0 or Aoutput// level_factor == 0:
                            pulseDelay = 100
                        else:
                            pulseDelay = (levels - (Aoutput // level_factor)) * (1/levels)
                        #print("output: {}, output // level_factor: {}, pulseDelay: {}".format(output, output // level_factor, pulseDelay))
                        
                        
                # control feedback pulse delay
                if mode == 2 or mode == 3:
                    if time.time() - start > pulseDelay:
                        if self.value  > 0:
                            if mode == 2:
                                self.playSound.emit("file:///single_pulse_right.mp3")
                            else:
                                self.playSound.emit("file:///pulses_right.mp3")
                        elif self.value  < 0:
                            if mode == 2:
                                self.playSound.emit("file:///single_pulse_left.mp3")
                            else:
                                self.playSound.emit("file:///pulses_left.mp3")
                        else:
                            self.playSound.emit([self.testSuite, pulse])
                        start = time.time()
                
                count += 1
                # check and control target intensity
                if target == 0:
                    if output <= -20 or output >= 20:
                        # reset target timer
                        target_time = time.time()
                elif target > 0:
                    if output <= target_lower or output >= target_upper:
                        # reset target timer
                        target_time = time.time()
                elif target < 0:
                    if output <= target_upper or output >= target_lower:
                        # reset target timer
                        target_time = time.time()
                # if target is held for more than 1 second, play tone as sign of success
                if time.time() - target_time >= 1:
                    self.playSound.emit([self.testSuite, fin_tone])
                    time_to_find = time.time() - fin
                    break
                
            #plt.plot(data)
            if ignore == False:
                with open('EMGdata.csv', 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([self.testSuite, self.modeTable[mode], 'target%: {}'.format(target/levels), 'target area%: {}'.format((256//levels)/256),
                                     'time to find and hold 1s: {}'.format(time_to_find)])
                    writer.writerow(final)
                    writer.writerow([])
            
            if len(targets) == 0 or stop == True:
                break
            toggle_neutral_target += 1
            
        stream.close()
        ser.close()
        self.finished.emit()
        self.update_button.emit(["Finished", True])
        print("Thread complete")


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
        
        self.runLoop = False
        self.mode = 0                   # mode variable, see keyPressEvent()
        self.output = 0                 # used for drawing cursor from worker thread
        self.flex = 0
        self.ext = 0
        self.target = 0                 # target value. -100=full extension, 0=neutral position, 100=full flexion
        self.levels = 4                 # amount of discrete levels in feedback, default = 4
        self.numberOfTargets = 50       # number of individual targets in test suite
        self.testSuite = "audiovisual"
        self.test = False
        
        self.initUI()
        
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
        
        self.radiobuttonAudioVisual = QRadioButton(self)
        self.radiobuttonAudioVisual.setGeometry(self.width/2 + 450, self.height/2 - 310, 150, 25)
        self.radiobuttonAudioVisual.setText("Audio + visual feedback")
        self.radiobuttonAudioVisual.mode = "audiovisual"
        self.radiobuttonAudioVisual.toggled.connect(self.onClicked)
        self.radiobuttonAudio = QRadioButton(self)
        self.radiobuttonAudio.setGeometry(self.width/2 + 450, self.height/2 - 280, 150, 25)
        self.radiobuttonAudio.setText("Audio feedback only")
        self.radiobuttonAudio.mode = "audio"
        self.radiobuttonAudio.toggled.connect(self.onClicked)
        self.radiobuttonVisual = QRadioButton(self)
        self.radiobuttonVisual.setGeometry(self.width/2 + 450, self.height/2 - 250, 150, 25)
        self.radiobuttonVisual.setText("Visual feedback only")
        self.radiobuttonVisual.mode = "visual"
        self.radiobuttonVisual.toggled.connect(self.onClicked)
        
        self.checkboxMode = QCheckBox(self)
        self.checkboxMode.setGeometry(self.width/2 - 550, self.height/2 - 280, 150, 25)
        self.checkboxMode.setText(f"Run test with {self.numberOfTargets} targets?")
        self.checkboxMode.toggled.connect(self.checkboxToggle)
        
    def onClicked(self):
        radioButton = self.sender()
        if radioButton.isChecked():
            mode = radioButton.mode
            self.testSuite = mode
    
    def checkboxToggle(self):
        if self.test == False:
            self.test = True
        else:
            self.test = False

    def run(self):
        if self.runLoop == False:
            self.runLoop = True
            try:
                self.target = int(self.targetTextbox.text())
            except ValueError:
                ''' test mode, generates an evenly distributed array of 50 different targets within level range '''
                self.target = 0
            try:
                self.levels = int(self.levelsTextbox.text())
            except ValueError:
                self.levels = 4
            self.loop.variables.emit([self.mode, self.target, self.levels, self.numberOfTargets, self.test, self.testSuite])
            
        else:
            self.runLoop = False
    
    @pyqtSlot()
    def stop(self):
        self.runLoop = False
        
    @pyqtSlot(list)
    def getOutput(self, output):
        if self.runLoop == True:
            self.output = output[0]
            self.flex = output[1]
            self.ext = output[2]
            self.target = output[3]
            self.repaint()

    @pyqtSlot(list)
    def updateButton(self, ls):
        self.btn.setText(ls[0])
        self.btn.setEnabled(ls[1])
        
    def paintEvent(self, event):
        wCenter = self.width/2
        hCenter = self.height/2
        painter = QPainter(self)
        painter.begin(self)
        if self.testSuite == "audio":
            painter.drawText(wCenter, hCenter, f"Target: {self.target}")
            return
        cursorWPos = wCenter + 3 * (self.output)
        flexPos = wCenter + 3 * (self.flex)
        extPos = wCenter - 3 * (self.ext)
        
        target_higher = self.target * (256/self.levels)
        if self.target == 0:
            targetWPosL = wCenter - 20
            targetWPosR = 40
        else:
            if self.target > 0:
                target_lower = target_higher - (256/self.levels)
                targetWPosL = wCenter + 3 * target_higher - 3 * 256/self.levels
                targetWPosR = 3 * 256/self.levels
            elif self.target < 0:
                target_lower = target_higher * (256/self.levels)
                targetWPosL = wCenter + 3 * target_higher
                targetWPosR = 3 * 256/self.levels
        brush = QBrush(Qt.darkGray)
        # coloured cursor indicators
        if self.output >= 0:
            painter.setPen(QPen(QColor(0, 255, 0, 64)))
            brush.setColor(QColor(0, 255, 0, 128))
            painter.fillRect(wCenter, hCenter - 50, 3 * (self.output), 100, brush)
        else:
            painter.setPen(QPen(QColor(255, 0, 0, 64)))
            brush.setColor(QColor(255, 0, 0, 128))
            painter.fillRect(cursorWPos, hCenter - 50, wCenter-cursorWPos, 100, brush)
        
        # target intensity area
        brush.setColor(QColor(0, 0, 0, 32))
        painter.setPen(QPen(Qt.black, 2))
        painter.fillRect(targetWPosL, hCenter-50, targetWPosR, 100, brush)
        # line
        painter.setPen(QPen(Qt.black, 4))
        painter.drawLine(140, hCenter, self.width - 140, hCenter)
        painter.setPen(QPen(Qt.darkGray, 2))
        painter.drawLine(140, hCenter, self.width - 140, hCenter)
        # cursor
        painter.drawLine(cursorWPos, hCenter + 50, cursorWPos, hCenter - 50)
        
        painter.setPen(QPen(QColor(0, 255, 0, 64)))
        brush.setColor(QColor(0, 255, 0, 128))
        painter.fillRect(wCenter, hCenter + 150, 3 * (self.flex), 100, brush)
        
        painter.setPen(QPen(QColor(255, 0, 0, 64)))
        brush.setColor(QColor(255, 0, 0, 128))
        painter.fillRect(extPos, hCenter + 150, wCenter-extPos, 100, brush)
        # line for flexor and extensor values
        painter.setPen(QPen(Qt.black, 4))
        painter.drawLine(140, hCenter + 200, self.width - 140, hCenter + 200)
        painter.setPen(QPen(Qt.darkGray, 2))
        painter.drawLine(140, hCenter + 200, self.width - 140, hCenter + 200)
        # cursor for flexor
        painter.drawLine(flexPos, hCenter + 150, flexPos, hCenter + 250)
        # cursor for extensor
        painter.drawLine(extPos, hCenter + 150, extPos, hCenter + 250)
        
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

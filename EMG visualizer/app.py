from PyQt5.QtWidgets import QPushButton, QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal
from PyQt5.QtCore import Qt, QObject
import serial                    # serial port IO
import math
import pyaudio                   # audio generation
import numpy as np               # audio generation
import time                      # timer used for frequency modulation
import datetime
import matplotlib.pyplot as plt  # data plotting
import csv
import wave

    
''' Serial and audio IO in separate thread to keep GUI usable and responsive '''
class Loop(QObject):
    
    # signal slots for thread communication
    requestSignal = pyqtSignal()
    runLoop = pyqtSignal(bool)
    finished = pyqtSignal()
    update_button = pyqtSignal(list)
    
    # sound playback variables
    CHUNK = 4096
    RATE = 44100
                          
    def __init__(self):
        super().__init__()
        self.runLoop.connect(self.get_run_status)
        self.runStatus = True
        self.play_sound = True
        self.pipfrequency = 1
        self.frequency = 0
        
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
    
    @pyqtSlot(bool)
    def get_run_status(self, status):
        self.runStatus = status
    
    def run(self, mode):
        print("Thread start")
        self.update_button.emit(["Running...", False])
        
        p = pyaudio.PyAudio()
        if 0 <= mode <= 1:
            stream = p.open(format = pyaudio.paFloat32,    # stream1 for continuous playback
                        channels = 2,
                        rate = self.RATE,
                        output = True,
                        stream_callback = self.callback)
        else:
            wf = wave.open('1khz.wav', 'rb')
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)
            start = time.time()
        ser = serial.Serial('COM3', 9600)    

        count = 0
        data = []
        mv_avg = [0 for i in range(5)]      # moving average
        mv_avg_idx = 0
        
        plt.ion()
        fig=plt.figure()        # create new figure on each function call
        self.runStatus = True
        wfData = None
        
        while True:
            if self.runStatus == False:
                break
            line = ser.readline().decode().split('-')
            try:
                flex, ext = int(line[0]), int(line[1])
                res = (flex - ext)/2 + 255
                mv_avg[mv_avg_idx] = res
                output = sum(mv_avg) / 5
            except (ValueError, TypeError) as e:
                print("{}: Invalid data", e)
                break
            
            if mode == 0:      # continuous frequency-modulated signal
                self.frequency = 1000 + 2 * output    
            elif mode == 1:    # discrete frequency-modulated signal, 4 levels
                self.frequency = 1000 + 100 * (output//64)
            elif mode == 2:    # pulse-modulated signal 4 levels, still quite clumsy
                self.frequency = 1000           
                if output == 0:
                    self.pipfrequency = 0
                else:
                    self.pipfrequency = 1 / (output//64)
                
            if mode == 2 or mode == 3:
                if time.time() - start > self.pipfrequency:
                    wfData = wf.readframes(self.CHUNK)
                    stream.write(wfData)
                    wf.rewind()
                    start = time.time()
                    
            else:
                data.append(output)
            
            #plt.scatter(count, output, s=1, c='black')        # need to find more efficient plotting method
            #plt.show()
            plt.pause(0.0001)
            count += 1
            if count % 10 == 0:
                self.requestSignal.emit()
            if mv_avg_idx >= 4:
                mv_avg_idx = 0
            else:
                mv_avg_idx += 1
        stream.close()
        ser.close()
        self.finished.emit()
        self.update_button.emit(["Finished", True])
        print("Thread complete")
        self.runStatus = False
        with open('EMGdata.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(map(lambda x: [x], data))
            

''' GUI '''
class EMGApp(QWidget):
    
    def __init__(self):
        super().__init__()
        
        # create QThread and use it for reading data
        thread = QThread(self)
        thread.start()
        self.loop = Loop()
        self.loop.moveToThread(thread)
        
        self.loop.requestSignal.connect(self.send_run_status)
        self.loop.finished.connect(self.stop)
        self.loop.update_button.connect(self.updateButton)

        self.setGeometry(600, 270, 500, 400)
        btn = QPushButton("Run continuous frequency-modulated signal", self)
        btn.setStyleSheet("QPushButton { background-color: green; color: white }"
                        "QPushButton:disabled { background-color: red; color: white }")
        btn.setFixedSize(250, 50)
        btn.clicked.connect(self.run)
        self.btn = btn
        
        lay = QVBoxLayout(self)
        lay.addWidget(self.btn, alignment=Qt.AlignCenter)
        self.runLoop = False
        self.mode = 0
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.grabKeyboard()
        self.setEnabled(True)
        self.show()

    def run(self):
        if self.runLoop == False:
            self.runLoop = True
            self.loop.run(self.mode)
        else:
            self.runLoop = False
    
    @pyqtSlot()
    def stop(self):
        self.runLoop = False
    
    @pyqtSlot()
    def send_run_status(self):
        self.loop.runLoop.emit(self.runLoop)

    @pyqtSlot(list)
    def updateButton(self, ls):
        self.btn.setText(ls[0])
        self.btn.setEnabled(ls[1])
        
    def keyPressEvent(self, event):
        print("Keyevent fetched")
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
            self.btn.setText("Run pulse-modulated signal")
        if key == Qt.Key_4:
            self.mode = 3
            self.btn.setText("Run pattern-modulated signal")

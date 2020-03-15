from PyQt5.Qt import QWidget, QTextBrowser
from PyQt5.QtWidgets import QPushButton
from PyQt5 import QtCore
import serial   # for reading the data via COM serial port 
import re       # regex for parsing the data
import math     # needed for handling audio data
import pyaudio  # signal generation

class EMGApp(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        self.stop = False
        #self.serialport = serial.Serial('COM3', 9600)

        #text = QLabel(self)
        #text.setGeometry(200, 600, 400, 75)
        #text.setText("Tryck pa en prisklass eller anvand kodlasaren")
        #self.text = text

        red = QPushButton(self)
        red.setStyleSheet("background-color: black")
        red.setGeometry(350, 200, 100, 100)
        self.red = red 
        red.clicked.connect(self.loop)
    
    
    def loop(self):
        textbr = QTextBrowser()
        
        
        with serial.Serial('COM3', 9600) as ser:
            while 1:
                line = str(ser.readline())
                line = line.split()
                
                sensor1 = line[0].strip()
                searchObj = re.match('\d+', sensor1)
                if searchObj:
                    textbr.setText("group(): " + searchObj.group())
                else:
                    textbr.setText("Nothing found!\n")
                
                sensor2 = line[1].strip()
                searchObj = re.match('\d+', sensor2)
                if searchObj:
                    textbr.setText("group(): " + searchObj.group())
                else:
                    textbr.setText("Nothing found!\n")
                    
                output = line[2].strip()
                searchObj = re.match('\d+', output)
                if searchObj:
                    textbr.setText("group(): " + searchObj.group())
                else:
                    textbr.setText("Nothing found!\n")
                
                if self.stop == True:
                    break
                
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            self.stop = True
            

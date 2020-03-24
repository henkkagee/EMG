'''import serial
import wave
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import wavfile
import time



def readAndOutput():
    plt.ion()
    fig=plt.figure() 
    
    i=0
    x=list()
    y=list()
    i=0
    ser = serial.Serial('COM3',9600)
    ser.close()
    ser.open()
    len = 0
    t = time.perf_counter()
    while True:
    
        if len >= 300:
            break
        data = ser.readline()
        #print(data.decode())
        x.append(i)
        y.append(data.decode().split('-')[0])
    
        plt.scatter(i, float(data.decode().split('-')[0]))
        #plt.plot(i, abs(np.fft.rfft(data.decode().split('-')[0], )))
        i += 1
        plt.show()
        plt.pause(0.0001)  # Note this correction
        len += 1
    
    elapsed_time = time.perf_counter() - t
    data2 = np.asarray(y, dtype=np.int16)
    wavfile.write('test.wav', 44100, data2)
    ser.close()
    return elapsed_time
    
def main():
    time = readAndOutput()
    print("Time is {}".format(time))
    
    wr = wave.open('test.wav', 'r')
    sz = 44100 # Read and process 1 second at a time.
    da = np.frombuffer(wr.readframes(sz), dtype=np.int16)
    left = da
    
    rate = len(left)/time
    i = 0
    k = 0
    measure = []        # in milliseconds
    while i < len(left):
        k = 0
        while k < 1000/rate:
            measure.append(left[i])
            k += 1
        i += 1
    
    lf= abs(np.fft.rfft(left))
    
    plt.figure(1)
    a = plt.subplot(211)
    a.set_ylim([0, 255])
    a.set_xlabel('time [s]')
    a.set_ylabel('sample value [-]')
    x = np.arange(len(left))
    plt.plot(x, left)
    b = plt.subplot(212)
    b.set_ylim([0, 2000])
    b.set_xscale('log')
    b.set_xlabel('frequency [Hz]')
    b.set_ylabel('|amplitude|')
    plt.plot(lf)
    plt.savefig('sample-graph.png')

    
main()
'''
'''
from datetime import datetime
from matplotlib import pyplot
from matplotlib.animation import FuncAnimation
from random import randrange

x_data, y_data = [], []

figure = pyplot.figure()
line, = pyplot.plot_date(x_data, y_data, '-')

def update(frame):
    x_data.append(datetime.now())
    y_data.append(randrange(0, 100))
    line.set_data(x_data, y_data)
    figure.gca().relim()
    figure.gca().autoscale_view()
    return line,

animation = FuncAnimation(figure, update, interval=200)

pyplot.show()

'''

# Back up the reference to the exceptionhook
#sys._excepthook = sys.excepthook

'''def custom_exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys.excepthook(exctype, value, traceback)
    sys.exit(1)


sys.excepthook = custom_exception_hook'''


gt = [0 for i in range(5)]
print(gt)

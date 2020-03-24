import time
import numpy
import pyaudio
import math

CHUNK = 4096
RATE = 44100

def sine(current_time):
    
    sine.frequency = sine.frequency + 5
    length = CHUNK
    factor = float(sine.frequency) * (math.pi * 2) / RATE
    this_chunk = numpy.arange(length) + current_time
    #this_chunk[0] = 1.58429704e+09
    #sine.previous = numpy.arange(length)[length-1]
    return numpy.sin(this_chunk * factor)

sine.frequency = 440
sine.previous = None
sine.first = True

def get_chunk():
    data = sine(time.time())
    return data * 0.1

def callback(in_data, frame_count, time_info, status):
    chunk = get_chunk() * 0.25
    data = chunk.astype(numpy.float32).tostring()
    return (data, pyaudio.paContinue)

p = pyaudio.PyAudio()
stream = p.open(format = pyaudio.paFloat32,
                channels = 2,
                rate = RATE,
                output = True,
                stream_callback = callback)

stream.start_stream()

while stream.is_active():
    time.sleep(0.1)

stream.stop_stream()
stream.close()
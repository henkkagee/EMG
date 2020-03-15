# Generate a 440 Hz square waveform in Pygame by building an array of samples and play
# it for 5 seconds.  Change the hard-coded 440 to another value to generate a different
# pitch.
#
# Run with the following command:
#   python pygame-play-tone.py

from array import array
from time import sleep
import numpy

import pygame
from pygame.mixer import Sound, get_init, pre_init

class Note(Sound):

    def __init__(self, frequency, volume=.1):
        self.frequency = frequency
        Sound.__init__(self, buffer = self.build_samples())
        self.set_volume(volume)

    def build_samples(self):
        sample_rate = pygame.mixer.get_init()[0]
        period = int(round(sample_rate / self.frequency))
        amplitude = 2 ** (abs(pygame.mixer.get_init()[1]) - 1) - 1
    
        def frame_value(i):
            return amplitude * numpy.sin(2.0 * numpy.pi * self.frequency * i / sample_rate)
    
        return numpy.array([frame_value(x) for x in range(0, period)]).astype(numpy.int16)

if __name__ == "__main__":
    pre_init(44100, -16, 1, 1024)
    pygame.init()
    Note(440).play(-1)
    print("played")
    sleep(5)
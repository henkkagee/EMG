import pyaudio
import numpy as np
import math

def play_tone(frequency, dur):
    p = pyaudio.PyAudio()
    volume = 0.8     # range [0.0, 1.0]
    fs = 44100       # sampling rate, Hz, must be integer
#   duration = 0.3   # in seconds, may be float
    duration=dur    #"dur" parameter can be removed and set directly
    f=frequency

    # We need to ramp up (I used an exponential growth formula)
    # from low volume to the volume we want.
    # For some reason (I can't bothered to figure that out) the
    # following factor is needed to calculate how many steps are
    # needed to reach maximum volume:
    # 0.693147 = -LN(0.5)

    stepstomax = 50
    stepstomax_mod = int(round(stepstomax/0.693147)) 
    ramprate  = 1/(math.exp(0.5)*stepstomax_mod)

    decayrate = 0.9996
    #Decay could be programmed better. It doesn't take tone duration into account.
    #That means it might not reach an inaudible level before the tone ends. 

    #sine wave
    samples1=(np.sin(2*np.pi*np.arange(0,fs*duration,1)*f/fs))

    stepcounter=0
    for nums in samples1:
        thisnum=samples1[stepcounter]
        if stepcounter<stepstomax_mod:
            #the ramp up stage
            samples1[stepcounter]=volume*thisnum*(pow(ramprate+1,stepcounter+1)-1)
        else:
            #the decay stage
            samples1[stepcounter]=volume*thisnum*(pow(decayrate,stepcounter-stepstomax)) 
        stepcounter+=1

    samples = samples1.astype(np.float32).tobytes()
    stream = p.open(format=pyaudio.paFloat32,
        channels=1,
        rate=fs,
        output=True)        
    stream.write(samples)
    stream.stop_stream()
    stream.close()
    p.terminate()

play_tone(261.6, 0.3)
play_tone(329.6, 0.3)
play_tone(392, 0.3) 
play_tone(523.3, 0.6)
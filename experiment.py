from settings import *
from gui import *
from logger import *
from packet_listener import *
import sys
import os.path
import random.choice

def build_experiment():
    experiment = []

    # build trials from grating list
    for grating in GRATINGS:
        if (grating=="h"):
            experiment.append(("vStimHorizontal", DURV))
        else:
            experiment.append(("vStimVertical", DURV))
        experiment.append(DELAY)
        for i in xrange(3):
            experiment.append(("aStim", FREQ, DURA))
            experiment.append(DURAWAIT)
        experiment.append(calcITIr())
    
    experiment.reverse()
    return experiment

def calcITIr():
    """ ITI with jitter
    """
    return ITI + random.choice(xrange(-JITTER, JITTER))

def startui(logname):
    experiment = build_experiment()
    logger=Logger(logname)    
    pl = PacketListener(logger)
    pl.start()
    app = Application(None, experiment, [2], logger, pl)
    app.mainloop()
    logger.closefile()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python experiment.py logname")
    else:
        startui(sys.argv[1])

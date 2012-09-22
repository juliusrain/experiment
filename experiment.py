from settings import *
from gui import *
from logger import *
from packet_listener import *
import sys
import os.path

def build_experiment():
    experiment = []
    for grating in GRATINGS:
        if (grating=="h"):
            experiment.append(("vStimHorizontal", DURV))
        else:
            experiment.append(("vStimVertical", DURV))
        for i in xrange(3):
            experiment.append(("aStim", FREQ, DURA))
            experiment.append(DURAWAIT)
    
    experiment.reverse()
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

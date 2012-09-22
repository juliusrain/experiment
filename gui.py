'''
Created on Jul 24, 2011

@author: matt
'''
#!/usr/local/bin/python     
from Tkinter import *
import time
from threading import *
from win32con import WM_SETFOCUS
from win32gui import GetFocus, SetFocus, SendMessage
from win32api import GetSystemMetrics,GetMonitorInfo,EnumDisplayDevices
from threading import Timer
from winsound import Beep

class Application(Frame):              
    def __init__(self, master=None, fullExperiment=[], blockIndices=[], logger=None, pl=None):
        self.fullExperiment = fullExperiment #preserve the whole experiment data structure
        self.experiment = self.fullExperiment #use self.experiment for jumping around without losing data
        self.blockIndices = blockIndices
        self.logger = logger
        self.rects = {}
        self.grating={}
        self.numRects = 4
        self.firstFocus = True
        self.stimOnMessages = {1:"Stim\t1", 2:"Stim\t2", 3:"Stim\t3", 4:"Stim\t4"}
        self.stimOffMessages = {1:"Clear\t1", 2:"Clear\t2", 3:"Clear\t3", 4:"Clear\t4"}
        self.currentBlock = 0
        self.pl = pl
        #self.pl.startTest() # TEMPORARY FIX -- for timer drift test March 27 2012
        self.t = Timer(1000, self.runexperiment)
        self.startTesting = False
        self.waitForTrigger = False
        Frame.__init__(self, master)   
        self.grid()                    
        self.create_widgets()
        self.set_keybinds()

    def create_widgets(self):
        #self.quitButton = Button ( self, text='Quit', command=self.master.destroy)        
        #self.quitButton.grid()
        #self.startButton = Button (self, text='Start',command=self.runexperiment)
        #self.startButton.grid()
        
        # determine size of rectangles based on monitor size
        self.width = GetSystemMetrics(0)
        #self.width = 1280
        self.height = GetSystemMetrics(1)
        #self.height = 800
		
		#display1 monitor size
        #self.displaywidth1 = 1366
        self.displaywidth1 = 0
		
        self.borderSize = self.width / 20
        self.canvas = Canvas(self, width=self.width, height=self.height, background="gray")
        self.canvas.grid()
        self.squareWH = (self.width / self.numRects) - 2 * (self.borderSize)
        self.master.geometry("+" + str(self.displaywidth1) + "+0")
        
        # Draw fixation cross
        self.makeFixCross()
        self.makeControlWin()
        
        # draw the squares
##        for i in range(self.numRects):
##            self.rectX = i * (self.width / self.numRects) + self.borderSize
##            self.rectY = (self.height / 2) - (self.squareWH / 2)
##            self.rects[i + 1] = self.canvas.create_rectangle(self.rectX, self.rectY, self.rectX + self.squareWH, self.rectY + self.squareWH)
##            self.canvas.itemconfigure(self.rects[i + 1], fill='light gray')

		# Maximize window:
        #self.master.wm_state('zoomed')
        
        # Remove maximize button:
        #self.master.resizable(False,False)
		
    def makeControlWin(self):
        self.controlWin = Toplevel(self.master)
        self.controlCanvas = Canvas(self.controlWin, width=300, height=300)
        self.controlCanvas.grid()
        self.controlWin.title("CONTROL")
        self.quitButt = Button(self.controlCanvas, text='QUIT', command=self.quitButtonCmd)
        self.quitButt.grid(row=4, columnspan=6)
        self.goButt = Button(self.controlCanvas, text='START/RESUME', command=self.runexperiment)
        self.goButt.grid(row=0, columnspan=6)
        self.waitButt = Button(self.controlCanvas, text='Start on next Trigger...', command=self.waitForTrig)
        self.waitButt.grid(row=1, columnspan=6)
        self.waitButt.config(background="white")
        # self.waitButt.config(state=DISABLED) used to be diabled
        # run-from-block text
        self.rfbText = Label(self.controlCanvas, text="Current Block:")
        self.rfbText.grid(row=2, columnspan=6)
        # run-from-block radio buttons
        self.runFromBlock = IntVar()
        self.runFromBlock.set(0)
        self.rfbRadio = self.blockIndices[:]
        for block in range(len(self.blockIndices)):
            self.rfbRadio[block] = Radiobutton(self.controlCanvas, text=str(block + 1), variable=self.runFromBlock, value=block, indicatoron=0, command=self.changeBlock)
            self.rfbRadio[block].grid(row=3, column=block)
            # select first block by default
            if(block == 0):
                self.rfbRadio[block].select()
            
    def makeFixCross(self):
        # calculate fixed cross geometry as percentage of screen space
        self.fixCrossSize = 0.020
        self.fixCrossWH = self.fixCrossSize * self.width
        self.fixCrossThick = self.height / 200
        self.fixCross = {}
        
        # create window
##        self.fixCrossWin = Toplevel(self.master)
##        self.fixCrossCanvas = Canvas(self.fixCrossWin, width=self.width, height=self.height, background='gray')
##        self.fixCrossCanvas.grid()
        
        # maximize and remove resize button
        #self.fixCrossWin.state('zoomed')
        #self.fixCrossWin.resizable(False, False)
        
        # draw the fixation cross
        self.fixCross[1] = self.canvas.create_rectangle((self.width / 2) - (self.fixCrossThick / 2), (self.height / 2) - (self.fixCrossWH / 2), (self.width / 2) + (self.fixCrossThick / 2), (self.height / 2) + (self.fixCrossWH / 2))
        self.fixCross[2] = self.canvas.create_rectangle((self.width / 2) - (self.fixCrossWH / 2), (self.height / 2) - (self.fixCrossThick / 2), (self.width / 2) + (self.fixCrossWH / 2), (self.height / 2) + (self.fixCrossThick / 2))
        self.canvas.itemconfigure(self.fixCross[1], fill='red', outline='red')
        self.canvas.itemconfigure(self.fixCross[2], fill='red', outline='red')
		
##        self.fixCrossWin.geometry("+" + str(self.displaywidth1) + "+0")
        
        #self.fixCrossWin.focusmodel(ACTIVE)
        # wait and exit
#        self.after(time, self.closeFixCrossWin())

    def makeVGrating(self):
        # calculate grating as a percentage of screen space
        self.lineHeight = 100
        self.lineWidth = 5
        self.grating = {}

        # draw the grating

        for i in xrange(20):
            self.grating[i] = self.canvas.create_rectangle((3*self.width/4)+i*self.lineWidth+1, (3*self.height/4), (3*self.width/4) + (i+1)*self.lineWidth, (3*self.height/4)+self.lineHeight)
            if i%2 == 1:
                color = 'black'
            else:
                color = 'white'
            self.canvas.itemconfigure(self.grating[i], fill=color, outline=color)
            
    def makeHGrating(self):
        # calculate grating as a percentage of screen space
        self.lineHeight = 5
        self.lineWidth = 100
        self.grating = {}

        # draw the grating

        for i in xrange(20):
            self.grating[i] = self.canvas.create_rectangle((3*self.width/4), (3*self.height/4)+i*self.lineHeight+1, (3*self.width/4)+self.lineWidth, (3*self.height/4)+(i+1)*self.lineHeight)
            if i%2 == 1:
                color = 'black'
            else:
                color = 'white'
            self.canvas.itemconfigure(self.grating[i], fill=color, outline=color)
            
    def clearGrating(self):
        for i in xrange(len(self.grating)):
            self.canvas.delete(self.grating[i])
        self.runexperiment()

    def playAudioStim(self, freq, length):
        Beep(freq, length)
        self.runexperiment()

    def quitButtonCmd(self):
        self.pl.alive = 0
        #self.pl.close_connection()
        time.sleep(1.5)
        self.master.destroy()
        
    def showFixCross(self, time):
        
        if(self.firstFocus == False):
            self.fixCrossWin.focus_force()
            SendMessage(self.hwnd, WM_SETFOCUS, None, None)
            #SetFocus(self.hwnd)
            
        # focus on the fixation cross window
        self.fixCrossWin.focus_force()
        
        if(self.firstFocus == True):
            self.hwnd = GetFocus()
            #print "hwnd: " + str(self.hwnd)
            self.firstFocus = False
            
        #self.fixCrossWin.focus_set()s
        # log the presentation of the cross
        self.logger.write("FIXCROSS")
        
        # focus on the main window again and run it
        self.after(time, self.hideFixCrossWin)
        
    def hideFixCrossWin(self):
        self.focus_force()
        #self.focus_set()
        # extra one-second delay before next step so the transition isn't so jarring
        self.after(1000, self.runexperiment)
        
    def changeBlock(self):
        self.currentBlock = self.runFromBlock.get()
        print "Now starting from block: " + str(self.currentBlock+1)
        # change the experiment stack to start at the beginning of the selected block
        newStartIndex = self.blockIndices[self.currentBlock]
        self.experiment = self.fullExperiment[:-newStartIndex]
    
    def waitForTrig(self):
        #print self.runFromBlock.get()
        self.waitForTrigger = True
        self.pl.waitForTrig(self.waitForTrigger,self.goButt)
        self.waitButt.config(background="red")
        self.waitButt.config(state=DISABLED)
        

    def keyPress(self, event):
        pressed = event.char
        for k in self.rectKey:
            if (pressed == self.rectKey[k]):
                self.logResponse(k)
                print 'Response ' + str(k)
                
    def set_keybinds(self):
        self.master.bind('<Key>', self.keyPress)
        
        self.rectKey = {}
        self.rectKey[1] = 'j'
        self.rectKey[2] = 'k'
        self.rectKey[3] = 'l'
        self.rectKey[4] = ';'
    
    def stimAll(self):
        for rect in range(self.numRects):
            if (rect + 1) in self.rects:
                self.canvas.itemconfigure(self.rects[rect + 1], fill='maroon')
                
    def clearAll(self):
        for rect in range(self.numRects):
            if (rect + 1) in self.rects:
                self.canvas.itemconfigure(self.rects[rect + 1], fill='light gray')
        self.runexperiment()

        
    def stim(self, rect):
        if rect in self.rects:
            self.canvas.itemconfigure(self.rects[rect], fill='maroon')
            self.logger.write(str(self.stimOnMessages[rect]))
    
    def clear(self, rect):
        if rect in self.rects:
            self.canvas.itemconfigure(self.rects[rect], fill='light gray')
            self.logger.write(str(self.stimOffMessages[rect]))
            self.runexperiment()
            
    def logResponse(self, target):
        #target is an int representing the key corresponding to a square 1..4
        self.logger.write("Response " + str(target))
		
    def pauseExperiment(self,pauseTime):
        
        #DISABLED: Suspect in the case of the spazzy scanning session. Stops Chris from pressing the "start" button between blocks.
        # re-enable all buttons
        #for block in range(len(self.blockIndices)):
        #    self.rfbRadio[block].config(state=NORMAL)
        #self.rfbText.config(state=NORMAL)
        #self.goButt.config(state=NORMAL)
        # self.waitButt.config(state=NORMAL)

        #self.startTesting = False
        print "Block finished. Paused for " + str(pauseTime/1000) +  " seconds\n"
        
        self.t = Timer(pauseTime/1000, self.runexperiment)
        self.t.start()
        #self.pl.pauseTest() # TEMPORARY COMMENTED -- for timer drift test March 27 2012
    
    def runexperiment(self):
        if not self.startTesting:
            print "Testing..."
            self.startTesting = True
            self.pl.startTest();
            
            if(self.waitForTrigger==True):
                self.waitForTrigger = False
                self.waitButt.config(background="white")
                #self.waitButt.config(state=ENABLED) #should only be doing this at the start of the experiment
            
            # grey-out all the buttons and stuff
            for block in range(len(self.blockIndices)):
                self.rfbRadio[block].config(state=DISABLED)
            self.rfbText.config(state=DISABLED)
            self.goButt.config(state=DISABLED)
            self.waitButt.config(state=DISABLED)
            
        if self.experiment:
            instruction = self.experiment.pop()
            # an integer is a simple wait
            if type(instruction) == type(int()):
                # Log the ISI, wait, and execute next instruction
                self.logger.write("ISI")
                self.t = Timer(float(instruction) / 1000, self.clearAll)
                self.t.start()
            elif type(instruction) == type(tuple()):
                if(instruction[0] == 'flash'):
                    # instruction of 'flash' flashes all rects
                    self.stimAll()
                    self.logger.write("FLASH")
                    self.t = Timer(float(instruction[1]) / 1000, self.clearAll)
                    self.t.start()
                elif(instruction[0] == 'fix'):
                    # instruction of 'fix' presents the fixation cross
                    self.showFixCross(instruction[1])
                elif(instruction[0] == 'vStimVertical'):
                    self.makeVGrating()
                    self.logger.write("visual stim vertical")
                    self.t = Timer(float(instruction[1]) / 1000, self.clearGrating)
                    self.t.start()
                elif(instruction[0] == 'vStimHorizontal'):
                    self.makeHGrating()
                    self.logger.write("visual stim horizontal")
                    self.t = Timer(float(instruction[1]) / 1000, self.clearGrating)
                    self.t.start()
                elif(instruction[0] == 'aStim'):
                    # instruction[1] contains frequency (Hz) and instruction[2] contains length (ms)
                    self.logger.write("audio stim %d Hz" % int(instruction[1]))
                    self.playAudioStim(int(instruction[1]), int(instruction[2]))
                elif(instruction[0] == 'TrialStart'):
                    # instruction[2] will contain the number of the trial
                    self.logger.write("TRIALSTART\t" + str(instruction[2]))
                    print ""
                    print "Starting Trial #" + str(instruction[2])
                    self.t = Timer(float(instruction[1]) / 1000, self.clearAll)
                    self.t.start()
                elif(instruction[0] == 'blockBreak'):
                    # instruction of 'blockBreak' waits between blocks
                    self.logger.write("BLOCKBREAK\t" + str(instruction[2]))
                    # set the radio button for the next block
                    if not (self.currentBlock == len(self.blockIndices)-1):
                        self.currentBlock+=1
                        self.rfbRadio[self.currentBlock].select()
                    #if we are done, finish up. At most we will have one element after
                    #the last block break (a fixation cross) so if there is more than
                    #one instruction left pause the experiment, otherwise finish up right
                    #away
                    print ""
                    #print "Instructions remaining: " + str(len(self.experiment))#DEBUG:
                    #if there is one instruction remaining, it is a fixation cross, so run one last time
                    if len(self.experiment) <= 1:
                        self.runexperiment()
                    else:
                        #otherwise pause and wait for input
                        self.pauseExperiment(instruction[1])
    
					
                elif(instruction[0] == 'BlockStart'):
                    # instruction[2] will have the description of the block (eg. "Day 2 Block 1") 
                    self.logger.write("BlockStart\t" + str(instruction[2]))
                    print "Starting Block #" + str(instruction[2])
                    self.t = Timer(0.0, self.clearAll)
                    self.t.start()
                else:
                    # simple stim instruction
                    self.stim(instruction[0])
                    # print str(instruction[0]), # print stim id
                    print ".", #print a dot
                    self.t = Timer(float(instruction[1]) / 1000, self.clear, (instruction[0],))
                    self.t.start()
        else:
            #self.pauseExperiment()
            print "Experiment complete"

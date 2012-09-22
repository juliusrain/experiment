'''
Created on Aug 1, 2011

@author: matt
Updated by avrum, Nov. 7, 2011

Heavily modified and updated by Joseph Thibodeau, Nov 2011 - April 2012
'''
import threading
import time
from packet import Packet
import serial
from threading import Timer
import string
#import reedsolomon
from struct import unpack
import ctypes


"""
This class is a daemon thread that listens forever for incoming packets and logs their contents.
"""
class PacketListener(threading.Thread):
    def __init__(self, logger):
        threading.Thread.__init__(self)
        self.logger = logger
#        self.c = reedsolomon.Codec(15, 11, 4)
        self.setUpRS()
        self.daemon = True
        self.arm_port_list = [7]
        self.opto_port_list = [4]
        self.ser = {}
        self.alive = 1
        self.ARM_port = 0
        self.opto_port = 0
#        self.OKToLog = False
        self.startTesting = False
        self.inBuffer = {}
        self.optoboard_init_config()
        self.serial_init()
        self.setup_ARM(self.ARM_port)
        self.key_msg = None
        self.key_msg_parsed = None
        self.keyID = None
        self.keyType = None
        self.tempBuffer = ''
        self.DEBUG = False
        self.waitForTrigger = False
    
    def setUpRS(self):
        # Set up data structures for use in ctypes
#        message = ctypes.c_int8*11
#        parity = ctypes.c_int8*4
        self.rs = ctypes.cdll.LoadLibrary('librs.dll')
        self.rs.init_rs()
        codedMessageArray = ctypes.c_int8*15
        self.RSDataLength = 11
        self.message = codedMessageArray()
        
    def startTest(self):
        self.startTesting = True
        
    # debilitating this function for now. Always logging.
    def pauseTest(self):
        # self.startTesting = False
        self.startTesting = True
        
    def waitForTrig(self,value,goButton):
        self.waitForTrigger = value
        self.goButton = goButton
        
    def run(self):
        # Spawn a timer in 2000ms to make a fake keypress every 1 second --- JT
        # self.metro(2000)
        self.messagecount = 0
        while self.alive == 1:
            
            self.serial_readMessages(self.ARM_port)
            
            # if we have found some status messages in the serial data, display them
            if(self.DEBUG==True):
                if len(self.outStatus) > 0:
                    for message in self.outStatus:
                        print "+++++++\r\nSTATUS: " + message
                        
            # if we have found some data messages in the serial data, decode and log them
            if len(self.outData) > 0:
                for message in self.outData:
                    if(self.DEBUG==True):
                        print "*******\r\nDATA\r\nLENGTH: " + str(len(message)) + "\r\nRAW: " + repr(message)
                        
                    # in a normal test scenario before the experiment starts,
                    # output a "message received" type of thing so that the experimenter
                    # knows whether (a) the person presses a key and (b) whether there
                    # is unending data streaming in thru the PSoC1, indicating a need to
                    # re-plug everything
                    if not self.DEBUG:
                        if not self.startTesting:
                            print ".",
                        
                    # parse the binary data from the PSoC if it is the right length
                    if len(message) == 15:
                        # parse out the hex data
                        unpacked = unpack('BBBBBBBBBBBBBBB', message)
                        hexed = bytearray(unpacked)
                        
                        # RS-decode
                        try:
                            # fill a c-type array with the encoded message:
                            for e in range(len(hexed)):
                                self.message[e] = hexed[e]
                                
                            # decode the message using ctypes rs codec
                            # note: self.message will be modified in-place if errors exist!
                            decoded = self.rs.eras_dec_rs(self.message,0,0)
                            
                            # Determine the type of message:
                            self.keyID = self.message[0]
                            # if the key number is zero, this is a trigger
                            if(self.keyID == 0):
                                self.keyType = 'keyTRIG'
                                #if we are waiting for the trigger signal to start logging, this is when we start logging
                                if(self.waitForTrigger == True):
                                    self.waitForTrigger = False # Disable WaitForTrigger
                                    self.startTesting = True
                                    self.goButton.invoke() #get the GUI to start presenting material

                            # otherwise this is a keyup, keydown, or positional measure
                            else:
                                # the 2nd and 3rd columns give us the type of non-trigger message
                                self.keyID = (self.message[1] * 16) + self.message[2]
                                if (self.keyID == 127):
                                    self.keyType = 'keyUP'
                                elif (self.keyID == 0):
                                    self.keyType = 'keyDN'
                                else:
                                    self.keyType = 'keyPOS'

#                            # create a human-readable log string
                            logstring = ''
                            
#                            # add the numerical value from each decoded element
                            for element in range(self.RSDataLength):
                                logstring = logstring + '\t' + str(self.message[element])
                                
                            if(self.DEBUG==True):
                                print self.keyType + logstring

                            if(self.startTesting==True):
                                self.logger.writeKey(self.keyType,logstring)
                        
                        except:
                            print "Unable to decode:" + repr(hexed)
                    else:
                        print "Incorrect message length:" + repr(message)

        #set self.alive=0 whenever program quits,
        #otherwise the port will remain open and the process will have to be killed manually!
        self.close_connection()
        print "Packet Listener Stopped"
        
    def metro(self, time):
        # set PSoC metronome to 1Hz
        self.ser[self.ARM_port].writelines("KF 1\r\n")
        # enable metronome reporting
        print "Metronome Command Sent"
        self.t = Timer(float(time) / 1000, self.ser[self.ARM_port].writelines, ("KM\r\n",))
        self.t.start()

    def close_connection(self):
        for port_num in self.arm_port_list:
            try:
                self.ser[port_num].writelines("!ud\r\n") #send stop printing command
                time.sleep(0.5)
                self.ser[port_num].close()
                time.sleep(0.5)
            except:
                print("can't close port:", port_num)
                
    def optoboard_init_config(self):
        for port_num in self.opto_port_list:
            try:
                self.ser[port_num] = serial.Serial(port_num-1,115200,timeout=.001)
                #port_num is decremented due to zero-index base with pySerial
                self.ser[port_num].writelines("\r\n \r\n")
                self.serial_read(port_num, 100)
                for line in self.inBuffer[port_num]:
                    if ("$PSOC:" in line):
                        self.opto_port = port_num
            except:
                print ("opto port not opening, ensure that the port number is correct: ", port_num)
                
            try:
                #put setup commands here
                self.ser[self.opto_port].writelines("SbL 0S1 1S1 2S1 3S1\r\n") #keyboard mapped normally
                #self.ser[self.opto_port].writelines("SbL 7D1 4D1 6D1 0D1\r\n") #keyboard mapped inverse (Penhune Lab)
                self.serial_read(self.opto_port, 100)
                print ("In Opto Buffer: ", self.inBuffer[self.opto_port])
                time.sleep(0.5)
                self.ser[self.opto_port].writelines("Sc 500\r\n")
                self.serial_read(self.opto_port, 100)
                print ("In Opto Buffer: ", self.inBuffer[self.opto_port])
                time.sleep(0.5)
            except:
                print "can't write to opto port:" +  str(self.opto_port)
                
            for port_num in self.opto_port_list:
                try:
                    self.ser[self.opto_port].close()
                    time.sleep(0.5)
                except:
                    print "can't close opto port:" + str(self.opto_port)

    def serial_init(self):
        for port_num in self.arm_port_list:
            try:
                self.ser[port_num] = serial.Serial(port_num-1,115200,timeout=.001)
                #port_num is decremented due to zero-index base with pySerial
                self.ser[port_num].writelines("\r\n \r\n")
                self.serial_read(port_num, 100)
                for line in self.inBuffer[port_num]:
                    if ("ARM$" in line):
                        self.ARM_port = port_num
            except:
                print ("arm port not opening, ensure that the port number is correct: ", port_num)

    def setup_ARM(self, ARM_port):
        try:
            #put setup commands here
            self.ser[ARM_port].writelines("!ud\r\n")
            self.serial_read(ARM_port, 100)
            time.sleep(0.5)
            print ("In ARM Buffer: ", self.inBuffer[ARM_port])
            self.ser[ARM_port].writelines("FR\r\n") #read saved calibration
            self.serial_read(ARM_port, 300)
            time.sleep(0.5)
            print ("In ARM Buffer: ", self.inBuffer[ARM_port])
            self.ser[ARM_port].writelines("KF 300\r\n")
            self.serial_read(ARM_port, 100)
            time.sleep(0.5)
            print ("In ARM Buffer: ", self.inBuffer[ARM_port])
            self.ser[ARM_port].writelines("!ie\r\n")
            self.serial_read(ARM_port, 100)
            print ("In ARM Buffer: ", self.inBuffer[ARM_port])
            time.sleep(0.5)
            self.ser[ARM_port].writelines("Kre\r\n")
            self.serial_read(ARM_port, 100)
            print ("In ARM Buffer: ", self.inBuffer[ARM_port])
            time.sleep(0.5)
            self.ser[ARM_port].writelines("Re\r\n")
            self.serial_read(ARM_port, 100)
            print ("In ARM Buffer: ", self.inBuffer[ARM_port])
            time.sleep(0.5)
            self.ser[ARM_port].writelines("Ad\r\n")
            self.serial_read(ARM_port, 100)
            print ("In ARM Buffer: ", self.inBuffer[ARM_port])
            time.sleep(0.5)
            self.ser[ARM_port].writelines("Be\r\n")
            self.serial_read(ARM_port, 100)
            print ("In ARM Buffer: ", self.inBuffer[ARM_port])
            time.sleep(0.5)
         
            print "SUCCESS!!!!!1one"
        except:
            print ("can't write to port:", ARM_port)

        #we will want to set up opto-boards here too!
        #however they have different commands and port number, and shouldn't be treated the same
        
    #OLD CODE --- NOW DEPRECIATED DEC2-2011 JT
    def serial_read(self, port_num,max_lines):
        self.OKToLog = False
        try:
            if(self.ser[port_num].inWaiting() > 0):
                self.inBuffer[port_num] = self.ser[port_num].readlines(max_lines)
                self.OKToLog = True
            else:
                self.inBuffer[port_num] = ""
        except:
            print ("Could not read from port: ", port_num)
            
    def parse_bracketed(self,s,l,r,min,max):
        # s = string, l = left-bracket character, r = right-bracket character
        lbrace = 0
        rbrace = 0

        #find left and right delimiters
        rbrace = string.find(self.tempBuffer,r,min,max)
        #if we find an rbrace we want to find a corresponding lbrace to the LEFT of the rbrace
        if rbrace != -1:
            lbrace = string.rfind(self.tempBuffer,l,min,rbrace)
            
        return [lbrace,rbrace]

    def serial_readMessages(self, port_num):
        self.outStatus = []
        self.outData = []
        try:
            #if serial data is waiting
            if((self.ser[port_num].inWaiting() > 0)):
                #read all the waiting data
                self.inBuffer[port_num] = self.ser[port_num].read(int(self.ser[port_num].inWaiting()))
                #append the waiting data to an accumulation string
                self.tempBuffer = self.tempBuffer + self.inBuffer[port_num]
                if(self.DEBUG==True):
                    print "======="
                    print "INPUT BUFF: " + repr(self.inBuffer[port_num])
                    print "TEMP BUFF: " + repr(self.tempBuffer)
                buff_length = len(self.inBuffer)
                
                #Now parse out messages surrounded by braces and brackets.
                limit = [0,0]
                while limit[0] != -1 and limit[1] != -1:
                    # find a right and left brace
                    limit = self.parse_bracketed(self.tempBuffer,'{','}',0,len(self.tempBuffer))
                    # if we found a right but not a left, search again but after the first right brace
                    if limit[0] == -1 and limit[1] != -1:
                        limit = self.parse_bracketed(self.tempBuffer,'{','}',limit[1]+1,len(self.tempBuffer))
              
                    # we found both right and left!
                    if limit[0] != -1 and limit[1] != -1:
                        # output the stuff between braces as a status message
                        self.outStatus.append(self.tempBuffer[limit[0]+1:limit[1]])
                        # strip off the substring we just found (-1 is the last character in an array)
                        self.tempBuffer = self.tempBuffer[limit[1]+1:len(self.tempBuffer)]
                        print "{ " + str(limit[0]) + " : " + str(limit[1]) + " }"    
                            
                limit = [0,0]
                while limit[0] != -1 and limit[1] != -1:
                    # find a right and left brace
                    limit = self.parse_bracketed(self.tempBuffer,'[',']',0,len(self.tempBuffer))
                    # if we found a right but not a left, search again but after the first right brace
                    if limit[0] == -1 and limit[1] != -1:
                        limit = self.parse_bracketed(self.tempBuffer,'[',']',limit[1]+1,len(self.tempBuffer))
                        
                    # we found both right and left!
                    if limit[0] != -1 and limit[1] != -1:
                        # output the stuff between braces as a status message
                        self.outData.append(self.tempBuffer[limit[0]+1:limit[1]])
                        # strip off the substring we just found (-1 is the last character in an array)
                        self.tempBuffer = self.tempBuffer[limit[1]+1:len(self.tempBuffer)]
                        if(self.DEBUG==True):
                            print "[ " + str(limit[0]) + " : " + str(limit[1]) + " ]"  
                
            else:
#                print("nothing in serial buffer")
                return ""
        except:
            print ("Could not read from port:", port_num)
            raise
            return ""

    def ARM_calibrate(self):
        print ("Calibrate ARM in this function")

#System
import threading
import time
import sys
from queue import Queue

#Syspaths
sys.path.insert(0, '/home/pi/Desktop/Griffin')
sys.path.insert(0, '/home/pi/Desktop/Reworked Project/manager')
sys.path.insert(0, '/home/pi/Desktop/Reworked Project/listener')

#Project
#from rest import RestServer

from deviceManager import DeviceManager
from motionManager import MotionManager

from turnListener import TurnListener
from touchListener import TouchListener
from verification import Verification
from executioner import Executioner

from events import AboartEvent

class Controller:
    
    def __init__(self):
        self.initManager()
        #self.startRestServer()
        self.start()
        
    def start(self):

        self.bareSignalsLock = threading.Lock()
        self.signalsLock = threading.Lock()

        self.bareSignals = []
        self.signals = []
        
        turnThread = TurnListener(self.bareSignals, self.bareSignalsLock)
        touchThread = TouchListener(self.bareSignals, self.bareSignalsLock)

        verificationThread = Verification(self.bareSignals, self.bareSignalsLock, self.signals, self.signalsLock)
        executionerThread = Executioner(self.signals, self.signalsLock)
        
        turnThread.start()
        touchThread.start()
        verificationThread.start()
        executionerThread.start()

        #self.test1()
        #self.test2()
        time.sleep(5)
        print('Now')
        self.signalsLock.acquire()
        self.signals.append(AboartEvent(time.time()))
        self.signalsLock.release()
        
        turnThread.join()
        touchThread.join()
        verificationThread.join()
        executionerThread.join()
        
        print('Controller wird beendet')

    def test1(self):
        while True:
            self.bareSignalsLock.acquire()
            print(self.bareSignals)
            self.bareSignalsLock.release()
            time.sleep(4)
            

    def test2(self):
        while True:
            self.signalsLock.acquire()
            print(self.signals)
            self.signalsLock.release()
            time.sleep(4)

    def startRestServer(self):
        restServer = RestServer()
        restServer.start()

    def initManager(self):
        deviceManager = DeviceManager()
        deviceManager.initDevices()
        
        motionManager = MotionManager()
        motionManager.initMotions()
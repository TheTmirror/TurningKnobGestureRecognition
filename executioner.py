# -*- coding: utf-8 -*-
#System
import threading
import sys

#System Paths
sys.path.insert(0, '/home/pi/Desktop/Reworked Project/manager')
sys.path.insert(0, '/home/pi/Desktop/api/subscription')

from events import BaseEvent, RotationEvent, ButtonEvent, AboartEvent
from events import EVENT_BASE, EVENT_ROTATE, EVENT_BUTTON, EVENT_ABOART

from myMath import Calculator
from ipc import IPCMemory
from transformer import MotionTransformer

from motionManager import MotionManager

from SubscriptionService import SubscriptionService
from Event import Event

class Executioner(threading.Thread):

    def __init__(self, signals, signalsLock):
        threading.Thread.__init__(self)

        self.signals = signals
        self.signalsLock = signalsLock
        self.signalsCounter = 0

        self.sm = IPCMemory()
        self.smCounter = 0;

        self.motionManager = MotionManager()
        self.firstMotion = False

        ###
        #Teil der Bachelorarbeit
        self.subscriptionService = SubscriptionService()
        ###

    def run(self):
        print('Executioner is running')
        #Wenn keine Motions vorhanden sind
        if not self.motionManager.getAllMotions():
            self.firstMotion = True
            print("Bitte die erste Geste anlernen")
            self.startLearning()
        self.firstMotion = False
        self.startExecution()

    def startExecution(self):
        self.sm.put(IPCMemory.NEW_MOTION)
        #ggf kurze wartezeit um sicherzustellen dass der befehl auch ankommt?
        
        while True:
            self.checkSharedMemory()
            self.signalsLock.acquire()
            if not self.signalsCounter < len(self.signals):
                self.signalsLock.release()
                continue

            event = self.signals[self.signalsCounter]
            self.signalsCounter = self.signalsCounter + 1
            self.signalsLock.release()

            if isinstance(event, AboartEvent):
                ###
                #Bachelorarbeit
                self.removeRedundance()
                ###
                self.signalsLock.acquire()
                signalsCopy = self.signals[:]
                self.signalsLock.release()
                
                self.sm.put(IPCMemory.NEW_MOTION)

                self.startRecognition(signalsCopy)
            else:
                continue

    def startRecognition(self, signalsCopy):
        motion = self.transformMotion(signalsCopy)

        #Vergleiche die Motion mit allen anderen
        calculator = Calculator()
        knownMotions = self.motionManager.getAllMotions()
        bestMatch = None
        bestScore = None
        print('')
        for knownMotionName in knownMotions:
            knownMotion = self.motionManager.getMotion(knownMotionName)
            score = calculator.getMatchingScore(motion, knownMotion)

            print('{} - {} %'.format(knownMotionName, score))

            if bestMatch == None or score > bestScore:
                bestMatch = knownMotionName
                bestScore = score

        print('')
        print('Den besten Match gab es mit: {} - {} %'.format(bestMatch, bestScore))

        #Funktionalität der erkannten Geste ausführen
        print('Hier wird nun function.execute ausgeführt')
        print('')

        if bestMatch == 'learningMotion':
            print('lerne')
            self.startLearning()

        ###
        #Teil der Bachelorarbeit
        else:
            print('Firing new event')
            topic = 'newMotionEvent'
            values = dict()
            values['name'] = bestMatch
            event = Event(topic, values)
            self.subscriptionService.onEvent(event)
        ###

    def startLearning(self):
        #Send all Signals to reset Inputs
        #Zur Sicherheit hier einmal zuviel, damit wirklich
        #erst mit beginn des lernens die Signale aufgenommen werden
        self.sm.put(IPCMemory.NEW_MOTION)

        while True:
            self.checkSharedMemory()
            self.signalsLock.acquire()
            if not self.signalsCounter < len(self.signals):
                self.signalsLock.release()
                continue

            event = self.signals[self.signalsCounter]
            self.signalsCounter = self.signalsCounter + 1
            self.signalsLock.release()

            if isinstance(event, AboartEvent):
                ###
                #Bachelorarbeit
                self.removeRedundance()
                ###
                
                self.signalsLock.acquire()
                signalsCopy = self.signals[:]
                self.signalsLock.release()

                self.sm.put(IPCMemory.NEW_MOTION)

                self.transformAndSafeMotion(signalsCopy)
                break
            else:
                continue

    def transformAndSafeMotion(self, signalsCopy):
        motion = self.transformMotion(signalsCopy)

        if self.firstMotion:
            motion.setName('learningMotion')
        else:
            name = input('Wie heißt die Motion\n')
            motion.setName(name)

        self.motionManager.saveOrUpdateMotion(motion)

    def transformMotion(self, signalsCopy):
        del signalsCopy[len(signalsCopy) - 1]

        transformer = MotionTransformer()
        motion = transformer.transformMotion(signalsCopy)

        return motion

    ###
    #Bachelorarbeit
    def removeRedundance(self):
        self.signalsLock.acquire()
        #Remove aboartEvent
        del self.signals[-1]

        #Remove allAboartButtonEvents
        deleted = False
        i = -1
        while not deleted:
            if isinstance(self.signals[i], ButtonEvent) and self.signals[i].value == 1:
                #print('Found ButtonEvent with Value {} @ {}'.format(self.signals[i].value, i))
                del self.signals[i]
                deleted = True
            else:
                i = i - 1

        deleted = False
        i = -1
        while not deleted:
            if isinstance(self.signals[i], ButtonEvent) and self.signals[i].value == 0:
                #print('Found ButtonEvent with Value {} @ {}'.format(self.signals[i].value, i))
                del self.signals[i]
                deleted = True
            else:
                i = i - 1

        deleted = False
        i = -1
        while not deleted:
            if isinstance(self.signals[i], ButtonEvent) and self.signals[i].value == 1:
                #print('Found ButtonEvent with Value {} @ {}'.format(self.signals[i].value, i))
                del self.signals[i]
                deleted = True
            else:
                i = i - 1
        
        self.signalsLock.release()
    ###

    def checkSharedMemory(self):
        import time
        if self.smCounter < self.sm.getSize():
            message = self.sm.get(self.smCounter)
            self.smCounter = self.smCounter + 1

            if message == IPCMemory.SHUTDOWN:
                print('I shall shutdown')
                time.sleep(2)
                sys.exit()
            elif message == IPCMemory.NEW_MOTION:
                self.signalsCounter = 0

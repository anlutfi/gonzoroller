#!/usr/bin/python
################################################################################
# TrinamicSilentMotor.py
# 
#
# By: Denis-Carl Robidoux
# 3 pins motor driver for the Gugusse Roller
#
################################################################################


from time import sleep, time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM) 


class TrinamicSilentMotor():
    def __init__(self,cfg,autoSpeed = False,trace = False):
        GPIO.setmode(GPIO.BCM)
        self.autoSpeed = autoSpeed
        
        if autoSpeed:
        
            if "targetTime" not in cfg:
                self.targetTime = cfg["defaultTargetTime"]
        
            else:
                self.targetTime = cfg["targetTime"]
        
            self.minSpeed = cfg["minSpeed"]
            self.maxSpeed = cfg["maxSpeed"]
        
        self.accel = cfg["accel"]
        self.histo = []
        self.skipHisto = 3
        self.trace = trace
        self.fault = False
        self.name = cfg["name"]
        self.speed = cfg["speed"]
        self.speed2 = cfg["speed2"]
        self.currentSpeed = 0
        self.target = 0
        self.SensorStopPin = cfg["stopPin"]
        self.ignoreInitial = cfg["ignoreInitial"]
        self.ignore = 0
        self.faultTreshold = cfg["faultTreshold"]
        self.pinEnable = cfg["pinEnable"]
        self.pinDirection = cfg["pinDirection"]
        self.pinStep = cfg["pinStep"]
        self.SensorStopState = cfg["stopState"]
        self.lasttick = time()
        self.toggle = 0
        self.shortsInARow = 0
        
        GPIO.setup(self.pinStep, GPIO.OUT, initial = 0)
        GPIO.setup(self.pinEnable, GPIO.OUT, initial = 0)
        
        if cfg["invert"]:
            GPIO.setup(self.pinDirection, GPIO.OUT, initial = 0)
        
        else:
            GPIO.setup(self.pinDirection, GPIO.OUT, initial = 1)
        
        self.pos = int(0)
        GPIO.setup(self.SensorStopPin, GPIO.IN)
    
    
    def enable(self):
        GPIO.output(self.pinEnable, 0)
    
    
    def disable(self):
        GPIO.output(self.pinEnable, 1)
        
    
    def forward(self):
        self.pos += 1
        GPIO.output(self.pinStep, self.toggle)
    
        if self.toggle == 1:
            self.toggle = 0
    
        else:
            self.toggle = 1
    
    
    def tick(self):
        if self.target != self.pos:
            self.direction()            
            if self.currentSpeed < self.targetSpeed:
                self.currentSpeed += self.accel
                if self.currentSpeed > self.targetSpeed:
                    self.currentSpeed = self.targetSpeed
    
            return time() + (1.0 / self.currentSpeed)
    
        return None
                        
    
    def move(self):
        ticks = 0
        #log = []
    
        if self.autoSpeed:
            self.moveStart = time()
    
        self.target = self.pos+self.faultTreshold
        self.targetSpeed = self.speed
        self.currentSpeed = 0
        self.ignore = self.ignoreInitial
    
        if self.target < self.pos:
            self.fault = True
            raise Exception("We do not support backward yet")
    
        else:
            self.direction = self.forward
    
        waitUntil = self.tick()
    
        while waitUntil != None:
            reading = GPIO.input(self.SensorStopPin)
            #log.append(reading)
            if self.ignore > 0:
                self.ignore -= 1
    
            else:
                if reading == self.SensorStopState:
                    if self.trace:
                        print("\033[1;32m{}\033[0m ticks for {}".format(ticks,self.name))
    
                    if ticks == self.ignoreInitial:
                        self.shortsInARow += 1;
    
                    else:
                        self.shortsInARow = 0
    
                    if self.shortsInARow >= 5:
                        self.fault = True
                        raise Exception("\033[1;31mFAULT\033[0m: only the lowest amount of steps for 5 cycles in a row")
    
                    if self.autoSpeed:
                        if self.skipHisto > 0:
                            self.skipHisto -= 1
                            return
    
                        delta = time()-self.moveStart
                        self.histo.append(delta)
    
                        if len(self.histo)<6:
                            return
    
                        self.histo = self.histo[-5:]
                        avg = sum(self.histo)/len(self.histo)
    
                        if abs(avg-self.targetTime)<0.01:
                            return
    
                        gamma = 20.0*(avg-self.targetTime)/(self.targetTime*100.0)
                        newspeed = self.speed2 * (1.0 + gamma)
                        self.speed2 = int(newspeed)
    
                        if self.speed2 < self.minSpeed:
                            self.speed2 = self.minSpeed
    
                        elif self.speed2 > self.maxSpeed:
                            self.speed2 = self.maxSpeed
    
                        self.speed = self.speed2
                        print("New speed for {} = {}ticks/s".format(self.name, self.speed))
                        
                    return
    
            if self.ignore == 0 and self.ignoreInitial != 0:
                self.currentSpeed = self.speed2
                self.targetSpeed = self.speed2
    
            delay = waitUntil - time()
    
            if delay>0.000001:
                sleep(delay)
    
            ticks += 1
    
            waitUntil = self.tick()
    
        self.fault = True
        raise Exception("Move failed, \033[1;31m{}\033[0m passed its limit without triggering sensor".format(self.name))

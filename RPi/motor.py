import RPi.GPIO as gpio
import time
import logging
import threading

servoPIN = 12
gpio.setmode(gpio.BCM)
gpio.setup(servoPIN, gpio.OUT)
p = gpio.PWM(servoPIN, 50) # gpio 17 for PWM with 50Hz
def change_lock():
    try:
        p.start(0) #Initialization
        while True:
            p.ChangeDutyCycle(2)
            time.sleep(0.5)
            p.ChangeDutyCycle(0)
            time.sleep(2)
            p.ChangeDutyCycle(12.5)
            time.sleep(0.5)
            p.ChangeDutyCycle(0)
            time.sleep(2)
    except Exception as e:
        print("error", e)
        p.stop()
        gpio.cleanup()
change_lock()
import RPi.GPIO as gpio
import time
import logging
import threading

servoPIN = 12
gpio.setmode(gpio.BCM)
gpio.setup(servoPIN, gpio.OUT)
p = gpio.PWM(servoPIN, 50) # gpio 17 for PWM with 50Hz

def start_motor_tread(state):
    logging.debug('starting motor thread')
    motor_thread = threading.Thread(name='change_lock', target=change_lock, args=(state,))
    motor_thread.start()
    logging.debug('motor thread finished')

def change_lock(state):
    try:
        p.start(0) #Initialization
        start_time = time.time()
        while (time.time()-start_time<3):
            if state:
                #lock
                p.ChangeDutyCycle(11)
            else:
                #open
                p.ChangeDutyCycle(2)
            time.sleep(0.5)
            p.ChangeDutyCycle(0)
            time.sleep(2)
        p.stop()
        gpio.cleanup()
        print("done")
    except:
        p.stop()
        gpio.cleanup()
#change_lock()
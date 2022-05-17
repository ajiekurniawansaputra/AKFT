"""
OTHER FUNCTIONS. SGLCERIC. CAPSTONE.
"""
import paho.mqtt.client as mqtt
import json
import base64
from pygame import mixer
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.fernet import Fernet
import RPi.GPIO as gpio
import time
import logging
import threading

class Room:
    def __init__ (self):
        self.id = 6
        self.password = None

def send_mqtt_encrypt(topic,msg,data=None,qos=1,retain=False):
    if data!=None:
        data = json.dumps(data).encode('utf-8')             #dict to byte
        key = Fernet.generate_key()
        fernet = Fernet(key)
        data = fernet.encrypt(data)
        data = base64.b64encode(data)                       #byte to string
        data = data.decode('ascii')
        key = base64.b64encode(key)                         #byte to string
        key = key.decode('utf-8')
        msg['data_key'] = key
    msg = json.dumps(msg).encode('utf-8')                   #dict to byte
    msg = public_key.encrypt(
        msg,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None))
    msg = base64.b64encode(msg)                             #byte to string
    msg = msg.decode('utf-8')
    client.publish(topic=topic, payload=json.dumps({'msg':msg,'data':data}), qos=qos, retain=retain)

def receive_mqtt_decrypt(msg):
    msg = json.loads(msg)
    data = msg['data']
    msg = msg['msg']
    msg = base64.b64decode(msg)                             #string to byte
    msg = private_key.decrypt(
    msg,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None))
    msg = json.loads(msg.decode('utf-8'))                   #byte to dict
    if data!=None:
        key = msg.pop('data_key')
        key = base64.b64decode(key)                         #string to byte
        data = base64.b64decode(data)                       #string to byte
        fernet = Fernet(key)
        data = fernet.decrypt(data)
        data = json.loads(data.decode('utf-8'))             #byte to dict
    return msg, data

#check for diferent cases
def play_sound(file, wait_for_finnish=True):
    mixer.init()
    mixer.music.load('sound/'+file)
    mixer.music.play()
    if wait_for_finnish:
        while mixer.music.get_busy()==True:
            continue

def door_command(client, userdata, msg):
    msg, _ = receive_mqtt_decrypt(msg.payload)
    if msg['state'] == True:
        open_door()
    else:
        start_motor_tread(True)
        print("tok tok e pintune tutup")

def open_door():
    start_motor_tread(False)
    print("tok tok e pintune dibuka")

def start_motor_tread(state):
    print('starting motor thread')
    motor_thread = threading.Thread(name='change_lock_local', target=change_lock_local, args=(state,))
    motor_thread.start()
    print('motor thread finished')

def change_lock(state):
    try:
        gpio.setmode(gpio.BCM)
        gpio.setup(12, gpio.OUT)
        gpio.setup (18, gpio.IN, pull_up_down=gpio.PUD_UP)
        gpio.setup (4, gpio.IN, pull_up_down=gpio.PUD_UP)
        p = gpio.PWM(12, 50)
        p.start(0) #Initialization
        start_time = time.time()
        while (time.time()-start_time<3):
            if state:
                #lock
                p.ChangeDutyCycle(12.5)
            else:
                #open
                p.ChangeDutyCycle(2)
            time.sleep(0.5)
            p.ChangeDutyCycle(0)
            time.sleep(2)
        p.stop()
        gpio.cleanup()
        gpio.setmode(gpio.BCM)
        gpio.setup (18, gpio.IN, pull_up_down=gpio.PUD_UP)
        print("donehfht")
    except Exception as e:
        print(e)#p.stop()
        #gpio.cleanup()

def change_lock_local(state):
    try:
        print("inside change lock")
        gpio.setmode(gpio.BCM)
        gpio.setup(12, gpio.OUT)
        gpio.setup (18, gpio.IN, pull_up_down=gpio.PUD_UP)
        gpio.setup (4, gpio.IN, pull_up_down=gpio.PUD_UP)
        p = gpio.PWM(12, 50)
        p.start(0) #Initialization
        while True:
            p.ChangeDutyCycle(2)
            print("open door")
            time.sleep(0.5)
            p.ChangeDutyCycle(0)
            door_timeout = time.time()#time.sleep(3)
            print("wait to open or 5s")
            while gpio.input(4)==0 and (time.time()-door_timeout<5):
                pass
            if gpio.input(4)==0:
                print("timeout")
                p.ChangeDutyCycle(12.5)
                start_time = time.time()
                while (time.time()-start_time<2):
                    pass
                break
            else:
                print("wait to close")
                while gpio.input(4)==1:
                    pass
                print("closeed")
                p.ChangeDutyCycle(12.5)
                start_time = time.time()
                while (time.time()-start_time<2):
                    pass
                break
        print("cleaning gpio")
        p.stop()
        gpio.cleanup()
        gpio.setmode(gpio.BCM)
        print("doooone c;eaning up")
        gpio.setup (18, gpio.IN, pull_up_down=gpio.PUD_UP)
        print("doooone")
    except Exception as e:
        print(e)
        #p.stop()
        #gpio.cleanup()
        
this_room = Room()
client = mqtt.Client(protocol=mqtt.MQTTv311)
with open("server_public_key.pem", "rb") as key_file:  #server public key
    public_key = serialization.load_pem_public_key(
        key_file.read(),
        backend=default_backend())
with open("sensor_private_key.pem", "rb") as key_file: #rpi private key
    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=None,
        backend=default_backend())
#start_motor_tread(False)
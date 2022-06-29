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
import fingerprint
import rfid
import pincam

class Room:
    """ Class that hold room data"""
    def __init__ (self):
        self.id = 6
        self.password = None
        self.fingerprint_flag = True
        self.pin_flag = True
        self.rfid_flag = True

def send_mqtt_encrypt(topic,msg,data=None,qos=1,retain=False):
    """function to send encrypt data and then send them with mqtt"""
    if data!=None:
        data = json.dumps(data).encode('utf-8')             #dict to byte
        key = Fernet.generate_key()
        fernet = Fernet(key)
        data = fernet.encrypt(data)
        data = base64.b64encode(data)                       #byte to string
        data = data.decode('ascii')
        #key = base64.b64encode(key)                         #byte to string
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
    """function to receive mqtt message and decrypt its data"""
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
        #key = base64.b64decode(key)                         #string to byte
        data = base64.b64decode(data)                       #string to byte
        fernet = Fernet(key)
        data = fernet.decrypt(data)
        data = json.loads(data.decode('utf-8'))             #byte to dict
    return msg, data

def play_sound(file, wait_for_finnish=True):
    """play a sound from a stated directory file"""
    mixer.init()
    mixer.music.load('sound/'+file)
    mixer.music.play()
    if wait_for_finnish:
        while mixer.music.get_busy()==True:
            continue

def door_command(client, userdata, msg):
    """callback for a command to open all rooms or close all room"""
    msg, _ = receive_mqtt_decrypt(msg.payload)
    if msg['state'] == True:
        #open
        start_motor_tread(False)
    else:
        #close
        start_motor_tread(True)

def start_motor_tread(state):
    print('starting motor thread')
    motor_thread = threading.Thread(name='motor_thread_func', target=motor_thread_func, args=(state,))
    motor_thread.start()
    print('motor thread finished')

def motor_thread_func(state):
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
        print("doooone cleaning up")
        gpio.setup (18, gpio.IN, pull_up_down=gpio.PUD_UP)
        print("doooone")
    except Exception as e:
        print(e)
        #p.stop()
        #gpio.cleanup()
        
def set_command(client, userdata, msg):
    """callback for a command to change which authentication is active"""
    msg, _ = receive_mqtt_decrypt(msg.payload)
    logging.debug('Setting Authentication Method')
    this_room.fingerprint_flag = msg['fingerprint']
    this_room.rfid_flag = msg['rfid']
    this_room.pin_flag = msg['pin']
    logging.debug('Authentication Method Set')

this_room = Room()
client = mqtt.Client(protocol=mqtt.MQTTv311)
with open("/home/pi/Documents/ajie/akft/RPi/server_public_key.pem", "rb") as key_file:  #server public key
    public_key = serialization.load_pem_public_key(
        key_file.read(),
        backend=default_backend())
with open("/home/pi/Documents/ajie/akft/RPi/sensor_private_key.pem", "rb") as key_file: #rpi private key
    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=None,
        backend=default_backend())
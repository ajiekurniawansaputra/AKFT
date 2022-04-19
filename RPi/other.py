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

class Room:
    def __init__ (self):
        self.id = 6
        self.password = None

def send_mqtt_encrypt(topic,msg,data=None):                 #to sensor
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
    client.publish(topic=topic, payload=json.dumps({'msg':msg,'data':data}))

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
def play_sound(file):
    mixer.init()
    mixer.music.load('sound/'+file)
    mixer.music.play()
    while mixer.music.get_busy()==True:
        continue

def door_command(client, userdata, msg):
    msg, _ = receive_mqtt_decrypt(msg.payload)
    if msg['state'] == True:
        open_door()
    else:
        print("tok tok e pintune tutup")

def open_door():
    print("tok tok e pintune dibuka")
    
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

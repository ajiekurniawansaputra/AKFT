"""
APP MQTT. SGLCERIC. CAPSTONE.
This file contained callbacks that will be called when new message is received in subscribed MQTT topic.
Each callback corespond to a topic which will perform a process given data as msg.payload
"""
import paho.mqtt.client as mqtt
import json
import pymongo
import datetime
import random
import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.fernet import Fernet

"""
CALLBACK. APP MQTT. SGLCERIC. CAPSTONE.
"""
def auth_fp(client, userdata, msg):
    msg, _ = receive_mqtt_decrypt(msg.payload)
    room_id = msg['roomId']
    user_id = msg['userId']
    try:
        log_db.insert_one({'room_id':room_id,'user_id':user_id,
            'date':datetime.datetime.now().replace(microsecond=0),'sensor':'FP'})
    except: pass                                #error saving

def load_fp(client, userdata, msg):
    msg, _ = receive_mqtt_decrypt(msg.payload)
    user_id = msg['user_id']
    room_id = msg['room_id']
    try:
        model = user_db.find_one({"_id":user_id},{'_id':0,'FP':1})[0]['FP']
        send_mqtt_encrypt('SGLCERIC/auth/fp/'+str(room_id),
            {'user_id':user_id},
            {'model':model})
    except: return                              # raise error model not found

def auth_rfid(client, userdata, msg):
    msg, _ = receive_mqtt_decrypt(msg.payload)
    room_id = msg['roomId']
    data = msg['data']
    print(data)
    user_id = 2222
    result = random.choice([True, False])
    send_mqtt_encrypt('SGLCERIC/auth/rfid/'+str(room_id),{'result':result})
    if result == True:
        try:
            log_db.insert_one({'room_id':room_id,'user_id':user_id,
                'date':datetime.datetime.now().replace(microsecond=0),'sensor':'RFID'})
        except: pass                               #error saving

def sign_up(client, userdata, msg):
    msg, data = receive_mqtt_decrypt(msg.payload)
    user_id = msg['user_id']
    model_FP = data['model']
    model_RFID = msg['uid']
    try:
        user_db.find_one_and_update({'_id':user_id},{'$set':{"FP":model_FP,'RFID':model_RFID}},{})
    except:
        client.publish(topic='SGLCERIC/enro/notif', payload='Error Saving') #delete data in db
        return
    client.publish(topic='SGLCERIC/enro/notif', payload='Saved')

def resync(client, userdata, msg):
    print('resync')
    msg, _ = receive_mqtt_decrypt(msg.payload)
    room_id = msg['room_id']
    try:
        user_list = room_db.find_one({'_id':room_id},{'_id':0,'user_list':1})['user_list']
    except Exception as e: 
        print(e)
    for i in range(len(user_list)):                    #location=indexonmongodb+1
        if user_list[i]!=None:
            try:
                print(i,user_list[i], 'SGLCERIC/sync/add/'+str(room_id))
                model = user_db.find_one({"_id":user_list[i]},{'_id':0,'FP':1})['FP']
                if model == None:
                    print('nomodel')
                    return
                send_mqtt_encrypt('SGLCERIC/sync/add/'+str(room_id),
                    {'user_id':user_list[i],
                    'location':i+1},
                    {'model':model})
            except Exception as e:
                print(e)                                #raise error model not found           
 


def on_message_sync_ack(client, userdata, msg):
    pass

"""
OTHER FUNCTION. APP MQTT. SGLCERIC. CAPSTONE.
"""
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

def open_key():
    with open("server_private_key.pem", "rb") as key_file: #rpi private key
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend())
    with open("sensor_public_key.pem", "rb") as key_file:  #sensor public key
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend())
    return private_key, public_key

def open_db():
    with open('db_host.txt', "r") as key_file:
        db_host = key_file.read()
        db = pymongo.MongoClient(db_host)
        key_file.close()
    main_db = db["maindatabase"]
    user_db = main_db["user"]
    room_db = main_db["room"]
    log_db = main_db["log"]
    return user_db, room_db, log_db

def start_mqtt():
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.message_callback_add('SGLCERIC/auth/fp', auth_fp)
    client.message_callback_add('SGLCERIC/auth/fp_load', load_fp)
    client.message_callback_add('SGLCERIC/auth/rfid', auth_rfid)
    client.message_callback_add('SGLCERIC/enro/model', sign_up)
    client.message_callback_add('SGLCERIC/sync/re', resync)
    client.message_callback_add('SGLCERIC/sync/ack', on_message_sync_ack)
    client.connect("broker.hivemq.com", 1883, 8000)
    return client

"""
MAIN. APP MQTT. SGLCERIC. CAPSTONE.
"""
if __name__ == "__main__":
    try:
        private_key, public_key = open_key()
        user_db, room_db, log_db = open_db()
        client = start_mqtt()
        client.subscribe('SGLCERIC/auth/fp') #to be added to the on connect function
        client.subscribe('SGLCERIC/auth/fp_load')
        client.subscribe('SGLCERIC/auth/rfid')
        client.subscribe('SGLCERIC/enro/model')
        client.subscribe('SGLCERIC/sync/re')
        client.loop_forever()
    except Exception as e:
        print(e)
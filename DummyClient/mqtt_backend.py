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
import logging
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.fernet import Fernet

"""
CALLBACK. APP MQTT. SGLCERIC. CAPSTONE. ####################################################################
"""
def auth_fp(client, userdata, msg):
    """ This callback process authentication result from fingerprint on sensor match
    data transfered including room_id, user_id are saved into databased with timestamp.
    """
    try:
        logging.debug('Receiving fingerprint authentication result')
        msg, _ = receive_mqtt_decrypt(msg.payload)
        date = msg['date']
        logging.debug(date)
        date = datetime.datetime.strptime(date, '%y-%m-%d %H:%M:%S')
        room_id = msg['room_id']
        result = msg['result']
        if result:
            user_id = msg['user_id']
            logging.debug(f'Saving data room id {room_id}, user id {user_id} to database')
            log_db.insert_one({'result':result,'room_id':room_id,'user_id':user_id,
                'date':date,'sensor':'FP'})
            logging.debug('Saved')
        else:
            logging.debug(f'Saving declined auth to database')
            log_db.insert_one({'result':result,'room_id':room_id,
                'date':date,'sensor':'FP'})
            logging.debug('Saved')
    except Exception as e:
            logging.error(e)

def auth_rfid(client, userdata, msg):
    """ This callback process uid data from rfid, authentication result are saved in database"""
    try:
        logging.debug('Receiving rfid authentication data')
        msg, _ = receive_mqtt_decrypt(msg.payload)
        date = msg['date']
        logging.debug(date)
        date = datetime.datetime.strptime(date, '%y-%m-%d %H:%M:%S')
        room_id = msg['roomId']
        data = msg['data']
        user_id = 2222
        result = random.choice([True, False])
        send_mqtt_encrypt('SGLCERIC/auth/rfid/'+str(room_id),{'result':result})
        logging.debug(f'Saving data room id {room_id}, user id {user_id}, data {data} to database')
        log_db.insert_one({'result':result,'room_id':room_id,'user_id':user_id,
                'date':date,'sensor':'RFID'})
    except Exception as e:
            logging.error(e)

def auth_pin(client, userdata, msg):
    """ This callback receive authentication result from keypad to be saved in database"""
    try:
        logging.debug('Receiving keypad data')
        msg, _ = receive_mqtt_decrypt(msg.payload)
        date = msg['date']
        logging.debug(date)
        date = datetime.datetime.strptime(date, '%y-%m-%d %H:%M:%S')
        room_id = msg['room_id']
        result = msg['result']
        logging.debug(f'Saving data room id {room_id} to database')
        log_db.insert_one({'result':result,'room_id':room_id,
                'date':date,'sensor':'pin'})
    except Exception as e:
            logging.error(e)

def save_img(client, userdata, msg):
    """ This callback save image to the database"""
    try:
        logging.debug('Receiving image data')
        msg, data = receive_mqtt_decrypt(msg.payload)
        date = msg['date']
        img = data['img']
        img = base64.b64decode(img)
        img = base64.b64encode(img)
        logging.debug(date)
        date = datetime.datetime.strptime(date, '%y-%m-%d %H:%M:%S')
        db_ack = image_db.insert_one({'date':date, 'img':img})
        logging.debug(f'inserted id {db_ack.inserted_id}')
    except Exception as e:
            logging.error(e)

def sign_up(client, userdata, msg):
    """ This callback will save uid and model to database"""
    try:
        logging.debug('Sign up, Receiving uid and model')
        msg, data = receive_mqtt_decrypt(msg.payload)
        user_id = msg['user_id']
        model_FP = data['model']
        model_RFID = msg['uid']
        logging.debug('Saving uid and model for user id {user_id}')
        try:
            user_db.find_one_and_update({'_id':user_id},{'$set':{"FP":model_FP,'RFID':model_RFID}},{})
        except:
            client.publish(topic='SGLCERIC/enro/notif', payload='Error Saving') #delete data in db
            raise Exception('error in saving model occured')
        client.publish(topic='SGLCERIC/enro/notif', payload='Saved')
    except Exception as e:
            logging.error(e)

def resync(client, userdata, msg):
    """ This callback sends every model in a room saved in database
    *warning, check timing when delete ack finished and this func start. should be okay if onethreaded
    """
    try:
        logging.debug('Resync, Receiving room id')
        msg, _ = receive_mqtt_decrypt(msg.payload)
        room_id = msg['room_id']
        logging.debug('Get user list')
        user_list = room_db.find_one({'_id':room_id},{'_id':0,'user_list':1})['user_list']
        #location=indexonmongodb+1
        for i in range(len(user_list)):
            if user_list[i]!=None:
                logging.debug('Get {user_list[i]} model')
                model = user_db.find_one({"_id":user_list[i]},{'_id':0,'FP':1})['FP']
                if model == None:
                    raise Exception('model not found')
                logging.debug('Send {user_list[i]} model')
                send_mqtt_encrypt('SGLCERIC/sync/add/'+str(room_id),
                    {'user_id':user_list[i],
                    'location':i+1},
                    {'model':model})
    except Exception as e:
        logging.error(e)

def ack_del(client, userdata, msg):
    """ This callback record delete ack message from device"""
    try:
        logging.debug('Delete ACK')
        msg, _ = receive_mqtt_decrypt(msg.payload)
        room_id = msg['room_id']
        user_id = msg['user_id']
        logging.debug('Get user list')
        user_data = room_db.find_one({'_id':room_id},{'_id':0,'user_list':1,'user_list_todel':1,'user_list_ack':1})
        user_list_todel = user_data['user_list_todel']
        user_list_ack = user_data['user_list_ack']
        user_list = user_data['user_list']
        logging.debug('processing list')
        if user_id == 'all':
            for user in user_list_todel:
                logging.debug(f'deleting {user_list[user]}')
                user_list[user-1] = None
                logging.debug(f'deleted')
            user_list_todel.clear()
            user_list_ack.clear()
        else:
            logging.debug(f'get location')
            location = user_list.index(user_id)
            logging.debug(f'location = {location+1}')
            user_list[location]=None
            user_list_todel.remove(location+1)
            user_list_ack.remove(user_id)
        logging.debug('updating list')
        room_db.find_one_and_update({'_id':room_id},{'$set':{"user_list":user_list}},{})
        room_db.find_one_and_update({'_id':room_id},{'$set':{"user_list_ack":user_list_ack}},{})
        room_db.find_one_and_update({'_id':room_id},{'$set':{"user_list_todel":user_list_todel}},{})
        logging.debug('list updated')
    except Exception as e:
        logging.error(e)

def ack_add(client, userdata, msg):
    """ This callback record add ack message from device"""
    try:
        logging.debug('Add ACK')
        msg, _ = receive_mqtt_decrypt(msg.payload)
        room_id = msg['room_id']
        user_id = msg['user_id']
        logging.debug('Get user list')
        user_list_ack = room_db.find_one({'_id':room_id},{'_id':0,'user_list_ack':1})['user_list_ack']
        if user_id in user_list_ack:
            logging.warning('warning, trying to add userid to ack, userid already in ack')    
        else: 
            user_list_ack.append(user_id)
        logging.debug('updating list')
        room_db.find_one_and_update({'_id':room_id},{'$set':{"user_list_ack":user_list_ack}},{})
        logging.debug('list updated')
    except Exception as e:
        logging.error(e)

"""
OTHER FUNCTION. APP MQTT. SGLCERIC. CAPSTONE. ####################################################################
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
    image_db = main_db["image"]
    return user_db, room_db, log_db, image_db

"""
MQTT UTILS CALLBACK. APP MQTT. SGLCERIC. CAPSTONE. ####################################################################
"""
def on_connect(client, userdata, flags, rc):
    logging.info("Connected flags"+str(flags)+"result code "+str(rc))
    client.connected_flag=True
    client.subscribe('SGLCERIC/auth/fp')
    client.subscribe('SGLCERIC/auth/rfid')
    client.subscribe('SGLCERIC/auth/pin')
    client.subscribe('SGLCERIC/enro/model')
    client.subscribe('SGLCERIC/sync/re')
    client.subscribe('SGLCERIC/sync/del/ack')
    client.subscribe('SGLCERIC/sync/add/ack')
    client.subscribe('SGLCERIC/img')

"""
MAIN. APP MQTT. SGLCERIC. CAPSTONE. ####################################################################
"""

def main(debug = False):
    if debug == True:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

    client.message_callback_add('SGLCERIC/auth/fp', auth_fp)
    client.message_callback_add('SGLCERIC/auth/rfid', auth_rfid)
    client.message_callback_add('SGLCERIC/auth/pin', auth_pin)
    client.message_callback_add('SGLCERIC/enro/model', sign_up)
    client.message_callback_add('SGLCERIC/sync/re', resync)
    client.message_callback_add('SGLCERIC/sync/del/ack', ack_del)
    client.message_callback_add('SGLCERIC/sync/add/ack', ack_add)
    client.message_callback_add('SGLCERIC/img', save_img)

    client.on_connect= on_connect
    client.connect("broker.hivemq.com", 1883, 8000)
    client.loop_forever()

if __name__ == "__main__":
    while True:
        try:
            private_key, public_key = open_key()
            user_db, room_db, log_db, image_db = open_db()
            client = mqtt.Client(protocol=mqtt.MQTTv311)
            main(debug = True)
        except Exception as e:
            print(e)
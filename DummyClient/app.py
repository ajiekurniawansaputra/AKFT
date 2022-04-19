"""
Flask APP. SGLCERIC. CAPSTONE.
This file runs Flask Framework to render dummy website, 
each route used to accept form or showing data from database.
"""
from flask import Flask, request, render_template, redirect, url_for
import paho.mqtt.client as mqtt
import json
import pymongo
import base64
import logging
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.fernet import Fernet

"""
ROUTE. SGLCERIC. CAPSTONE. ####################################################################
"""
app = Flask(__name__)

@app.route('/',methods=['POST','GET'])
def home():
    """ This url show all log in every door"""
    try:
        if request.method == 'GET':
            logs_data = log_db.find({},{ "_id": 0}).limit(5).sort('date', -1)
            images_data = image_db.find({},{ "_id": 0}).limit(5).sort('date', -1) #.sort({$natural: -1})
            imgs_data = []
            for image in images_data:
                img = image['img']
                img = img.decode()
                imgs_data.append(img)
            return render_template("index.html", logs_data=logs_data, imgs_data=imgs_data)
    except Exception as e:
        logging.error(e)

@app.route('/users',methods=['POST','GET'])
def users():
    """ This url show all user and add new one"""
    try:
        if request.method == 'GET':
            users_data = user_db.find({},{ "_id": 1,'name':1})
            return render_template("users.html", users_data=users_data)
        elif request.method == 'POST':
            logging.debug('Receiving New User form')
            user_id = int(request.form['user_id'])
            name = request.form['name']
            try:
                logging.debug('Saving New User data')
                db_ack = user_db.insert_one({'_id':user_id,'name':name,'info':None,
                                        'FP':None,'RFID':None})
            except: 
                return render_template("users.html", message='user already exist', users_data=user_db.find({},{ "_id": 1,'name':1})) #user already exist, edit instead
            logging.debug('Sending Registration Command to RPi')
            send_mqtt_encrypt('SGLCERIC/enro/id',{'user_id':user_id})
            return render_template("enroll.html", ack=True, user_id=db_ack.inserted_id)
    except Exception as e:
        logging.error(e)

@app.route('/user/<string:request_method>/<int:user_id>')
def user(request_method, user_id):
    """ This url show a user and delete one"""
    try:
        if request_method == 'details': #get
            message = request.args.get('message')
            logging.debug('geting user data')
            room_list = room_db.find({'user_list_ack':{'$in':[user_id]}}, {'_id':1,'name':1})
            room_list_nin = room_db.find({'user_list_ack':{'$nin':[user_id]}}, {'_id':1,'name':1})
            user_data = user_db.find_one({'_id':user_id})
            logging.debug('render the page')
            return render_template("user.html", user_data=user_data, room_list=room_list, room_list_nin=room_list_nin, message=message)
        elif request_method == 'delete': #delete
            ack_message = user_db.delete_one({'_id':user_id})
            logging.debug('{user_id} is deleted')
            users_data = user_db.find({},{ "_id": 1,'name':1})
            return render_template("users.html", users_data=users_data, message=str(user_id)+" deleted: "+str(ack_message.acknowledged))
    except Exception as e:
        logging.error(e)

@app.route('/rooms',methods=['GET'])
def rooms():
    """ This url show all room"""
    try:
        room_data = room_db.find({},{ "_id": 1,'name':1})
        return render_template("rooms.html", room_data=room_data)
    except Exception as e:
        logging.error(e)

@app.route('/room/<string:request_method>/<int:room_id>') #should use delete method, but not suported in html, too lazy for ajax
def room(request_method, room_id):
    """ This url show a room and delete one"""
    try:
        if request_method == 'details': #get
            message = request.args.get('message')
            room_data = room_db.find_one({'_id':room_id})
            return render_template("room.html", room_data=room_data, message=message)
        elif request_method == 'delete': #delete
            ack_message = room_db.delete_one({'_id':room_id})
            logging.debug('{room_id} is deleted')
            room_data = room_db.find({},{ "_id": 1,'name':1})
            return render_template("rooms.html", room_data=room_data, message=str(room_id)+" deleted: "+str(ack_message.acknowledged))
    except Exception as e:
        logging.error(e)

@app.route('/user/enroll',methods=['GET'])
def enroll():
    """ This url show form for new user"""
    return render_template("enroll.html")

@app.route('/user/sync',methods=['POST','GET'])
def sync():
    """ This url edit user list in a room, send resync command"""
    try:
        if request.method == 'POST':
            button = request.form['button']
            if button == 'add':
                add_user_list = [int(i) for i in request.form['user_list'].split(',')]
                room_id = int(request.form['room_id'])
                logging.debug('add_user_list')
                add_list_func(room_id, add_user_list)
                return redirect(url_for('room', request_method='details', room_id=room_id, 
                                        message='List updated'))
            if button == 'del':
                remove_user_list =[int(i) for i in request.form['user_list'].split(',')]
                room_id = int(request.form['room_id'])             
                logging.debug('remove_user_list')
                remove_list_func(room_id, remove_user_list)
                return redirect(url_for('room', request_method='details', room_id=room_id, 
                                        message='List updated'))
            if button == 'sync_command':
                logging.debug('sending command sync')
                room_id = request.form['room_id']
                return redirect(url_for('room', request_method='details', room_id=room_id, 
                                        message='Device is processing the request, Refresh the page to update list'))
            if button == 'resync_command':
                logging.debug('sending command resync')
                room_id = request.form['room_id']
                send_mqtt_encrypt('SGLCERIC/sync/del/'+str(room_id),{'location':'resync'})
                return redirect(url_for('room', request_method='details', room_id=room_id, 
                                        message='Device is processing the request, Refresh the page to update list'))
            return render_template("sync.html", message="unknown button pressed")
        else : return render_template("sync.html")
    except Exception as e:
        logging.error(e)

@app.route('/editlist/<string:mode>')
def editlist(mode):
    """ This url for add or delete allowed list and send command to add or delete fp model"""
    try:
        if mode == 'add':
            logging.debug('adding user to room')
            user_id = int(request.args.get('user_id'))
            room_id = int(request.args.get('room_id'))
            logging.debug('add_user_list')
            location = add_list_func(room_id, [user_id], True)
            logging.debug('Get {user_id} model')
            model = user_db.find_one({"_id":user_id},{'_id':0,'FP':1})['FP']
            if model == None:
                raise Exception('model not found')
            logging.debug('Send {user_id} model')
            send_mqtt_encrypt('SGLCERIC/sync/add/'+str(room_id),
                {'user_id':user_id,
                'location':location},
                {'model':model})
            logging.debug('command sent')
            return redirect(url_for('user', request_method='details', user_id=user_id, 
                                        message='Sending Command'))
        else:
            logging.debug('removing a user from a room')
            user_id = int(request.args.get('user_id'))
            room_id = int(request.args.get('room_id'))
            logging.debug('remove_user_list')
            location = remove_list_func(room_id, [user_id], True)
            send_mqtt_encrypt('SGLCERIC/sync/del/'+str(room_id),{'location':location, 'user_id':user_id})
            return redirect(url_for('user', request_method='details', user_id=user_id, 
                                        message='Sending Command'))
    except Exception as e:
        logging.error(e)

@app.route('/opendoor/<string:state>')
def opendoor(state):
    """ This url send command to open all dor in an emergency, or close when anything is get back to normal"""
    try:
        if state == 'true':
            send_mqtt_encrypt('SGLCERIC/open',{'state':True})
        else:
            send_mqtt_encrypt('SGLCERIC/open',{'state':False})
        logs_data = log_db.find({},{ "_id": 0}).limit(5).sort('date', -1)
        return render_template("index.html", logs_data=logs_data, message = 'command sent')
    except Exception as e:
        logging.error(e)

"""
OTHER FUNCTION. SGLCERIC. CAPSTONE. ####################################################################
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
    return None, public_key
    
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

def add_list_func(room_id, add_user_list, unit=False):
    logging.debug('get old user list')
    user_data = room_db.find_one({'_id':room_id},{'_id':0,'user_list':1, 'user_list_todel':1})
    user_list = user_data['user_list']
    user_list_todel = user_data['user_list_todel']
    logging.debug('processing list')
    for user_id in add_user_list:
        if (user_id in user_list):
            try:
                user_list_todel.remove(user_list.index(user_id)+1)
                logging.warning(f'{user_id} deleted from todel list with the value {user_list.index(user_id)}')
            except:
                logging.warning(f'{user_id} not in todel list with the value {user_list.index(user_id)}')
            logging.warning(f'{user_id} already in the list')
        else:
            try:
                user_list[user_list.index(None)]=user_id
                logging.debug(f'{user_id} added')
            except: 
                logging.warning('room is full')    
    logging.debug('updating list')
    room_db.find_one_and_update({'_id':room_id},{'$set':{"user_list":user_list}},{})
    room_db.find_one_and_update({'_id':room_id},{'$set':{"user_list_todel":user_list_todel}},{})
    logging.debug('list updated')
    if unit:
        logging.debug(f'Get {user_id} location')
        location = user_list.index(user_id)
        return location
    return            

def remove_list_func(room_id, remove_user_list, unit=False):
    logging.debug('get old user list')
    user_data = room_db.find_one({'_id':room_id},{'_id':0,'user_list':1,'user_list_todel':1,'user_list_ack':1})
    user_list = user_data['user_list']
    user_list_todel = user_data['user_list_todel']
    user_list_ack = user_data['user_list_ack']
    logging.debug('processing list')
    for user_id in remove_user_list:
        if user_id not in user_list_ack:
            logging.debug(f'deleting {user_id} from userlist')
            try:
                user_list[user_list.index(user_id)] = None
            except:
                logging.warning(f'{user_id} is not in userlist nor userlistack')
            logging.debug(f'deleted')
        else:
            if user_id not in user_list_todel:
                try:
                    user_list_todel.append(user_list.index(user_id)+1)
                    logging.debug(f'{user_id} added to todel list')
                except:
                    logging.warning(f'adding todel list error')
            else:
                logging.warning(f'{user_id} already added to todel list')
    logging.debug('updating list')
    room_db.find_one_and_update({'_id':room_id},{'$set':{"user_list":user_list}},{})
    room_db.find_one_and_update({'_id':room_id},{'$set':{"user_list_todel":user_list_todel}},{})
    logging.debug('list updated')
    if unit:
        logging.debug(f'Get {user_id} location')
        location = user_list.index(user_id)+1
        return location
    return

"""
MAIN. SGLCERIC. CAPSTONE. ####################################################################
"""
def main(debug=False):
    if debug == True:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    
    client.connect("broker.hivemq.com", 1883, 8000)

if __name__ == '__main__':
    _, public_key = open_key()
    user_db, room_db, log_db, image_db = open_db()
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    main(debug=True)
    app.run(host="0.0.0.0", port=5000, use_reloader=False)
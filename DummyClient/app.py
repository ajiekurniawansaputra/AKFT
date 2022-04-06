"""
Flask APP. SGLCERIC. CAPSTONE.
This file runs Flask Framework to render dummy website, 
each route used to accept form or showing data from database.
"""
from flask import Flask, request, render_template
import paho.mqtt.client as mqtt
import json
import pymongo
import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.fernet import Fernet

"""
ROUTE. SGLCERIC. CAPSTONE.
"""
app = Flask(__name__)

@app.route('/',methods=['POST','GET'])
def home():
    if request.method == 'GET':
        try:
            logs_data = log_db.find({},{ "_id": 0}).limit(5).sort('date', -1)
            return render_template("index.html", logs_data=logs_data)
        except Exception as e:
            return ("error")

@app.route('/users',methods=['POST','GET'])
def users():
    if request.method == 'GET':
        users_data = user_db.find({},{ "_id": 1,'name':1})
        return render_template("users.html", users_data=users_data)
    elif request.method == 'POST':
        user_id = int(request.form['user_id'])
        name = request.form['name']    
        try:
            db_ack = user_db.insert_one({'_id':user_id,'name':name,'info':None,
                                    'room_list':None,'FP':None,'RFID':None})
        except: return render_template("users.html", message='user already exist', users_data=user_db.find({},{ "_id": 1,'name':1})) #user already exist, edit instead
        send_mqtt_encrypt('SGLCERIC/enro/id',{'user_id':user_id})
        return render_template("enroll.html", ack=True, user_id=db_ack.inserted_id)

@app.route('/user/<string:request_method>/<int:user_id>') #should use delete method, but not suported in html, too lazy for ajax
def user(request_method, user_id): #
    if request_method == 'details': #get
        user_data = user_db.find_one({'_id':user_id})
        return render_template("user.html", user_data=user_data)
    elif request_method == 'delete': #delete
        ack_message = user_db.delete_one({'_id':user_id})
        users_data = user_db.find({},{ "_id": 1,'name':1})
        return render_template("users.html", users_data=users_data, message=str(user_id)+" deleted: "+str(ack_message.acknowledged))

@app.route('/rooms',methods=['POST','GET'])
def rooms():
    if request.method == 'GET':
        room_data = room_db.find({},{ "_id": 1,'name':1})
        return render_template("rooms.html", room_data=room_data)

@app.route('/room/<string:request_method>/<int:room_id>') #should use delete method, but not suported in html, too lazy for ajax
def room(request_method, room_id):
    if request_method == 'details': #get
        users_list = user_db.find({'room_list':{'$in':[room_id]}}, {'_id':0,'name':1})
        room_data = room_db.find_one({'_id':room_id})
        return render_template("room.html", room_data=room_data, users_list=users_list)
    elif request_method == 'delete': #delete
        ack_message = room_db.delete_one({'_id':room_id})
        room_data = room_db.find({},{ "_id": 1,'name':1})
        return render_template("rooms.html", room_data=room_data, message=str(room_id)+" deleted: "+str(ack_message.acknowledged))


@app.route('/user/enroll',methods=['GET'])
def enroll():
    return render_template("enroll.html")

@app.route('/user/sync',methods=['POST','GET'])
def sync():
    if request.method == 'POST':
        button = request.form['button']
        if button == 'save_list': #should be added to room/<room_id> as PUT
            print('edit list')
            try:
                add_user_list = [int(i) for i in request.form['add_user_list'].split(',')]
                remove_user_list =[int(i) for i in request.form['remove_user_list'].split(',')] 
                room_id = int(request.form['room_id'])
            except Exception as e:
                return render_template("sync.html", message="error reading form")
            try: #all this operations should be in mongodb with update_one $[identifier]
                user_list = room_db.find_one({'_id':room_id},{'_id':0,'user_list':1})['user_list']
            except: return render_template("sync.html", message="room doesnt exist") 
            for user_id in remove_user_list:
                try:
                    user_list[user_list.index(user_id)]=None
                except:
                    print('alredi non')
                    pass #user id already None
            for user_id in add_user_list:
                if user_id in user_list:
                    pass #user id already in the list
                else:
                    try:
                        user_list[user_list.index(None)]=user_id
                    except: 
                        print('full')
                        pass #list is full
            db_ack=room_db.find_one_and_update({'_id':room_id},{'$set':{"user_list":user_list}},{})
            print('saved')
            return render_template("sync.html", message= db_ack)
        if button == 'sync_command': #added later, can be added after the savelist too for easy of use
            print('sync_command') #send delete command and add command
            room_id = request.form['room_id']
            return render_template("sync.html")
        if button == 'resync_command':
            print("sending command resync")
            room_id = request.form['room_id']
            send_mqtt_encrypt('SGLCERIC/sync/del/'+str(room_id),{'location':'resync'})
            return render_template("sync.html")
    else : return render_template("sync.html")

"""
OTHER FUNCTION. SGLCERIC. CAPSTONE.
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

"""
MAIN. SGLCERIC. CAPSTONE.
"""
if __name__ == '__main__':
    #read public key for encryption
    with open("sensor_public_key.pem", "rb") as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend())
    #connect connect mongodb
    with open('db_host.txt', "r") as key_file:
        db_host = key_file.read()
        db = pymongo.MongoClient(db_host)
        key_file.close()
    main_db = db["maindatabase"]
    user_db = main_db["user"]
    room_db = main_db["room"]
    log_db = main_db["log"]
    #connect mqtt
    client = mqtt.Client(protocol=mqtt.MQTTv311) 
    client.connect("broker.hivemq.com", 1883, 8000)
    #run flask
    app.run(host="0.0.0.0", port=5000, use_reloader=True)
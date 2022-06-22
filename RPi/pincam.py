"""
Camera. Pin. SGLCERIC. CAPSTONE.
"""
import other as util
import threading
import os
import logging
import base64
import time
import board
import busio
import adafruit_mpr121
import datetime
import random
import threading

i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)
key_map = {'0':'-2', '1':'7', '2':'4', '3':'1', '4':'0', '5':'8',
           '6':'5', '7':'2', '8':'-1', '9':'9', '10':'6', '11':'3'}

def password_command(client, userdata, msg):
    try:
        logging.debug('Changing room password')
        util.this_room.password=msg.payload
        logging.debug('Changed')
    except Exception as e:
        logging.error(e)
        return

def _bouncing(i):
    while mpr121[i].value:
        pass
        
def _process_key(input_key, i):
    if key_map[str(i)] == '-1':
        _bouncing(i)
        print("Input {} touched!".format(key_map[str(i)]))
        util.play_sound('tbl clr.mp3', wait_for_finnish=False)
        raise
    elif key_map[str(i)] == '-2':
        _bouncing(i)
        print("Input {} touched!".format(key_map[str(i)]))
    else:
        _bouncing(i)
        input_key.append(key_map[str(i)])
        util.play_sound('tbl pin.mp3', wait_for_finnish=False)
        print("Input {} touched!".format(key_map[str(i)]))
    return input_key

def touchpad_sensor():
    logging.debug('touchpad thread start')
    while util.this_room.rfid_flag == True:
        try:
            read_keypad()
        except Exception as e:
            print(e)

def read_keypad():
    try:
        input_key = []
        start_key_timer = time.time()
        while (len(input_key)<6)and((time.time()-start_key_timer)<5):
            for i in range(12):
                if mpr121[i].value:
                    input_key = _process_key(input_key, i)
                    start_key_timer = time.time()
                if (len(input_key))==0:
                    if util.this_room.rfid_flag == 0:
                        return
                    start_key_timer = time.time()
        if len(input_key)<6:
            print("timeout")
            util.play_sound('Timeout.mp3')
        else:
            input_key = ''.join(input_key)
            print(input_key,type(input_key))
            password_auth(int(input_key))
    except Exception as e:
        print("tombol clear", e)
        pass

#pin_thread = threading.Thread(name='touchpad_sensor', target=touchpad_sensor)

def password_auth(pin):
    logging.debug('decrypt password')
    msg, _ = util.receive_mqtt_decrypt(util.this_room.password)
    password = int(msg['password'])
    date = str(datetime.datetime.now().replace(microsecond=0))[2:]
    img_key = random.randint(1111, 9999)
    img_key = str(img_key)+date
    take_photo(img_key)
    if pin == password:
        logging.debug('pin true')
        util.start_motor_tread(False)
        util.play_sound('Pin Match.mp3')
        logging.debug('Send Payload')
        util.send_mqtt_encrypt('SGLCERIC/auth/pin',
            {'date':date,
            'room_id':util.this_room.id,
            'result': True,
            'img_key':img_key})
    else:
        logging.debug('pin false')        
        util.play_sound('Pin not Match.mp3')
        logging.debug('Send Payload')
        util.send_mqtt_encrypt('SGLCERIC/auth/pin',
            {'date':date,
            'room_id':util.this_room.id,
            'result': False,
            'img_key':img_key})

def take_photo(img_key):
    logging.debug('starting camera thread')
    take_photo_thread = threading.Thread(name='shoot', target=shoot, args=(img_key))
    take_photo_thread.start()
    logging.debug('camera thread finished')
    
def shoot(img_key):
    logging.debug('taking a photo')
    try:
        os.system("libcamera-still -o img.jpg -t 1000 -n --width 1280 --height 720")
        logging.debug('photo captured')
    except Exception as e:
        logging.debug(f'photo not captured, {e}')
        return
    try:
        logging.debug('photo processing')
        with open("img.jpg", "rb") as imageFile:
            img = base64.b64encode(imageFile.read())
            img = img.decode('utf-8')
            #print(img)
        logging.debug('Sending photo')
        util.send_mqtt_encrypt('SGLCERIC/img',{'img_key':img_key}, {'img':img})
        logging.debug('Sent')
    except Exception as e:
        logging.debug(f'photo processing failed, {e}')
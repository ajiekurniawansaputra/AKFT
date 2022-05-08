"""
Main Rasberry APP. SGLCERIC. CAPSTONE.
"""
import other as util
import fingerprint
import pincam
import rfid
import threading
import time
import logging
import serial

def main(debug=False):
    if debug == True:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    
    #define thread
    background_thread = threading.Thread(name='background', target=background)
    fingerprint_thread = threading.Thread(name='fingerprint_sensor', target=fingerprint_sensor)
    rfid_thread = threading.Thread(name='rfid_sensor', target=rfid_sensor)
    pin_thread = threading.Thread(name='touchpad_sensor', target=touchpad_sensor)    
    
    #start thread
    background_thread.start()
    fingerprint_thread.start()
    rfid_thread.start()
    pin_thread.start()
    
#add error handling to background
def background():
    logging.debug('Background thread start')
    client = util.client
    client.message_callback_add('SGLCERIC/auth/rfid/'+str(util.this_room.id), nfc.response)
    client.message_callback_add('SGLCERIC/sync/add/'+str(util.this_room.id), fp.add)
    client.message_callback_add('SGLCERIC/sync/del/'+str(util.this_room.id), fp.delete)
    client.message_callback_add('SGLCERIC/open', util.door_command)
    client.message_callback_add('SGLCERIC/pass/'+str(util.this_room.id), pincam.password_command)
    client.will_set(topic='SGLCERIC/connection/'+str(util.this_room.id), payload='Device Lost Connection', qos=1, retain=True )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    #client.tls_set('/home/pi/Documents/client/ca.crt', '/home/pi/Documents/client/client.crt', '/home/pi/Documents/client/client.key')
    #client.connect('54.196.200.69', 8883)
    client.connect('broker.hivemq.com', 1883, 10)
    client.loop_forever()

def on_connect(client, userdata, flags, rc):
    if rc==0:
        logging.debug('MQTT Conected')
        client.publish(topic='SGLCERIC/connection/'+str(util.this_room.id), payload='Connected', qos=1, retain=True)
        client.connected_flag = True
        client.subscribe('SGLCERIC/auth/rfid/'+str(util.this_room.id))
        client.subscribe('SGLCERIC/sync/add/'+str(util.this_room.id))
        client.subscribe('SGLCERIC/sync/del/'+str(util.this_room.id))
        client.subscribe('SGLCERIC/open')
        client.subscribe('SGLCERIC/pass/'+str(util.this_room.id))
    else:
        logging.debug('MQTT Conection Refused {rc}')
        
def on_disconnect(client, userdata, rc):
    logging.debug('MQTT Disconected, {rc}')
    client.connected_flag = False
    #add reconect funtion

def fingerprint_sensor():
    logging.debug('fingerprint thread start')
    while True:
        try:
            fp.read()
        except Exception as e:
            print(e)

def rfid_sensor():
    logging.debug('rfid thread start')
    while True:
        try:
            nfc.read()
        except Exception as e:
            print(e)

def touchpad_sensor():
    logging.debug('touchpad thread start')
    while True:
        try:
            #pincam.password_auth(int(input('pin:')))
            pincam.read_keypad()
        except Exception as e:
            print(e)

if __name__ == "__main__":
    fp = fingerprint.FP(serial.Serial("/dev/serial0", baudrate=57600, timeout=1))
    nfc = rfid.RFID()
    main(debug=True)
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
    client = util.client
    client.message_callback_add('SGLCERIC/auth/rfid/'+str(util.this_room.id), nfc.response)
    client.message_callback_add('SGLCERIC/sync/add/'+str(util.this_room.id), fp.add)
    client.message_callback_add('SGLCERIC/sync/del/'+str(util.this_room.id), fp.delete)
    #client.tls_set('/home/pi/Documents/client/ca.crt', '/home/pi/Documents/client/client.crt', '/home/pi/Documents/client/client.key')
    #client.connect('54.196.200.69', 8883, 8000)
    client.connect('broker.hivemq.com', 1883, 8000)
    logging.debug('Subscribe to SGLCERIC/auth/rfid/{str(util.this_room.id)}')
    print('SGLCERIC/auth/rfid/'+str(util.this_room.id))
    client.subscribe('SGLCERIC/auth/rfid/'+str(util.this_room.id))
    client.subscribe('SGLCERIC/auth/fp/'+str(util.this_room.id))
    client.subscribe('SGLCERIC/sync/add/'+str(util.this_room.id))
    client.subscribe('SGLCERIC/sync/del/'+str(util.this_room.id))
    client.loop_forever()

def fingerprint_sensor():
    while True:
        try:
            fp.read()
        except Exception as e:
            print(e)

def rfid_sensor():
    while True:
        try:
            nfc.read()
        except Exception as e:
            print(e)

def touchpad_sensor():
    while True:
        try:
            time.sleep(5)
        except Exception as e:
            print(e)

if __name__ == "__main__":
    fp = fingerprint.FP(serial.Serial("/dev/serial0", baudrate=57600, timeout=1))
    nfc = rfid.RFID()
    main(debug=True)
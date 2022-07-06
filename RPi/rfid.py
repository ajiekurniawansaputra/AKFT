"""
RFID. SGLCERIC. CAPSTONE.
"""
import other as util
import pincam
import subprocess
import time
import datetime
import logging
import random
import threading

class RFID():
    def __init__(self):
        self.busy = False
            
    def read(self):
        logging.debug('Reading rfid')
        lines = subprocess.Popen("nfc-read", shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
        #lines = subprocess.check_output("/usr/bin/nfc-read", stderr=open('/dev/null','w'))
        out, _ = lines.communicate()
        lines = out.splitlines()
        
        uid_raw = [s for s in lines if "UID" in s]
        temp = uid_raw[0].split()
        uid="".join(temp[2:])
        
        if util.this_room.rfid_flag==0:
            return None
        
        logging.debug(f'Captured {uid}')
        logging.debug('Sending Payload')
        date = str(datetime.datetime.now().replace(microsecond=0))[2:]
        img_key = date+str(random.randint(1111, 9999))
        util.send_mqtt_encrypt('SGLCERIC/auth/rfid',
            {'date':date,
            'roomId':util.this_room.id,
            'data':uid,
            'img_key':img_key})
        pincam.take_photo(img_key)
        self.wait_for_response()
        logging.debug('Wait to be released')
        lines = subprocess.Popen("nfc-wait", shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        logging.debug('Released')
        return

    def response(self, client, userdata, msg):
        #only respond when rfid is expect the message, for when server respons late
        if self.busy == True:
            logging.debug('Read nfc response')
            msg, _ = util.receive_mqtt_decrypt(msg.payload)
            self.busy = False
            if msg['result'] == True:
                logging.debug('rfid Match')
                util.start_motor_tread(False)
                util.play_sound('RFID Match.mp3')
            elif msg['result'] == False:
                logging.debug('rfid not Match')
                util.play_sound('RFID not Match.mp3') #restricted or not registered
            return
        else:
            logging.debug('Unexpected message coming in, neglect the message')
        
    def wait_for_response(self):
        logging.debug('wait for response')
        self.busy = True
        startTime = time.time()
        while ((time.time()-startTime)<4) and (self.busy == True):
            pass
        self.busy = False
        if (time.time()-startTime)>=4:
            logging.debug('conection timeout')
            util.play_sound('Sorry. Please try again.mp3')
        return

def rfid_sensor():
    logging.debug('rfid thread start')
    while True:
        try:
            nfc.read()
        except Exception as e:
            print(e)

nfc = RFID()
rfid_thread = threading.Thread(name='rfid_sensor', target=rfid_sensor)
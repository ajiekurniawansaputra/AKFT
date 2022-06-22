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
        self.result = None
        self.thread_status = False

    def nfc_sub_thread(self):
        self.thread_status = True
        lines = subprocess.Popen("nfc-poll2", shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
        out, _ = lines.communicate()
        logging.debug(f'Captured out is {out}')
        self.result = out
        self.thread_status = False

    def read(self):
        logging.debug('Reading rfid')
        #start the threaad
        
        start_time = time.time()
        while (time.time() - start_time < 5) and (self.result is None) :
            pass
        if self.result is None:
            lines.kill()
            lines.terminate()
            self.thread_status = False
            return None

        lines = self.result.splitlines()
        for line in lines:
            line_content = lines
   
        uid_raw = [s for s in line_content if "UID" in s]
        temp = uid_raw[0].split()
        uid="".join(temp[2:])
        logging.debug(f'Captured {uid}')
        logging.debug('Sending Payload')
        img_key = random.randint(1111, 9999)
        date = str(datetime.datetime.now().replace(microsecond=0))[2:]
        util.send_mqtt_encrypt('SGLCERIC/auth/rfid',
            {'date':date,
            'roomId':util.this_room.id,
            'data':uid,
            'img_key':img_key})
        pincam.take_photo(date, img_key)
        self.wait_for_response()
        logging.debug('Wait to be released')
        subprocess.check_output("nfc-poll", stderr=subprocess.DEVNULL)
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
    while util.this_room.rfid_flag == True:
        try:
            nfc.read()
        except Exception as e:
            print(e)

nfc = RFID()
#rfid_thread = threading.Thread(name='rfid_sensor', target=rfid_sensor)
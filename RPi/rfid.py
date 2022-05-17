"""
RFID. SGLCERIC. CAPSTONE.
"""
import other as util
import pincam
import subprocess
import time
import datetime
import logging

class RFID():
    def __init__(self):
        self.busy = False
            
    def read(self):
        logging.debug('Reading rfid')
        lines = subprocess.check_output("/usr/bin/nfc-poll2", stderr=open('/dev/null','w'))
        buffer=[]
        for line in lines.splitlines():
            line_content = line.decode('UTF-8')
            line_content = line_content.split()
            if(line_content[0] =='UID'):
                buffer.append(line_content)
            else:
                pass
        uid = "".join(buffer[0][2:])
        logging.debug(f'Captured {uid}')
        logging.debug('Sending Payload')
        date = str(datetime.datetime.now().replace(microsecond=0))[2:]
        util.send_mqtt_encrypt('SGLCERIC/auth/rfid',
            {'date':date,
            'roomId':util.this_room.id,
            'data':uid})
        pincam.take_photo(date)
        self.wait_for_response()
        logging.debug('Wait to be released')
        subprocess.check_output("/usr/bin/nfc-poll", stderr=open('/dev/null','w'))
        logging.debug('Released')
        return

    def response(self, client, userdata, msg):
        #only respond when rfid is expect the message, for when server respons late
        #if self.busy == True:
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
        #else:
        #    logging.debug('Unexpected message coming in, neglect the message')
        
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

"""
Enrollment Device Rasberry APP. SGLCERIC. CAPSTONE.
"""
import other as util
import adafruit_fingerprint_edit as af
import serial
import subprocess
import logging
import time

def create_model():
    try:
        start_time = time.time()
        logging.debug('Place Finger')
        while finger.get_image() != af.OK:
            if (start_time+30 < time.time()):
                return -1
        ackPacket = finger.image_2_tz(1)
        if ackPacket != af.OK:
            raise Exception('Error templating')
        logging.debug('Remove Finger')
        while finger.get_image() == af.OK:
            pass
        logging.debug('Place Finger again')
        start_time = time.time()
        while finger.get_image() != af.OK:
            if (start_time+30 < time.time()):
                return -1
        ackPacket = finger.image_2_tz(2)
        if ackPacket != af.OK:
            raise Exception('Error templating')
        logging.debug('Creating Model')
        ackPacket = finger.create_model()
        if ackPacket != af.OK:
            raise Exception('Error modeling')
        ackPacket, model = finger.get_fpdata('char', 1)
        if ackPacket != af.OK:
            raise Exception('Error get model')
        return str(model)[1:-1]
    except Exception as e:
        logging.error(e)
        return None

def create_uid():
    try:
        logging.debug('Reading RFID')
        uid = None
        while uid == None:
            lines = subprocess.check_output("/usr/bin/nfc-poll2", stderr=open('/dev/null','w'))
            buffer=[]
            for line in lines.splitlines():
                line_content = line.decode('UTF-8')
                line_content = line_content.split()
                if(line_content[0] =='UID'):
                    buffer.append(line_content)
                else:
                    pass
            string=buffer[0][2:]
            uid = "".join(string)
        logging.debug('RFID captured')
        return uid
    except Exception as e:
        logging.error(e)
        return None

def on_message_command_enroll(client, userdata, msg):
    msg, _ = util.receive_mqtt_decrypt(msg.payload)
    user_id = msg['user_id']
    logging.debug('New registration command, id:{user_id}')
    model, uid = None, None
    util.client.publish(topic='SGLCERIC/enro/notif', payload='Taking Fingerprint')
    while(model is None):
        model = create_model()
    if model == -1 :
        logging.debug('Abort, Timeout')    
    util.client.publish(topic='SGLCERIC/enro/notif', payload='Taking RFID')
    while(uid is None):
        uid = create_uid()
    util.send_mqtt_encrypt("SGLCERIC/enro/model",
        {'user_id':user_id, 'uid':uid},
        {'model':model})
    logging.debug('Data sent, id:{user_id}')
    return

def main(debug=False):
    if debug == True:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
        
    util.client.message_callback_add('SGLCERIC/enro/id', on_message_command_enroll)
    util.client.connect('broker.hivemq.com', 1883, 8000)
    util.client.subscribe('SGLCERIC/enro/id')
    util.client.loop_forever()
    
def main2(debug=False):
    if debug == True:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
        
    util.client.connect('broker.hivemq.com', 1883, 8000)
    while True:
        model, uid = None, None
        try:
            logging.debug('Waiting for UID')
            while(uid is None):
                uid = create_uid()
            logging.debug('UID Present, waiting for FP. timeout in 30seconds')
            while(model is None):
                model = create_model()
            if model == -1:
                logging.debug('Timeout')
            else:
                logging.debug('FP Present, Sending data')
                util.send_mqtt_encrypt("SGLCERIC/enro/model",{'uid':uid},{'model':model})
                logging.debug('Data sent')
        except:
            model, uid = None, None
            logging.debug('error')

if __name__ == "__main__":
    finger = af.Adafruit_Fingerprint(serial.Serial("/dev/serial0", baudrate=57600, timeout=1))
    #main(debug=True)
    main2(debug=True)
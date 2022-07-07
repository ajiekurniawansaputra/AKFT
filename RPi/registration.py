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
        util.client.publish(topic='SGLCERIC/enro/notif', payload='Remove Finger')
        while finger.get_image() == af.OK:
            pass
        logging.debug('Place Finger again')
        util.client.publish(topic='SGLCERIC/enro/notif', payload='Place Finger Again')
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
        #should we add timeout timer?
        logging.debug('Reading RFID')
        process = subprocess.Popen(
            'nfc-wait',
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=True,
            encoding='utf-8',
            errors='replace'
        )    
        start_time = time.time()
        while (start_time+30 > time.time()):
            realtime_output = process.stdout.readline()
            if realtime_output == '' and process.poll() is not None:
                logging.debug('Released')
                break
            if realtime_output:
                raw = realtime_output.strip()
                if raw[:3]=="UID":
                    temp = raw.split()
                    uid="".join(temp[2:])
                    logging.debug(f'Captured {uid}')
                    logging.debug('Wait to be released')
                    break
            if uid:
                return uid
            else: 
                return -1
    except Exception as e:
        logging.error(e)
        return None

def on_message_command_enroll(client, userdata, msg):
    msg, _ = util.receive_mqtt_decrypt(msg.payload)
    user_id = msg['user_id']
    type_auth = msg['type']
    logging.debug('New registration command, id:{user_id}, for {type_auth}')
    if type_auth == 'fingerprint':
        model = None
        util.client.publish(topic='SGLCERIC/enro/notif', payload='Taking Fingerprint')
        while(model is None):
            model = create_model()
        if model == -1 :
            logging.debug('Abort, Timeout')
            util.client.publish(topic='SGLCERIC/enro/notif', payload='Timeout')
            return
        util.client.publish(topic='SGLCERIC/enro/notif', payload='Fingerprint taken')
        util.send_mqtt_encrypt("SGLCERIC/enro/model",
            {'user_id':user_id, 'type':type_auth},
            {'model':model})
    else:
        uid = None
        util.client.publish(topic='SGLCERIC/enro/notif', payload='Taking RFID')
        while(uid is None):
            uid = create_uid()
        if uid == -1 :
            logging.debug('Abort, Timeout')
            util.client.publish(topic='SGLCERIC/enro/notif', payload='Timeout')
            return
        util.client.publish(topic='SGLCERIC/enro/notif', payload='RFID taken')
        util.send_mqtt_encrypt("SGLCERIC/enro/model",{'user_id':user_id, 'type':type_auth, 'uid':uid})
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
    util.client.subscribe('SGLCERIC/enro/id', 2)
    util.client.loop_forever()

if __name__ == "__main__":
    finger = af.Adafruit_Fingerprint(serial.Serial("/dev/serial0", baudrate=57600, timeout=1))
    main(debug=True)
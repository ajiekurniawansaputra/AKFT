"""
Fingerprint. Pin. SGLCERIC. CAPSTONE.
"""
import other as util
import pincam
import adafruit_fingerprint_edit as adafruit_fingerprint
from busio import UART
from typing import Tuple
import RPi.GPIO as GPIO
import logging
import datetime
import time
import random
import serial
import threading

class FP(adafruit_fingerprint.Adafruit_Fingerprint):
    """Extend adafruit library"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup (18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    def __init__(self, uart: UART, passwd: Tuple[int, int, int, int] = (0, 0, 0, 0)):
        super().__init__(uart, passwd)
        self.busy = False
        
    def read(self):
        """Requests the sensor take the live scan and template it in char 1
        search for model and finally send data to mqtt broker
        """
        if self.busy == False and GPIO.input(18)==0 and util.this_room.fingerprint_flag == True:
            self.busy = True
            try:
                if self.get_image() != 0:
                    #no finger
                    return
                logging.debug('Templating')
                ack_packet = self.image_2_tz(1)
                if ack_packet != 0:
                    raise Exception('Error templating')
                logging.debug('Identify, Search for matching template')
                ack_packet = self.finger_search()
                self.action(ack_packet)
                if self.get_image() == 0:#di ilangin aja ga guna
                    logging.debug('Wait to be released')
                    while self.get_image() == 0:
                        pass
                    logging.debug('Released')
            except Exception as e:
                logging.error(e)
            finally:
                self.busy = False
        elif self.busy == True:#di ilangin aja ga guna
            pass

    def action(self, ack_packet):
        logging.debug(f'ack code: {ack_packet}')
        date = str(datetime.datetime.now().replace(microsecond=0))[2:]
        img_key = random.randint(1111, 9999)
        img_key = date+str(img_key)
        pincam.take_photo(img_key)
        if ack_packet == 0:    
            util.start_motor_tread(False)
            logging.debug(f'Fingerprint Match {self.finger_id}')
            util.play_sound('Fingerprint match.mp3')
            logging.debug('Send Payload')
            util.send_mqtt_encrypt('SGLCERIC/auth/fp',
                {'date':date,
                'user_id':self.finger_id,
                'room_id':util.this_room.id,
                'result': True,
                'img_key':img_key})
        elif ack_packet == 9:
            util.play_sound('Fingerprint match.mp3')
            util.send_mqtt_encrypt('SGLCERIC/auth/fp',
                {'date':date,
                'room_id':util.this_room.id,
                'result': False,
                'img_key':img_key})
        else:
            raise Exception
                
    def delete(self, client, userdata, msg):
        """ Receive payload data from MQTT broker, delete stored model at
        location detailed in payload.
        """
        try:
            msg, _ = util.receive_mqtt_decrypt(msg.payload)
            location = msg['location']
            startTime = time.time()
            while self.busy == True and ((time.time()-startTime)<30):
                #wait until the fp not busy
                pass
            if (time.time()-startTime)>=30:
                logging.debug('conection timeout')
                return
        except Exception as e:
            logging.error(e)
            return
        try:
            self.busy = True
            if location=='resync':
                ack_packet = self.empty_library()
                if ack_packet != 0:
                    raise Exception('Error formating')
                logging.debug('fingerprint formated')
                util.send_mqtt_encrypt('SGLCERIC/sync/del/ack',
                    {'room_id':util.this_room.id,'user_id':'resync'})
            elif location=='all':
                ack_packet = self.empty_library()
                if ack_packet != 0:
                    raise Exception('Error formating')
                logging.debug('fingerprint formated')
                util.send_mqtt_encrypt('SGLCERIC/sync/del/ack',
                    {'room_id':util.this_room.id,'user_id':'all'})
            else:
                user_id = msg['user_id']
                ack_packet = self.delete_model(int(location), 1)
                if ack_packet != 0:
                    raise Exception(f'Error Delete {location}')
                logging.debug(f'Model {location} Deleted')
                util.send_mqtt_encrypt('SGLCERIC/sync/del/ack',
                    {'room_id':util.this_room.id,'user_id':user_id})
        except Exception as e:
            logging.error(e)
        finally:
            self.busy = False

    def add(self, client, userdata, msg):
        """ Receive payload data from MQTT broker, add received model at
        location detailed in payload.
        """
        try:
            logging.debug('New add Command')
            msg, data = util.receive_mqtt_decrypt(msg.payload)
            location = msg['location']
            user_id = msg['user_id']
            model = data['model']
            startTime = time.time()
            while self.busy == True and ((time.time()-startTime)<10):
                time.sleep(1)
                #wait until the fp not busy
            if (time.time()-startTime)>=10:
                logging.debug('conection timeout')
                return
        except Exception as e:
            logging.error(e)
            return
        try:
            self.busy = True
            model = model.split(', ')
            model = [int(i) for i in model]
            ack_packet = self.send_fpdata(model, 'char', 2)
            if ack_packet != 0:
                raise Exception('sending model to sensor error')
            ack_packet = self.store_model(location,2)
            if ack_packet != 0:
                raise Exception('store model error')
            logging.debug(f'fingerprint saved {location}')
            util.send_mqtt_encrypt('SGLCERIC/sync/add/ack',
                    {'room_id':util.this_room.id,'user_id':user_id})
        except Exception as e:
            logging.error(e)
        finally:
            self.busy = False

def fingerprint_sensor():
    logging.debug('fingerprint thread start')
    while True:
        try:
            fp.read()
        except Exception as e:
            print(e)

fp = FP(serial.Serial("/dev/serial0", baudrate=57600, timeout=1))
fingerprint_thread = threading.Thread(name='fingerprint_sensor', target=fingerprint_sensor)
"""
Fingerprint. Pin. SGLCERIC. CAPSTONE.
"""
import other as util
import adafruit_fingerprint_edit as adafruit_fingerprint
from busio import UART
from typing import Tuple, List, Union
import RPi.GPIO as GPIO
import logging

class FP(adafruit_fingerprint.Adafruit_Fingerprint):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup (18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    def __init__(self, uart: UART, passwd: Tuple[int, int, int, int] = (0, 0, 0, 0)):
        super().__init__(uart, passwd = (0, 0, 0, 0))
        self.busy = False
        
    def read(self):
        """Requests the sensor take the live scan and template it in char 1
        search for model and finally send data to mqtt broker
        """
        if self.busy == False and GPIO.input(18)==0:
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
                #pincam.take_photo()
                self.action(ack_packet)
                if self.get_image() == 0:
                    logging.debug('Wait to be released')
                    while self.get_image() == 0:
                        pass
                    logging.debug('Released')
            except Exception as e:
                logging.error(e)
            finally:
                self.busy = False
        elif self.busy == True:
            pass

    def action(self, ack_packet):
        logging.debug(f'ack code: {ack_packet}')
        if ack_packet == 0:
            #we should open the door here
            logging.debug('Fingerprint Match')
            util.play_sound('Fingerprint match.mp3')
            logging.debug('Send Payload')
            util.send_mqtt_encrypt('SGLCERIC/auth/fp',
                {'sensor':'FP',
                #dont forget convert sensor_user_id to user_id
                'userId':self.finger_id,
                'roomId':util.this_room.id})
        elif ack_packet == 9:
            logging.debug('Fingerprint is rejected. Try another method')
            util.play_sound("Sorry, the room is restricted. you're not allowed to enter.mp3")
        else:
            raise Exception
                
    def delete(self, client, userdata, msg):
        """ Receive payload data from MQTT broker, delete stored model at
        location detailed in payload.
        """
        try:
            msg, _ = util.receive_mqtt_decrypt(msg.payload)
            location = msg['location']
            while self.busy == True:
                #wait until the fp not busy
                pass
            self.busy = True
            if location=='resync':
                ack_packet = self.empty_library()
                if ack_packet != 0:
                    raise Exception('Error formating')
                logging.debug('fingerprint formated')
                util.send_mqtt_encrypt('SGLCERIC/sync/re',
                    {'room_id':util.this_room.id})
            elif location=='all':
                ack_packet = self.empty_library()
                if ack_packet != 0:
                    raise Exception('Error formating')
                logging.debug('fingerprint formated')
            else:
                #delete a location
                pass
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
            model = data['model']
            while self.busy == True:
                #wait until the fp not busy
                pass
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
        except Exception as e:
            logging.error(e)
        finally:
            self.busy = False
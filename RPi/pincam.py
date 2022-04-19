"""
Camera. Pin. SGLCERIC. CAPSTONE.
"""
import other as util
import threading
import os
import logging
import base64
        
class PIN:
    pass

def take_photo(date):
    logging.debug('starting camera thread')
    take_photo_thread = threading.Thread(name='shoot', target=shoot, args=(date,))
    take_photo_thread.start()
    logging.debug('camera thread finished')
    
def shoot(date):
    logging.debug('taking a photo')
    os.system('libcamera-still -o img.jpg -t 1000 -n --width 1280 --height 720')
    logging.debug('photo captured')
    logging.debug('photo processing')
    with open("img.jpg", "rb") as imageFile:
        img = base64.b64encode(imageFile.read())
        img = img.decode('utf-8')
        print(img)
    logging.debug('Sending photo')
    util.send_mqtt_encrypt('SGLCERIC/img',{'date':date}, {'img':img})
    logging.debug('Sent')
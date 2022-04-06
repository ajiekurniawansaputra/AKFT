"""
Camera. Pin. SGLCERIC. CAPSTONE.
"""
import other as util
import threading
import os
import logging
        
class PIN:
    pass

def take_photo():
    logging.debug('starting camera thread')
    take_photo_thread = threading.Thread(name='shoot', target=shoot)
    take_photo_thread.start()
    logging.debug('camera thread finished')
    
def shoot():
    logging.debug('taking a photo')
    os.system('libcamera-still -o img.jpg -t 1000 -n --width 1280 --height 720')
    logging.debug('photo captured')
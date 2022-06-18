"""
Main Rasberry APP. SGLCERIC. CAPSTONE.
"""
import other as util
import pincam
import logging
    
def background():
    while True:
        try:
            logging.debug('Background thread start')
            client = util.client
            client.message_callback_add('SGLCERIC/auth/rfid/'+str(util.this_room.id), util.nfc.response)
            client.message_callback_add('SGLCERIC/sync/add/'+str(util.this_room.id), util.fp.add)
            client.message_callback_add('SGLCERIC/sync/del/'+str(util.this_room.id), util.fp.delete)
            client.message_callback_add('SGLCERIC/open', util.door_command)
            client.message_callback_add('SGLCERIC/pass/'+str(util.this_room.id), pincam.password_command)
            client.message_callback_add('SGLCERIC/set/'+str(util.this_room.id), util.set_command)
            client.will_set(topic='SGLCERIC/connection/'+str(util.this_room.id), payload='Device Lost Connection', qos=1, retain=True )
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            #client.tls_set('/home/pi/Documents/client/ca.crt', '/home/pi/Documents/client/client.crt', '/home/pi/Documents/client/client.key')
            client.connect('127.0.0.1', 8883)
            #client.connect('broker.hivemq.com', 1883, 10)
            client.loop_forever()
        except Exception as e:
            logging.debug('background thread failed, restarting', e)

def on_connect(client, userdata, flags, rc):
    if rc==0:
        logging.debug('MQTT Conected')
        client.publish(topic='SGLCERIC/connection/'+str(util.this_room.id), payload='Connected', qos=1, retain=True)
        client.connected_flag = True
        client.subscribe('SGLCERIC/auth/rfid/'+str(util.this_room.id))
        client.subscribe('SGLCERIC/sync/add/'+str(util.this_room.id))
        client.subscribe('SGLCERIC/sync/del/'+str(util.this_room.id))
        client.subscribe('SGLCERIC/open')
        client.subscribe('SGLCERIC/pass/'+str(util.this_room.id))
        client.subscribe('SGLCERIC/set/'+str(util.this_room.id))
    else:
        logging.debug('MQTT Conection Refused {rc}')
        
def on_disconnect(client, userdata, rc):
    logging.debug('MQTT Disconected, {rc}')
    client.connected_flag = False
    #add reconect funtion

if __name__ == "__main__":
    debug = True
    if debug == True:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    background()
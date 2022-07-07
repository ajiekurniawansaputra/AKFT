"""
Main Rasberry APP. SGLCERIC. CAPSTONE. Agustus lulus GASS.
"""
import other as util
import pincam
import fingerprint
import rfid
import logging
import threading

def background():
    while True:
        try:
            logging.debug('Background thread start')
            client = util.client
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            client.on_subscribe = on_subscribe
            for item in my_topic:
                client.message_callback_add(item['topic_name'], item["callback"])
            client.will_set(topic='SGLCERIC/connection/'+str(util.this_room.id), payload='Device Lost Connection', qos=1, retain=True )
            #client.tls_set('/home/pi/Documents/client/ca.crt', '/home/pi/Documents/client/client.crt', '/home/pi/Documents/client/client.key')
            client.connect('broker.hivemq.com', 1883, 10)
            #client.connect('127.0.0.1', 8883, 10)
            client.loop_forever()
        except Exception as e:
            logging.debug('background thread failed, restarting', e)

def on_connect(client, userdata, flags, rc):
    if rc==0:
        logging.debug('MQTT Conected')
        client.publish(topic='SGLCERIC/connection/'+str(util.this_room.id), payload='Connected', qos=1, retain=True)
        client.connected_flag = True
        for item in my_topic:
            client.subscribe(item["topic_name"], item["qos"])
    else:
        logging.debug('MQTT Conection Refused {rc}')
        
def on_disconnect(client, userdata, rc):
    logging.debug('MQTT Disconected, {client}, {userdata}, {rc}')
    client.connected_flag = False

def on_subscribe(client, userdata, mid, granted_qos):
    logging.debug('on_subscribe, {client}, {userdata}, {mid}, {granted_qos}')

my_topic = [ 
    {
        "topic_name" : 'SGLCERIC/auth/rfid/'+str(util.this_room.id),
        "callback" : rfid.nfc.response,
        "qos": 2,
        },
    {
        "topic_name" : 'SGLCERIC/sync/add/'+str(util.this_room.id),
        "callback" : fingerprint.fp.add,
        "qos": 2,
        },
    {
        "topic_name" : 'SGLCERIC/sync/del/'+str(util.this_room.id),
        "callback" : fingerprint.fp.delete,
        "qos": 2,
        },
    {
        "topic_name" : 'SGLCERIC/open',
        "callback" : util.door_command,
        "qos": 2,
        },
    {
        "topic_name" : 'SGLCERIC/pass/'+str(util.this_room.id),
        "callback" : pincam.password_command,
        "qos": 1,
        },
    {
        "topic_name" : 'SGLCERIC/set/'+str(util.this_room.id),
        "callback" : util.set_command,
        "qos": 1,
        },
]

if __name__ == "__main__":
    debug = True
    if debug == True:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    background_thread = threading.Thread(name='background', target=background)
    background_thread.start()
    rfid.rfid_thread.start()
    pincam.pin_thread.start()
    fingerprint.fingerprint_thread.start()
    
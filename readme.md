# Documentation
this documentation contain information about mqtt topic used to subscribe and publish in akft capstone project

## Subscribe
list of topic that the device is subscribed to and ready to receive message.

### 1. 'SGLCERIC/auth/rfid/'+str(this_room.id)
receive authentication result response, expected payload json
- qos : 2
- retain : False
```
{
    'msg':{'result':(bollean)},
    'data':{None}
    }
```
Response must be received before timeout (currently set to 4s). This response is expected after device publish to _('SGLCERIC/auth/rfid')_

### 2.	'SGLCERIC/sync/add/'+str(this_room.id)
receive model data to be saved into device in a location, location is integer in range of 1-1000, expected payload json 
- qos : 2
- retain : False
```
{
    'msg':{'location': (int)},
    'data':{'model':(model_data)}
    }
```

### 3. 'SGLCERIC/sync/del/'+str(this_room.id)
receive a command to delete model in the device, expected payload json
- qos : 2
- retain : False
```
{
    'msg':{'location': (int/string)},
    'data':{None}
    }
```
location could be string or int.
* string
    * _'all'_ command to delete all model
    * _'resync'_ command to delete all model and send room_id to _'SGLCERIC/sync/re'_
* int
delete one model in the location spesified

### 4. 'SGLCERIC/enro/id'
receive a command to acquire fingerprint model or uid, expected payload json
- qos : 2
- retain : False
```
{
    'msg':{'user_id': (int), 'type': (string)},
    'data':{None}
    }
```
device will capture new fingerprint model or uid and then send it to _'SGLCERIC/enro/model'_
* string
    * _'fingerprint'_ 
    * _'SIM'_
    * _'KTP'_
    * _'KTM'_

### 5. 'SGLCERIC/open'
receive command to open door, boolean
- qos : 1
- retain : False
```
{
    'msg':{'state': Boolean},
    'data':{None}
    }
```

### 6. 'SGLCERIC/pass/'+str(this_room.id)
receive command to change room pin
- qos : 1
- retain : True
```
{
    'msg':{'password': (int)},
    'data':{None}
    }
```

### 6. 'SGLCERIC/set/'+str(this_room.id)
receive command to set authentication method
- qos : 1
- retain : True
```
{
    'msg':{
        'fingerprint': (Boolean),
        'rfid': (Boolean),
        'pin': (Boolean)
        },
    'data':{None}
    }
```

## Publish
list of topic the device will publish to
### 1. 'SGLCERIC/auth/fp'
trigered when device find a match 
```
{
    'msg':{
        'date':str(date),
        'userId':(int),
        'roomId':(int),
        'img_key':(int),
        'result':(bollean)},
    'data':{None}
    }
```
date is in str, need to be converted to datetime first
user_id is location in which the model is saved

### 2. 'SGLCERIC/auth/rfid'
triggered when device read uid
```
{
    'msg':{
        'date':str(date),
        'roomId':(int),
        'data':uid,
        'img_key':(int),},
    'data':{None}
    }
```
date is in str, need to be converted to datetime first

### 3. 'SGLCERIC/enro/model'
triggered after device receive command from topic _'SGLCERIC/enro/id'_ and succesfully acquire fp model or uid
```
{
    'msg':{'user_id':int, 'type':String(uid), 'uid':uid},
    'data':{None}
    }
or
{
    'msg':{'user_id':int, 'type':String(fingerprint)},
    'data':{'model':model}
    }
```
_'SGLCERIC/enro/notif'_ notification while taking data on the device, curently not encrypted

### 4. 'SGLCERIC/connection/(roomid)'
triggered when device lost conection or connected
```
{True/False}
```
curently not encrypted

### 5. 'SGLCERIC/sync/del/ack'
triggered when a delete command was succesfully proceed.
```
{
    'msg':{'user_id': (string), 'room_id': (int)},
    'data':{None}
    }
```

### 6. 'SGLCERIC/sync/add/ack'
triggered when an 'add' command was succesfully proceed.
```
{
    'msg':{'user_id': (string), 'room_id': (int)},
    'data':{None}
    }
```

### 7. 'SGLCERIC/img'
triggered when an authentication is attempted.
```
{
    'msg':{'date':str(date), 'img_key':(int)},
    'data':{'img':img}
    }
```
curently image is encoded as string with utf-8, filename contain img_key.

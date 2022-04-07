# Documentation
this documentation contain information about mqtt topic used to subscribe and publish in akft capstone project

## Subscribe
list of topic that the device is subscribed to and ready to receive message.

### 1. 'SGLCERIC/auth/rfid/'+str(this_room.id)
receive authentication result response, expected payload json
```
{
    'msg':{'result':True/False(bollean)},
    'data':{None}
    }
```
Response must be received before timeout (currently set to 4s). This response is expected after device publish to _('SGLCERIC/auth/rfid')_

### 2.	'SGLCERIC/sync/add/'+str(this_room.id)
receive model data to be saved into device in a location, location is integer in range of 1-1000, expected payload json 
```
{
    'msg':{'location': (int)},
    'data':{'model':(model_data)}
    }
```

### 3. 'SGLCERIC/sync/del/'+str(this_room.id)
receive a command to delete model in the device, expected payload json
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
receive a command to get fingerprint model and uid, expected payload json
```
{
    'msg':{'user_id': (int)},
    'data':{None}
    }
```
device will capture new fingerprint model and uid and then send it to _'SGLCERIC/enro/model'_

### 5. 'SGLCERIC/open'
receive command to open door, boolean
{
    'msg':{'state': True},
    'data':{None}
    }

## Publish
list of topic the device will publish to
### 1. 'SGLCERIC/auth/fp'
trigered when device find a match 
```
{
    'msg':{
        'date':str(date),
        'userId':finger_id,
        'roomId':this_room.id
        'result':True/False(bollean)},
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
        'roomId':this_room.id,
        'data':uid},
    'data':{None}
    }
```

### 3. 'SGLCERIC/enro/model'
triggered when device receive command from topic _'SGLCERIC/enro/id'_
```
{
    'msg':{
        'user_id':(int),
        'uid':int},
    'data':{'model':model}
}
```

### 3. 'SGLCERIC/connection/(roomid)'
triggered when device lost conection or connected
```
{True/False}
```
curently not encrypted
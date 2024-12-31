import os
from dotenv import load_dotenv
from pytz import timezone
import search
import random
from datetime import datetime, timedelta
from typing import List
from fastapi import FastAPI, Query

load_dotenv()

app = FastAPI()

DATABASE = {
    'name': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT')),
}

now = datetime.now(timezone('US/Mountain')).strftime('%X')
date_time = datetime.now(timezone('US/Mountain')).strftime('%m/%d %X')
dayOfWeek = datetime.now(timezone('US/Mountain')).strftime('%a')


@app.get("/now/{building}")
async def search_now(building):
    print("Request Time: " + date_time)
    result = search.lookup(building.upper(), '', 'now', '', '', '')
    if building.upper() == 'ANY':
        result = sorted(random.sample(result, 24), key=lambda x: x[1])
    return {"Rooms": result
            }


@app.get("/at/{building}/{time}")
async def search_at(building,
                    time: str,
                    d: List[str] = Query(default=[], max_length=2)):
    print("Request Time: " + time)
    if len(d) == 0:
        input_days = d
    else:
        input_days = [x.capitalize() for x in d]
    print(input_days)
    result = search.lookup(building.upper(), '', 'at', time, '', input_days)
    return {"Rooms": result}


@app.get("/between/{building}/{timeA}/{timeB}")
async def search_between(building,
                         timeA: str,
                         timeB: str,
                         d: List[str] = Query(default=[], max_length=2)):
    print("Request Time: " + timeA + " to " + timeB)
    if len(d) == 0:
        input_days = d
    else:
        input_days = [x.capitalize() for x in d]

    result = search.lookup(building.upper(), '', 'between', timeA, timeB, input_days)
    return {"Rooms": result}


@app.get("/when/{building}/{room}")
async def search_when(building, room):
    actioned_date = datetime.utcnow() - timedelta(hours=float(datetime.now(timezone('US/Mountain')).strftime('%z')[2]))
    my_date = datetime.combine(actioned_date.date(), actioned_date.time(), timezone('US/Mountain'))

    print("Request Time: " + date_time)
    day_events = search.lookup(building.upper(), room, 'when', '', '', [])
    inUse = False

    if len(day_events) != 0:
        busy_since = datetime.combine(datetime.now().date(), day_events[0][1], timezone('US/Mountain'))
        busy_until = datetime.combine(datetime.now().date(), day_events[0][2], timezone('US/Mountain'))
        if len(day_events) == 1:
            busy_until = datetime.combine(datetime.now().date(), day_events[0][2], timezone('US/Mountain'))
        else:
            for i in range(len(day_events) - 1):
                end_time = datetime.combine(datetime.now().date(), day_events[i][2], timezone('US/Mountain'))
                next_start_time = datetime.combine(datetime.now().date(), day_events[i + 1][1], timezone('US/Mountain'))
                if (next_start_time - end_time).seconds / 60 > 15:
                    busy_until = end_time
                    break
        if busy_until > my_date > busy_since:
            inUse = True
    else:
        return {"busySince": '',
                "busyUntil": '',
                "isInUse": False
                }
    return {"busySince": busy_since.strftime('%Y-%m-%dT%X-07:00'),
            "busyUntil": busy_until.strftime('%Y-%m-%dT%X-07:00'),
            "isInUse": inUse
            }

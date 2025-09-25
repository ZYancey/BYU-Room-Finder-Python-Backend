import os
import random
import search
import threading
import time
from datetime import datetime, timedelta
from typing import List
from fastapi import FastAPI, Query, HTTPException
from dotenv import load_dotenv
from pytz import timezone

load_dotenv()

app = FastAPI()

# Global variable to store service health status
# True = last search operation succeeded, False = last search operation failed
LAST_SEARCH_SUCCESS = True
SERVICE_STATUS_LOCK = threading.Lock()

now = datetime.now(timezone('US/Mountain')).strftime('%X')
date_time = datetime.now(timezone('US/Mountain')).strftime('%m/%d %X')
dayOfWeek = datetime.now(timezone('US/Mountain')).strftime('%a')


def update_search_status(success: bool):
    """Update the global search success status"""
    global LAST_SEARCH_SUCCESS
    with SERVICE_STATUS_LOCK:
        LAST_SEARCH_SUCCESS = success


@app.get("/now/{building}")
async def search_now(building):
    print("Request Time: " + date_time)
    try:
        result = search.lookup(building.upper(), '', 'now', '', '', '')
        update_search_status(True)  # Mark as successful
        if building.upper() == 'ANY':
            result = sorted(random.sample(result, min(24, len(result))), key=lambda x: x[1])
        return {"Rooms": result}
    except Exception as e:
        update_search_status(False)  # Mark as failed
        print(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search operation failed: {str(e)}")


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
    try:
        result = search.lookup(building.upper(), '', 'at', time, '', input_days)
        update_search_status(True)  # Mark as successful
        return {"Rooms": result}
    except Exception as e:
        update_search_status(False)  # Mark as failed
        print(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search operation failed: {str(e)}")


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

    try:
        result = search.lookup(building.upper(), '', 'between', timeA, timeB, input_days)
        update_search_status(True)  # Mark as successful
        return {"Rooms": result}
    except Exception as e:
        update_search_status(False)  # Mark as failed
        print(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search operation failed: {str(e)}")


@app.get("/when/{building}/{room}")
async def search_when(building, room):
    actioned_date = datetime.utcnow() - timedelta(hours=float(datetime.now(timezone('US/Mountain')).strftime('%z')[2]))
    my_date = datetime.combine(actioned_date.date(), actioned_date.time(), timezone('US/Mountain'))

    print("Request Time: " + date_time)
    try:
        day_events = search.lookup(building.upper(), room, 'when', '', '', [])
        update_search_status(True)  # Mark as successful
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
    except Exception as e:
        update_search_status(False)  # Mark as failed
        print(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search operation failed: {str(e)}")


@app.get("/status")
async def get_status():
    """Status endpoint that returns 200 if last search operation succeeded, 500 if it failed"""
    with SERVICE_STATUS_LOCK:
        if LAST_SEARCH_SUCCESS:
            return {"status": "healthy", "last_search": "successful"}
        else:
            raise HTTPException(status_code=500, detail="Last search operation failed")

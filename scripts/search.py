import os
import psycopg2
import re
from datetime import datetime
from peewee import SQL
from pytz import timezone
from typing import Union
from dotenv import load_dotenv
from models import Buildings, Events, Rooms, database

load_dotenv()

DAY_MAP = {
    'Mon': 'M',
    'Tue': 'T',
    'Wed': 'W',
    'Thu': 'Th',
    'Fri': 'F',
    'Sat': 'Sa',
    'Sun': 'Su',
}

UTAH_TIMEZONE = timezone('US/Mountain')


def run_query(query, connection=None, cursor=None):
    try:
        connection = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = connection.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        return result
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to Postgres", error)
        if connection:
            cursor.close()
            connection.close()
    finally:
        if connection:
            cursor.close()
            connection.close()


now = datetime.now(timezone('US/Mountain')).strftime('%X')
dayOfWeek = datetime.now(timezone('US/Mountain')).strftime('%a')


def lookup(input_building, input_room, input_time_type, input_timeA, input_timeB, input_days):
    database.connect()
    result = Rooms.select(Rooms, Buildings) \
        .join(Buildings) \
        .where(Rooms.description == 'CLASSROOM')

    building_name = input_building
    if building_name != 'ANY':
        building = Buildings.get(Buildings.name == building_name)
        result = result.where(Rooms.building == building)

    conflicting_events = Events.select()
    current_events = Events.select()
    days: Union[list[str], list] = []
    for i in input_days:
        days.append(i)

    if input_time_type == 'now':
        day = DAY_MAP[dayOfWeek]
        conflicting_events = conflicting_events \
            .where(Events.days.contains(day)) \
            .where((Events.start_time <= now) & (Events.end_time > now))
    elif input_time_type == 'when':
        day = DAY_MAP[dayOfWeek]
        current_events = current_events \
            .select(Events.name, Events.start_time, Events.end_time) \
            .join(Rooms, on=Events.room_id) \
            .join(Buildings, on=Rooms.building_id) \
            .where(Buildings.name == input_building) \
            .where(Rooms.number == input_room) \
            .where(Events.end_time >= now) \
            .where(SQL("days && ARRAY['%s']::weekday[]" % day)) \
            .order_by(Events.start_time) \
            .limit(5)
    elif input_time_type == 'at':
        if not re.match("^[0-2][0-9]:[0-5][0-9]:[0-5][0-9]$", input_timeA):
            database.close()
            raise Exception("from and to times required for time range")
        time_temp = input_timeA
        conflicting_events = conflicting_events \
            .where(SQL("days && ARRAY[%s]::weekday[]" % days)) \
            .where(
            (Events.start_time <= time_temp) & (Events.end_time > time_temp)
        )
    elif input_time_type == 'between':
        if not re.match("^[0-2][0-9]:[0-5][0-9]:[0-5][0-9]$", input_timeA) or \
                not re.match("^[0-2][0-9]:[0-5][0-9]:[0-5][0-9]$", input_timeB):
            database.close()
            raise Exception("from and to times required for time range")
        conflicting_events = conflicting_events \
            .where(SQL("days && ARRAY[%s]::weekday[]" % days)) \
            .where(
            SQL(
                "timerange(start_time::time, end_time::time, '()') && timerange('%s'::time, '%s'::time)" %
                (input_timeA, input_timeB)
            )
        )

    if input_time_type == "when":
        query_str = str(current_events)
    else:
        result = result \
            .where(Rooms.id.not_in([*map(lambda x: x.room_id, conflicting_events)])) \
            .order_by(Buildings.name, Rooms.number)
        query_str = str(result.select(Rooms.number, Buildings.name))

    database.close()
    return run_query(query_str)

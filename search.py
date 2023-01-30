from datetime import datetime

from peewee import SQL
from pytz import timezone

import psycopg2
import re

from models import Buildings, Events, Rooms, database

DAY_MAP = {
    'Mon': 'M',
    'Tue': 'T',
    'Wed': 'W',
    'Thu': 'Th',
    'Fri': 'F',
    'Sat': 'Sa',
    'Sun': 'Su',
}

# TODO: make this dynamic for earliest/latest hours
TIMES = [f"{h % 12 or 12}:{m:02} {'AM' if h < 12 else 'PM'}" for h in range(6, 23) for m in range(0, 60, 15)]

UTAH_TIMEZONE = timezone('US/Mountain')


def read_arguments():
    print("Welcome to BYU Room Finder Backend")
    print("[ now | at | between ]")
    type = input("Enter type: ")

    print("[ any | MARB | TMCB | ... ]")
    building = input("Enter building name: ")

    if type == 'at' or type == 'between':
        print("[ ##:##:## - 24hr Time Format ]")
        timeA = input("Enter time: ")
        if type == 'between':
            timeB = input("Enter time: ")
        else:
            timeB = ''
        print("[ S | M | T | W | Th | F | Sa ]")
        days = str("'" + input("Enter days: ") + "'")
    else:
        timeA = ''
        timeB = ''
        days = "''"
    return building, type, timeA, timeB, days


def run_query(query):
    try:
        conn = psycopg2.connect(
            host="192.168.50.235",
            port="49154",
            database="byu",
            user="postgres",
            password="postgres"
        )
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchall()
        return result
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
    finally:
        if conn:
            cur.close()
            conn.close()


def lookup(input_building, input_time_type, input_timeA, input_timeB, input_days):
    database.connect()
    result = []
    buildings = Buildings.select()
    show_results = 'none'
    if True:
        result = Rooms.select(Rooms, Buildings) \
            .join(Buildings) \
            .where(Rooms.description == 'CLASSROOM')

        building_name = input_building
        if building_name != 'any':
            building = Buildings.get(Buildings.name == building_name)
            result = result.where(Rooms.building == building)

        conflicting_events = Events.select()
        days = input_days

        if input_time_type == 'now':
            now = datetime.now(UTAH_TIMEZONE).time()
            day = DAY_MAP[now.strftime('%a')]
            conflicting_events = conflicting_events \
                .where(Events.days.contains(day)) \
                .where(
                (Events.start_time <= now) & (Events.end_time > now)
            )
        elif input_time_type == 'at':
            if not re.match("^[0-2][0-9]:[0-5][0-9]:[0-5][0-9]$", input_timeA):
                raise Exception("from and to times required for time range")
            time = input_timeA
            conflicting_events = conflicting_events \
                .where(SQL("days && ARRAY[%s]::weekday[]" % days)) \
                .where(
                (Events.start_time <= time) & (Events.end_time > time)
            )
        elif input_time_type == 'between':
            if not re.match("^[0-2][0-9]:[0-5][0-9]:[0-5][0-9]$", input_timeA) or \
                    not re.match("^[0-2][0-9]:[0-5][0-9]:[0-5][0-9]$", input_timeB):
                raise Exception("from and to times required for time range")
            conflicting_events = conflicting_events \
                .where(SQL("days && ARRAY[%s]::weekday[]" % days)) \
                .where(
                    SQL(
                        "timerange(start_time::time, end_time::time, '()') && timerange('%s'::time, '%s'::time)" %
                        (input_timeA, input_timeB)
                    )
                )

        result = result \
            .where(Rooms.id.not_in([*map(lambda x: x.room_id, conflicting_events)])) \
            .order_by(Buildings.name, Rooms.number)

        show_results = 'no_results' if len(result) == 0 else 'all'

        query_str = str(result.select(Rooms.number, Buildings.name))

    database.close()

    return run_query(query_str)


if __name__ == '__main__':
    building, type, timeA, timeB, days = read_arguments()
    print(lookup(building, type, timeA, timeB, days))

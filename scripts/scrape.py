### USAGE:
# Run python scrape.py from the same folder that has the `out` directory, with the first argument
# being the semester to scrape in YYYYT format (with T being a term, 1-5) and then a Postgres connection
# string, e.g.:
#
# python scrape.py 20224 postgresql://localhost:5342/byu
#
# Note that the terms are a bit odd. It seems to be:
# Winter: 1
# Spring: 3
# Summer: 4
# Fall: 5
#
# Just check the requests in the web app.
from datetime import datetime
import os
import re
import sys
import time
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import psycopg2
import requests

load_dotenv()

COLUMNS = {
    "course": 0,
    "class_period": 7,
    "days": 8,
}

TIME_FORMAT = "%I:%M%p"

# Determine the YEAR_TERM from the command parameters
if len(sys.argv) > 1:
    YEAR_TERM = sys.argv[1]
else:
    current_date = datetime.now()
    year = current_date.year
    month = current_date.month
    if 1 <= month <= 4:
        term = 1  # Winter
    elif 5 <= month <= 6:
        term = 3  # Spring
    elif 7 <= month <= 8:
        term = 4  # Summer
    else:
        term = 5  # Fall
    YEAR_TERM = f"{year}{term}"
    print(f"Automatically determined YEAR_TERM: {YEAR_TERM}")
    print("Usage: python scrape.py <YYYYT>")

def open_or_download_file(filename, fetch_fn):
    try:
        with open(f"scraper/out/{YEAR_TERM}/{filename}", "r", encoding="utf-8") as fh:
            html = fh.read()
    except FileNotFoundError:
        html = fetch_fn()
        with open(f"out/{YEAR_TERM}/{filename}", "w", encoding="utf-8") as fh:
            print(html, file=fh)
        time.sleep(0.1)  # to avoid overwhelming the server
    return html

def get_class_info(row):
    try:
        start, end = (
            row.find_all("td")[COLUMNS["class_period"]]
            .text.strip()
            .replace("a", "am")
            .replace("p", "pm")
            .split(" - ")
        )
    except ValueError as e:
        print(e)
        start, end = '01:00am', '01:00am'

    start = time.strptime(start, TIME_FORMAT)
    end = time.strptime(end, TIME_FORMAT)
    days = row.find_all("td")[COLUMNS["days"]].text.strip()
    return {
        "name": row.find_all("td")[COLUMNS["course"]].text.strip(),
        "start": start,
        "end": end,
        "days": ["M", "T", "W", "Th", "F"]
        if days == "Daily"
        else re.findall(r"(Th|Sa|Su|M|T|W|F)", days),
    }

def get_room_info(building, room):
    html = open_or_download_file(
        f"{building}-{room}.html",
        lambda: requests.post(
            "https://y.byu.edu/class_schedule/cgi/classRoom2.cgi",
            data={
                "year_term": YEAR_TERM,
                "building": building,
                "room": room,
            },
            timeout=10,
        ).text,
    )
    result = {}
    soup = BeautifulSoup(html, "html.parser")
    result["description"] = soup.find("input", attrs={"name": "room_desc"})["value"]
    result["capacity"] = int(soup.find("input", attrs={"name": "capacity"})["value"])
    result["classes"] = []
    schedule_table = soup.find("th", string=re.compile("Instructor"))  # .parent.parent
    if schedule_table:
        schedule_table = schedule_table.parent.parent
        for row in schedule_table.find_all("tr")[1:]:
            result["classes"].append(get_class_info(row))
    return result

def get_buildings_rooms(buildings):
    for building in buildings:
        html = open_or_download_file(
            f"{building}-list.html",
            lambda building=building: requests.post(
                "https://y.byu.edu/class_schedule/cgi/classRoom2.cgi",
                data={
                    "e": "@loadRooms",
                    "year_term": YEAR_TERM,
                    "building": building,
                },
                timeout=10,
            ).text,
        )
        soup = BeautifulSoup(html, "html.parser")
        yield (building, [tag.text for tag in soup.find("table").find_all("a")])

def main():
    try:
        os.mkdir(f"scraper/out/{YEAR_TERM}")
    except FileExistsError:
        print("Folder exists.")

    # Load database connection details from environment variables
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')

    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password
    )
    cur = conn.cursor()
    cur.execute("TRUNCATE buildings CASCADE")
    index = open_or_download_file(
        "classRoom2.cgi",
        lambda: requests.post(
            "https://y.byu.edu/class_schedule/cgi/classRoom2.cgi",
            data={ "year_term": YEAR_TERM, },
            timeout=10
        ).text
    )

    soup = BeautifulSoup(index, "html.parser")
    buildings = [
        tag["value"]
        for tag in soup.find("select", attrs={"name": "Building"}).find_all(
            "option"
        )
    ]

    classes = 0
    for building, rooms in get_buildings_rooms(buildings):
        print(building)
        cur.execute(
            "INSERT INTO buildings (name) VALUES (%s) RETURNING id", (building,)
        )
        building_id = cur.fetchone()[0]
        for room in rooms:
            room_info = get_room_info(building, room)
            cur.execute(
                "INSERT INTO rooms (building_id, number, description) VALUES (%s, %s, %s) RETURNING id",
                (building_id, room, room_info["description"]),
            )
            room_id = cur.fetchone()[0]
            for class_ in room_info["classes"]:
                print(f"    {classes:04}: {class_['name']}")
                classes += 1
                cur.execute(
                    """INSERT INTO events (room_id, name, days, start_time, end_time)
                        VALUES (%s, %s, %s::weekday[], %s, %s)""",
                    (
                        room_id,
                        class_["name"],
                        class_["days"],
                        time.strftime("%H:%M:00 MST", class_["start"]),
                        time.strftime("%H:%M:00 MST", class_["end"]),
                    ),
                )
            conn.commit()

if __name__ == "__main__":
    main()

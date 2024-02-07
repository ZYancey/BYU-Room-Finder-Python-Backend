import os
import re
import sys
import time

from bs4 import BeautifulSoup
import psycopg2
import requests

YEAR_TERM = "20235"


def open_or_download_file(filename, fetch_fn):
    try:
        with open(f"out/{YEAR_TERM}/{filename}", "r") as fh:
            html = fh.read()
    except FileNotFoundError:
        html = fetch_fn()
        with open(f"out/{YEAR_TERM}/{filename}", "w") as fh:
            print(html, file=fh)
        time.sleep(0.1)  # to avoid overwhelming the server
    return html

def get_courses():
    for building in buildings:
        html = open_or_download_file(
            f"{building}-list.html",
            lambda: requests.post(
                "https://y.byu.edu/class_schedule/cgi/classRoom2.cgi",
                data={
                    "e": "@loadRooms",
                    "year_term": YEAR_TERM,
                    "building": building,
                },
            ).text,
        )
        soup = BeautifulSoup(html, "html.parser")
        yield (building, [tag.text for tag in soup.find("table").find_all("a")])

def get_sections(buildings):
    for building in buildings:
        html = open_or_download_file(
            f"{building}-list.html",
            lambda: requests.post(
                "https://y.byu.edu/class_schedule/cgi/classRoom2.cgi",
                data={
                    "e": "@loadRooms",
                    "year_term": YEAR_TERM,
                    "building": building,
                },
            ).text,
        )
        soup = BeautifulSoup(html, "html.parser")
        yield (building, [tag.text for tag in soup.find("table").find_all("a")])

def get_class_info(building='JKB', room='TEST'):
    html = open_or_download_file(
        f"{building}-{room}.html",
        lambda: requests.post(
            "https://y.byu.edu/class_schedule/cgi/classScheduleRecord.cgi",
            data={
                "year_term": YEAR_TERM,
                "curriculum_id": '14033',
                "section_number": '001',
                "title_code": "000"
            },
        ).text,
    )
    # result = {}
    # soup = BeautifulSoup(html, "html.parser")
    # result["description"] = soup.find("input", attrs={"name": "room_desc"})["value"]
    # result["capacity"] = int(soup.find("input", attrs={"name": "capacity"})["value"])
    # result["classes"] = []
    # schedule_table = soup.find("th", string=re.compile("Instructor"))  # .parent.parent
    # if schedule_table:
    #     schedule_table = schedule_table.parent.parent
    #     for row in schedule_table.find_all("tr")[1:]:
    #         result["classes"].append(get_class_info(row))
    # return result

get_class_info()
from peewee import CharField, Field, ForeignKeyField, Model, TimeField, PrimaryKeyField, IntegerField
from playhouse.db_url import connect
from playhouse.postgres_ext import ArrayField
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get database connection details from environment variables
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')

# Construct the database URL
db_url = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

# Connect to the database
database = connect(url=db_url)


class BaseModel(Model):
    class Meta:
        database = database


class Buildings(BaseModel):
    name = CharField()

    class Meta:
        table_name = 'buildings'


class Rooms(BaseModel):
    id = PrimaryKeyField()
    building_id = IntegerField()
    building = ForeignKeyField(column_name='building_id', field='id', model=Buildings)
    description = CharField()
    number = CharField()

    class Meta:
        table_name = 'rooms'


class WeekdayField(Field):
    field_type = 'weekday'


class Events(BaseModel):
    id = PrimaryKeyField()
    room_id = IntegerField()
    days = ArrayField(WeekdayField)
    end_time = TimeField()
    name = CharField()
    room = ForeignKeyField(column_name='room_id', field='id', model=Rooms)
    start_time = TimeField()

    class Meta:
        table_name = 'events'
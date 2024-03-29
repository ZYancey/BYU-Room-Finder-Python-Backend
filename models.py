from peewee import CharField, Field, ForeignKeyField, Model, TimeField
from playhouse.db_url import connect
from playhouse.postgres_ext import ArrayField

database = connect(url='postgresql://192.168.50.92:49154/byu?user=postgres&password=postgres')


class BaseModel(Model):
    class Meta:
        database = database


class Buildings(BaseModel):
    name = CharField()

    class Meta:
        table_name = 'buildings'


class Rooms(BaseModel):
    building = ForeignKeyField(column_name='building_id', field='id', model=Buildings)
    description = CharField()
    number = CharField()

    class Meta:
        table_name = 'rooms'


class WeekdayField(Field):
    field_type = 'weekday'


class Events(BaseModel):
    days = ArrayField(WeekdayField)
    end_time = TimeField()
    name = CharField()
    room = ForeignKeyField(column_name='room_id', field='id', model=Rooms)
    start_time = TimeField()

    class Meta:
        table_name = 'events'

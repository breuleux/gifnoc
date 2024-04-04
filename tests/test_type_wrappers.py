import json

from apischema import deserialize, serialize

from gifnoc.schema import deserialization_schema
from gifnoc.type_wrappers import Extensible, TaggedSubclass

from .models import Point, Point3D, Point4D


def test_TaggedSubclass():
    p4d = Point4D(x=1, y=2, z=3, w=4)
    ser = serialize(TaggedSubclass[Point], p4d)
    deser = deserialize(TaggedSubclass[Point], ser)
    assert deser == p4d


def test_TaggedSubclass_representation(data_regression):
    points = [
        Point(x=1, y=2),
        Point3D(x=11, y=22, z=33),
        Point4D(x=111, y=222, z=333, w=444),
    ]
    ser = serialize(list[TaggedSubclass[Point]], points)
    data_regression.check(ser)


def test_TaggedSubclass_schema(file_regression):
    schema = deserialization_schema(TaggedSubclass[Point])
    file_regression.check(json.dumps(schema, indent=4), extension=".json")


def test_Extensible():
    ser = {
        "x": 1,
        "y": 2,
        "garbage": 3,
    }
    deser = deserialize(Extensible[Point], ser)
    assert deser == Point(x=1, y=2)
    ser2 = serialize(Extensible[Point], deser)
    assert ser2 == {
        "x": 1,
        "y": 2,
    }


def test_Extensible_schema(file_regression):
    schema = deserialization_schema(Extensible[Point])
    file_regression.check(json.dumps(schema, indent=4), extension=".json")

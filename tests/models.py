from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Union


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Point3D(Point):
    z: float


@dataclass
class Point4D(Point3D):
    w: float


@dataclass
class Member:
    # Member name
    name: str
    # User name
    username: str
    # Home directory
    home: Path
    # Date the member started working
    start: date
    # Date the member stopped working
    end: Union[date, None]


@dataclass
class Machine:
    name: str
    os: str
    ngpus: int


@dataclass
class Organization:
    # Name of the organization
    name: str
    # Whether the organization is a nonprofit
    nonprofit: bool
    # Members of the organization
    members: list[Member]
    # Machines the organization owns
    machines: list[Machine]
    # User passwords
    passwords: dict[str, str] = field(default_factory=dict)


@dataclass
class Person:
    name: str
    age: int
    fabulous: bool = False


@dataclass
class City:
    people: list[Person]


@dataclass
class Atlas:
    cities: dict[str, City]

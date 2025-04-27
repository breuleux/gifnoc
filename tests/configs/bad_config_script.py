from dataclasses import dataclass

from gifnoc import define, use


@dataclass
class TestConfig:
    value: bool


define("test", TestConfig)

with use({"test": {"value": "not-a-boolean"}}):
    pass

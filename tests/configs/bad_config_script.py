from dataclasses import dataclass

from gifnoc import define, use


@dataclass
class TestConfig:
    value: bool


define("test", TestConfig)


def main():
    with use({"test": {"value": "not-a-boolean"}}):
        pass


if __name__ == "__main__":
    main()

import os
import subprocess
import sys
from dataclasses import dataclass
from unittest import mock

import pytest

from gifnoc.proxy import MissingConfigurationError


def test_overlay(org, registry, configs):
    with registry.use(configs / "mila.yaml"):
        assert org.name == "mila"
        with registry.overlay({"org": {"name": "sekret"}}):
            assert org.name == "sekret"
        assert org.name == "mila"


def test_empty_config(registry, configs):
    with registry.use(configs / "empty.yaml"):
        pass


def test_config_plus_empty(org, registry, configs):
    with registry.use(configs / "mila.yaml", configs / "empty.yaml"):
        assert org.name == "mila"
        with registry.overlay({"org": {"name": "sekret"}}):
            assert org.name == "sekret"
        assert org.name == "mila"


@mock.patch.dict(os.environ, {"ORG_NAME": "boop"})
def test_envvar(org, registry, configs):
    env = {"org": {"name": "${env:ORG_NAME}"}}
    with registry.use(configs / "mila.yaml", env):
        assert org.name == "boop"


def test_envvar_not_set(org, registry, configs):
    env = {"org": {"name": "${env:ORG_NAME}"}}
    with registry.use(configs / "mila.yaml", env):
        assert org.name == "mila"


@mock.patch.dict(os.environ, {"NONPROFIT": "1"})
def test_envvar_boolean_true(org, registry, configs):
    env = {"org": {"name": "${env:ORG_NAME}", "nonprofit": "${env:NONPROFIT}"}}
    with registry.use(configs / "mila.yaml", env):
        assert org.name == "mila"
        assert org.nonprofit is True


@dataclass
class Point:
    x: int
    y: int


@dataclass
class Person:
    name: str
    age: int


def test_define_lazy(registry):
    pt = registry.define(field="pt", model=Point, lazy=True)
    perso = registry.define(field="perso", model=Person, lazy=True)

    with registry.use({"pt": {"x": 1, "y": 2}}):
        assert pt.x == 1
        assert pt.y == 2
        with pytest.raises(MissingConfigurationError):
            perso.name


#############
# CLI tests #
#############


def test_config_through_cli(org, registry, configs):
    pth = str(configs / "mila.yaml")
    registry.cli(argv=["--config", pth])
    assert org.name == "mila"
    assert org.members[0].home == configs / "breuleuo"


@dataclass
class CLIArgs:
    name: str
    amount: int


def test_cli_with_type(registry):
    args = registry.cli(type=CLIArgs, argv=["--name", "bob", "--amount", "42"])
    assert args.name == "bob"
    assert args.amount == 42


def test_cli_with_mapping(org, registry, configs):
    pth = str(configs / "mila.yaml")
    registry.cli(
        mapping={"org.name": "-n"},
        argv=["--config", pth, "-n", "blabb"],
    )
    assert org.name == "blabb"


def test_cli_does_an_overlay(org, registry, configs):
    registry.set_sources(configs / "mila.yaml")
    registry.cli(
        mapping={"org.name": "-n"},
        argv=["-n", "blabb"],
    )
    assert org.name == "blabb"
    assert org.nonprofit is True
    assert len(org.members) == 1


@pytest.mark.skipif(sys.version_info < (3, 13), reason="Python 3.13+ required")
def test_exception_hook(configs, file_regression):
    result = subprocess.run(
        [sys.executable, str(configs / "bad_config_script.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    header = "============================= Configuration error =============================="
    stderr = result.stderr
    assert header in stderr
    below = stderr.split(header, 1)[1]
    below = below.replace(str(configs), "REDACTED")
    file_regression.check(below)

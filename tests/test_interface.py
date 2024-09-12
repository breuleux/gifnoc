import os
import sys
from functools import partial
from unittest import mock

import pytest

import gifnoc
from gifnoc.arg import Command
from gifnoc.parse import EnvironMap
from gifnoc.utils import ConfigurationError


@pytest.fixture
def cli(registry):
    return partial(gifnoc.cli, registry=registry, write_back_environ=False)


def test_overlay(org, registry, configs):
    with registry.use(configs / "mila.yaml"):
        assert org.name == "mila"
        with gifnoc.overlay({"org": {"name": "sekret"}}):
            assert org.name == "sekret"
        assert org.name == "mila"


def test_empty_config(registry, configs):
    with registry.use(configs / "empty.yaml"):
        pass


def test_config_plus_empty(org, registry, configs):
    with registry.use(configs / "mila.yaml", configs / "empty.yaml"):
        assert org.name == "mila"
        with gifnoc.overlay({"org": {"name": "sekret"}}):
            assert org.name == "sekret"
        assert org.name == "mila"


@mock.patch.dict(os.environ, {"ORG_NAME": "boop"})
def test_envvar(org, registry, configs):
    env = EnvironMap(environ=os.environ, map={"ORG_NAME": "org.name".split(".")})
    with registry.use(configs / "mila.yaml", env):
        assert org.name == "boop"


@mock.patch.dict(os.environ, {"NONPROFIT": "1"})
def test_envvar_boolean_true(org, registry, configs):
    env = EnvironMap(environ=os.environ, map={"NONPROFIT": "org.nonprofit".split(".")})
    with registry.use(configs / "mila.yaml", env):
        assert org.nonprofit is True


@mock.patch.dict(os.environ, {"NONPROFIT": "0"})
def test_envvar_boolean_false(org, registry, configs):
    env = EnvironMap(environ=os.environ, map={"NONPROFIT": "org.nonprofit".split(".")})
    with registry.use(configs / "mila.yaml", env):
        assert org.nonprofit is False


def test_envvar_not_set(org, registry, configs):
    env = EnvironMap(environ=os.environ, map={"ORG_NAME": "org.name".split(".")})
    with registry.use(configs / "mila.yaml", env):
        assert org.name == "mila"


#############
# CLI tests #
#############


def test_cli(org, cli, configs):
    pth = str(configs / "mila.yaml")
    with cli(argv=["--config", pth]):
        assert org.name == "mila"
        assert org.members[0].home == configs / "breuleuo"


def test_cli_incomplete_conf(org, cli):
    src = [{"org": {"name": "x"}}]
    with pytest.raises(SystemExit):
        with cli(sources=src, argv=[]):
            pass
    with pytest.raises(ConfigurationError):
        with cli(sources=src, argv=[], exit_on_error=False):
            pass


def test_cli_gifnoc_file(org, cli, configs):
    pth = str(configs / "mila.yaml")
    with mock.patch.dict(os.environ, {"GIFNOC_FILE": pth}):
        with cli(argv=[]):
            assert org.name == "mila"


def test_cli_custom_envvar(org, cli, configs):
    pth = str(configs / "mila.yaml")
    with mock.patch.dict(os.environ, {"XOXOX": pth}):
        with cli(envvar="XOXOX", argv=[]):
            assert org.name == "mila"


def test_cli_simple_options(org, cli, configs):
    with cli(
        sources=[configs / "mila.yaml"],
        options="org",
        argv=["--name", "alim", "--no-nonprofit"],
    ):
        assert org.name == "alim"
        assert org.nonprofit is False


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Python 3.10 changed format")
def test_cli_options_help(org, cli, configs, capsys, file_regression):
    with pytest.raises(SystemExit):
        with cli(
            sources=[configs / "mila.yaml"],
            options="org",
            argv=["-h"],
        ):
            pass
    captured = capsys.readouterr()
    file_regression.check(captured.out)


def test_cli_custom_options(org, cli, configs):
    with cli(
        sources=[configs / "mila.yaml"],
        options=Command(
            mount="org",
            options={
                ".name": "-n",
            },
        ),
        argv=["-n", "zoup"],
    ):
        assert org.name == "zoup"

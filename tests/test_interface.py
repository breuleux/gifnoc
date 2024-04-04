import os
from unittest import mock

import pytest

import gifnoc
from gifnoc.arg import Command
from gifnoc.parse import EnvironMap


def test_use(org, registry, configs):
    with registry.use(configs / "mila.yaml"):
        assert org.name == "mila"


def test_overlay(org, registry, configs):
    with registry.use(configs / "mila.yaml"):
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


def test_cli(org, registry, configs):
    pth = str(configs / "mila.yaml")
    with gifnoc.cli(registry=registry, argv=["--config", pth]):
        assert org.name == "mila"


def test_cli_gifnoc_file(org, registry, configs):
    pth = str(configs / "mila.yaml")
    with mock.patch.dict(os.environ, {"GIFNOC_FILE": pth}):
        with gifnoc.cli(registry=registry, argv=[]):
            assert org.name == "mila"


def test_cli_custom_envvar(org, registry, configs):
    pth = str(configs / "mila.yaml")
    with mock.patch.dict(os.environ, {"XOXOX": pth}):
        with gifnoc.cli(envvar="XOXOX", registry=registry, argv=[]):
            assert org.name == "mila"


def test_cli_simple_options(org, registry, configs):
    with gifnoc.cli(
        sources=[configs / "mila.yaml"],
        options="org",
        registry=registry,
        argv=["--name", "alim", "--no-nonprofit"],
    ):
        assert org.name == "alim"
        assert org.nonprofit is False


def test_cli_options_help(org, registry, configs, capsys, file_regression):
    with pytest.raises(SystemExit):
        with gifnoc.cli(
            sources=[configs / "mila.yaml"],
            options="org",
            registry=registry,
            argv=["-h"],
        ):
            pass
    captured = capsys.readouterr()
    file_regression.check(captured.out)


def test_cli_custom_options(org, registry, configs):
    with gifnoc.cli(
        sources=[configs / "mila.yaml"],
        options=Command(
            mount="org",
            options={
                ".name": "-n",
            },
        ),
        registry=registry,
        argv=["-n", "zoup"],
    ):
        assert org.name == "zoup"

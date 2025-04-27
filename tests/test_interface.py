import os
from dataclasses import dataclass
from unittest import mock


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

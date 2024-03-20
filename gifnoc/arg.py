import argparse
from dataclasses import dataclass, field, fields, is_dataclass, replace
from pathlib import Path
from typing import Union

from ovld import ovld

from gifnoc.registry import global_registry
from gifnoc.utils import ConfigurationError, type_at_path


@dataclass
class Option:
    option: str
    aliases: list[str] = field(default_factory=list)
    action: object = None
    metavar: str = None
    help: str = None
    required: bool = None
    type: object = None


@dataclass
class Command:
    mount: str = None
    auto: bool = False
    help: str = None
    commands: dict[str, Union[str, "Command"]] = field(default_factory=dict)
    options: dict[str, Union[str, Option]] = field(default_factory=dict)


@ovld
def compile_option(model: bool, path: str, option: Option):
    if option.action is None:
        option.action = argparse.BooleanOptionalAction
    return option


@ovld
def compile_option(model: object, path: str, option: Option):  # noqa: F811
    if option.type is None:
        option.type = model
    if option.metavar is None:
        option.metavar = option.option.strip("-").upper()
    return option


@ovld
def compile_option(model: object, path: str, option: str):  # noqa: F811
    return compile_option[model, str, Option](model, path, Option(option=option))


def abspath(path, mount):
    if mount.startswith("."):
        return f"{path}{mount}"
    else:
        return mount


def auto(model, mount, prefix=""):
    options = {}
    for fld in fields(model):
        mounted = f"{mount}.{fld.name}"
        if issubclass(fld.type, (str, int, float, bool, Path)):
            options[mounted] = Option(f"--{prefix}{fld.name}")
        elif is_dataclass(fld.type):
            options.update(auto(fld.type, mounted, prefix=f"{fld.name}."))
        else:
            pass
    return options


def compile_command(global_model, path, command):
    if isinstance(command, str):
        command = Command(mount=command, auto=True)
    mount = abspath(path, command.mount)

    if mount:
        model, doc = type_at_path(global_model, mount.split("."), allow_union=False)
    else:
        model = global_model
        doc = ""

    def _compile_option(p, v):
        ap = abspath(mount, p)
        typ, doc = type_at_path(global_model, ap.split("."), allow_union=False)
        opt = compile_option[typ, str, type(v)](typ, mount, v)
        if opt.help is None:
            opt.help = doc
        return ap, opt

    options = dict(command.options)
    if command.auto:
        options.update(auto(model, mount))
    options = dict(_compile_option(p, v) for p, v in options.items())

    commands = {
        cmd: compile_command(global_model, mount, v)
        for cmd, v in command.commands.items()
    }
    return replace(
        command,
        help=command.help or doc,
        mount=mount,
        auto=False,
        commands=commands,
        options=options,
    )


@ovld
def add_arguments_to_parser(parser: argparse.ArgumentParser, command: Command):
    for dest, option in command.options.items():
        option.dest = f"&{dest}"
        add_arguments_to_parser(parser, option)
    if command.commands:
        global_model = global_registry.model()
        dest = f"&{command.mount}.command"
        path = dest[1:].split(".")
        try:
            holder_type, doc = type_at_path(model=global_model, path=path)
            if not issubclass(holder_type, str):
                raise ConfigurationError(
                    errors=[
                        {
                            "loc": path,
                            "err": f"The property `{dest[1:]}` is defined as {holder_type} in the code, but it should be str instead",
                        }
                    ],
                    is_definition_problem=True,
                )
        except TypeError:
            raise ConfigurationError(
                errors=[
                    {
                        "loc": path,
                        "err": f"The property `{dest[1:]}` is not defined. It must be defined (with type str) to hold the name of the command.",
                    }
                ],
                is_definition_problem=True,
            )
        subparsers = parser.add_subparsers(required=True, dest=dest, help=doc)
        for command_name, subcmd in command.commands.items():
            subparser = subparsers.add_parser(command_name, help=subcmd.help)
            add_arguments_to_parser(subparser, subcmd)


@ovld
def add_arguments_to_parser(parser: argparse.ArgumentParser, option: Option):  # noqa: F811
    parser.add_argument(
        option.option,
        *option.aliases,
        action=option.action,
        metavar=option.metavar,
        help=option.help,
        required=option.required,
        type=option.type,
        dest=option.dest,
    )


@ovld
def add_arguments_to_parser(parser: argparse.ArgumentParser, options: dict):  # noqa: F811
    add_arguments_to_parser(parser, Command(mount="", options=options))


@ovld
def add_arguments_to_parser(parser: argparse.ArgumentParser, mount: str):  # noqa: F811
    add_arguments_to_parser(parser, Command(mount=mount, auto=True))

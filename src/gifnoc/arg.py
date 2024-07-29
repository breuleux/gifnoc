import argparse
from dataclasses import dataclass, field, fields, is_dataclass, replace
from types import GenericAlias
from typing import Optional, Union

from ovld import ovld

from .registry import Registry
from .utils import ConfigurationError, convertible_from_string, type_at_path


@dataclass
class Option:
    option: Optional[str] = None
    aliases: list[str] = field(default_factory=list)
    action: Optional[object] = None
    metavar: Optional[str] = None
    help: Optional[str] = None
    required: Optional[bool] = None
    type: Optional[object] = None


@dataclass
class Command:
    mount: str = None
    auto: bool = False
    help: str = None
    command_field: str = "command"
    commands: dict[str, Union[str, "Command"]] = field(default_factory=dict)
    options: dict[str, Union[str, Option]] = field(default_factory=dict)


@ovld
def compile_option(model: type[bool], path: str, option: Option):
    if option.action is None:
        option.action = argparse.BooleanOptionalAction
    return option


@ovld
def compile_option(  # noqa: F811
    model: Union[type[int], type[float]], path: str, option: Option
):
    if option.type is None:
        option.type = model
    return option


@ovld
def compile_option(model: type[list], path: str, option: Option):  # noqa: F811
    assert isinstance(model, GenericAlias)
    option = compile_option(model.__args__[0], path, option)
    option.action = "append"
    return option


@ovld
def compile_option(model: type[object], path: str, option: Option):  # noqa: F811
    if isinstance(model, GenericAlias):
        return None
    elif option.type is None:
        option.type = str
    return option


@ovld
def compile_option(model: type[object], path: str, option: str):  # noqa: F811
    return compile_option(model, path, Option(option=option))


def abspath(path, mount):
    if mount.startswith("."):
        return f"{path}{mount}"
    else:
        return mount


def auto(model, mount, prefix=""):
    options = {}
    for fld in fields(model):
        name = fld.name.replace("_", "-")
        mounted = f"{mount}.{fld.name}"
        if is_dataclass(fld.type) and not convertible_from_string(fld.type):
            options.update(auto(fld.type, mounted, prefix=f"{prefix}{name}."))
        else:
            options[mounted] = Option(f"--{prefix}{name}")
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
        opt = compile_option(typ, mount, v)
        if not opt:
            return None
        if opt.help is None:
            opt.help = doc
        return ap, opt

    def _merge(opts1, opts2):
        results = {abspath(mount, p): v for p, v in opts1.items()}
        opts2 = {abspath(mount, p): v for p, v in opts2.items()}
        for k, v in opts2.items():
            if k in results:
                v = replace(
                    results[k],
                    **{key: value for key, value in vars(v).items() if value is not None},
                )
            results[k] = v
        return results

    options = {}
    if command.auto:
        options.update(auto(model, mount))
    options = _merge(options, command.options)
    options = dict(compiled for p, v in options.items() if (compiled := _compile_option(p, v)))

    commands = {
        cmd: compile_command(global_model, mount, v) for cmd, v in command.commands.items()
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
def add_arguments_to_parser(parser: argparse.ArgumentParser, command: Command, registry: Registry):
    for dest, option in command.options.items():
        option.dest = f"&{dest}"
        add_arguments_to_parser(parser, option, registry)
    if command.commands:
        global_model = registry.model()
        dest = f"&{command.mount}.{command.command_field}"
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
        subparsers = parser.add_subparsers(
            required=True, dest=dest, help=doc, metavar=command.command_field.upper()
        )
        for command_name, subcmd in command.commands.items():
            subparser = subparsers.add_parser(command_name, help=subcmd.help)
            add_arguments_to_parser(subparser, subcmd, registry)


@ovld
def add_arguments_to_parser(  # noqa: F811
    parser: argparse.ArgumentParser, option: Option, registry: Registry
):
    if option.metavar is None and option.option is not None:
        option.metavar = option.option.strip("-").upper()
    kwargs = {
        "action": option.action,
        "metavar": option.metavar,
        "help": option.help,
        "required": option.required,
        "type": option.type,
        "dest": option.dest,
    }
    if option.action == argparse.BooleanOptionalAction:
        # Python 3.14 will raise an exception on these, apparently.
        kwargs.pop("metavar")
        kwargs.pop("type")
    parser.add_argument(
        *([option.option] if option.option else []),
        *option.aliases,
        **kwargs,
    )


@ovld
def add_arguments_to_parser(  # noqa: F811
    parser: argparse.ArgumentParser, options: dict, registry: Registry
):
    add_arguments_to_parser(parser, Command(mount="", options=options), registry)


@ovld
def add_arguments_to_parser(  # noqa: F811
    parser: argparse.ArgumentParser, mount: str, registry: Registry
):
    add_arguments_to_parser(parser, Command(mount=mount, auto=True), registry)

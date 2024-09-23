import argparse
from typing import Any

import yaml

from .util import Config


def handle_config(args: argparse.Namespace) -> None:
    config = Config()
    if args.config_action == "view":
        if args.key:
            value = config.get(args.key)
            print(f"{args.key}: {value}")
        else:
            print(yaml.dump(config.data))
    elif args.config_action == "set":
        config.set(args.key, args.value)


def add_parser(subparsers: Any, parent: argparse.ArgumentParser) -> None:
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "config", parents=[parent], description="Configure Jobq"
    )

    config_subparsers = parser.add_subparsers(
        dest="config_action", help="Config actions"
    )

    view_parser = config_subparsers.add_parser(
        "view", help="View current configuration"
    )
    view_parser.add_argument("--key", help="Specific config key to view")

    set_parser = config_subparsers.add_parser("set", help="Set a configuration value")
    set_parser.add_argument("key", help="Configuration key to set")
    set_parser.add_argument("value", help="Value to set for the key")

    parser.set_defaults(func=handle_config, config_action="view")

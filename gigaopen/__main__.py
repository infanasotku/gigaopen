"""Command boundary: parse arguments, call the bridge, render JSON."""

import argparse
import json
import sys
from pathlib import Path

import yaml

from gigaopen.bridge import Bridge, BridgeError


def main():
    parser = argparse.ArgumentParser(
        description="Explicit OpenSpec to Superpowers bridge prototype"
    )
    parser.add_argument(
        "--lock",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "upstream.lock.yaml",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser(
        "prepare", help="Validate a change and prepare private handoff state"
    )
    for option in ("repo", "change", "upstream", "state-root"):
        prepare.add_argument(f"--{option}", required=True)
    resolve = commands.add_parser(
        "resolve", help="Resolve an execution skill or one of its resources"
    )
    resolve.add_argument("--session", required=True)
    resolve.add_argument("--skill", required=True)
    resolve.add_argument("--resource", default="SKILL.md")
    brief = commands.add_parser(
        "brief", help="Extract a task brief using the pinned upstream helper"
    )
    brief.add_argument("--session", required=True)
    brief.add_argument("--task", required=True, type=int)
    args = parser.parse_args()
    try:
        bridge = Bridge(args.lock)
        if args.command == "prepare":
            result = bridge.prepare(
                args.repo, args.change, args.upstream, args.state_root
            )
        elif args.command == "resolve":
            result = bridge.resolve(args.session, args.skill, args.resource)
        else:
            result = bridge.brief(args.session, args.task)
    except (
        BridgeError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        yaml.YAMLError,
    ) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

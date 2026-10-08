#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from lib import doctor as doctor_mod
from lib import engine, index, manifest
from lib.util import UserError, abspath

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aicj", description="ai-coding-java global installer")
    sub = parser.add_subparsers(dest="command", required=True)

    install = sub.add_parser("install", help="install components into the global home")
    _common(install)
    _scope(install)
    install.add_argument("--packs", default="auto", help="auto or comma separated pack names")
    install.add_argument("--adapters", default="", help="comma separated adapter names")
    install.add_argument("--codex", action="store_true", help="also link skills for codex")
    install.add_argument("--codex-hooks", action="store_true", help="also merge hooks into codex hooks.json")
    install.add_argument("--strict", action="store_true", help="run blocking hooks in block mode")
    install.add_argument(
        "--enable-hook",
        action="append",
        default=[],
        metavar="NAME",
        dest="enable_hook",
        help="also register an optional hook by name (repeatable; default registers none)",
    )
    install.add_argument("--link", action="store_true", help="symlink instead of copy")
    install.add_argument("--on-conflict", choices=("skip", "backup"), default="skip")
    install.add_argument("--dry-run", action="store_true")

    uninstall = sub.add_parser("uninstall", help="remove what the manifest records as ours")
    _common(uninstall)
    _scope(uninstall)
    uninstall.add_argument("--dry-run", action="store_true")

    status = sub.add_parser("status", help="read-only install report")
    _common(status)

    check = sub.add_parser("doctor", help="read-only health report")
    _common(check)
    return parser


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--home", help="override home directory")
    parser.add_argument("--source", help="component root (default: this repository)")


def _scope(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--global", dest="global_install", action="store_true", help="global install (default)")
    group.add_argument("--project", help="project archive directory")


def _home(args: argparse.Namespace) -> Path:
    return abspath(args.home) if args.home else Path.home()


def _source(args: argparse.Namespace, default: Path | None) -> Path | None:
    if args.source:
        return abspath(args.source)
    return default


def _print_report(title: str, report: engine.Report, dry_run: bool) -> None:
    suffix = " (dry-run, nothing written)" if dry_run else ""
    print(f"=== {title}{suffix} ===")
    for verb, path, note in report.lines:
        line = f"{verb:<16} {path}"
        if note:
            line += f"  {note}"
        print(line)
    for note in report.notes:
        print(f"note             {note}")
    for warning in report.warnings:
        print(f"warning          {warning}")
    counts = Counter(verb for verb, _path, _note in report.lines)
    summary = " ".join(f"{name}={counts[name]}" for name in sorted(counts)) or "nothing"
    print(f"summary          {summary}")


def cmd_install(args: argparse.Namespace) -> int:
    home = _home(args)
    source = _source(args, REPO_ROOT)
    if source is None or not source.is_dir():
        raise UserError(f"source root not found: {source}")
    if args.project:
        print(f"project layer {args.project}: no project entries in this build")
        return 0

    packs = index.resolve_packs(args.packs, Path.cwd(), index.available_names(source, "pack"), not args.project)
    adapters = [part.strip() for part in args.adapters.split(",") if part.strip()]
    options = manifest.Options(
        packs=packs,
        adapters=adapters,
        codex=args.codex,
        codex_hooks=args.codex_hooks,
        strict=args.strict,
        link=args.link,
        on_conflict=args.on_conflict,
        enable_hooks=list(args.enable_hook),
    )
    report, _result = engine.run_install(home, source, options, args.dry_run)
    _print_report("install", report, args.dry_run)
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    if args.project:
        print(f"project layer {args.project}: no project entries in this build")
        return 0
    report = engine.run_uninstall(_home(args), args.dry_run)
    _print_report("uninstall", report, args.dry_run)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    report = engine.run_status(_home(args), _source(args, None))
    _print_report("status", report, False)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    home = _home(args)
    checks, code = doctor_mod.run_doctor(home, _source(args, None))
    print("=== doctor ===")
    for status, name, detail in checks:
        print(f"{status:<8} {name}  {detail}")
    counts = Counter(status for status, _name, _detail in checks)
    print("summary          " + " ".join(f"{name}={counts[name]}" for name in sorted(counts)))
    return code


COMMANDS = {
    "install": cmd_install,
    "uninstall": cmd_uninstall,
    "status": cmd_status,
    "doctor": cmd_doctor,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except UserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

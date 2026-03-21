import argparse
import sys

from hippo.cli.utils import _count_connections, _print_errors, _print_warnings
from hippo.backup import create_backup, list_backups, restore_backup, validate_backup
from hippo.graph_builder import sync as graph_sync


def cmd_backup(args: argparse.Namespace) -> None:
    result = graph_sync()
    if result.validation_errors:
        print(f"Sync failed: {len(result.validation_errors)} errors\n")
        _print_errors(result.validation_errors)
        print("\nBackup not created")
        sys.exit(1)

    connection_count = _count_connections(result.topics)
    warning_count = len(result.clean_issues)
    if warning_count > 0:
        summary = f"Sync complete: {len(result.topics)} topics, {connection_count} connections, {warning_count} warnings"
        if not args.warnings:
            summary += " (see --warnings)"
        print(summary)
        if args.warnings:
            print()
            _print_warnings(result.clean_issues)
    else:
        print(
            f"Sync complete: {len(result.topics)} topics, {connection_count} connections"
        )

    backup_path = create_backup(result)
    print(f"\nBackup created: {backup_path.name}")


def cmd_restore(args: argparse.Namespace) -> None:
    timestamp = args.version
    if not timestamp:
        backups = list_backups()
        if not backups:
            print("ERROR: No backups found", file=sys.stderr)
            sys.exit(1)
        timestamp = backups[0]

    errors = validate_backup(timestamp)
    if errors:
        print(f"Restore failed: {len(errors)} errors\n")
        _print_errors(errors)
        sys.exit(1)

    success = restore_backup(timestamp)
    if not success:
        print("Restore failed: unknown error")
        sys.exit(1)

    print("Restore complete")
    result = graph_sync()
    if result.validation_errors:
        print(f"\nSync failed: {len(result.validation_errors)} errors\n")
        _print_errors(result.validation_errors)
        sys.exit(1)

    connection_count = _count_connections(result.topics)
    print(f"Sync complete: {len(result.topics)} topics, {connection_count} connections")

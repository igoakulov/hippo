import argparse
import sys

from hippo.cli.utils import _count_connections, _print_errors, _print_warnings
from hippo.graph_builder import sync as graph_sync


def cmd_sync(args: argparse.Namespace) -> None:
    result = graph_sync()
    connection_count = _count_connections(result.topics)

    if result.validation_errors:
        print(f"Sync failed: {len(result.validation_errors)} errors\n")
        _print_errors(result.validation_errors)
        sys.exit(1)

    warning_count = len(result.clean_issues)
    summary = (
        f"Sync complete: {len(result.topics)} topics, {connection_count} connections"
    )
    if warning_count > 0:
        summary += f", {warning_count} warnings"
        if not args.warnings:
            summary += " (see --warnings)"
    print(summary)

    if args.warnings and result.clean_issues:
        print()
        _print_warnings(result.clean_issues)

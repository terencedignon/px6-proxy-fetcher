"""Command line interface for px6-proxy-fetcher."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from pathlib import Path

from .core import (
    Px6ProxyFetcherError,
    fetch_proxies,
    format_env_exports,
    write_proxies,
)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the px6-proxy-fetcher CLI.

    Args:
        argv: Command-line arguments. Defaults to sys.argv if None.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(args)
    load_dotenv_if_available()

    api_key = args.api_key or os.getenv("PX6_API_KEY")
    if not api_key:
        msg = (
            "Provide --api-key or set the PX6_API_KEY "
            "environment variable."
        )
        parser.error(msg)

    try:
        proxies = fetch_proxies(api_key, timeout=args.timeout)
    except Px6ProxyFetcherError as exc:
        logger = logging.getLogger(__name__)
        logger.error("Failed to fetch proxies: %s", exc)
        return 1

    destination = Path(args.output)
    write_proxies(proxies, destination)

    if args.print_env and proxies:
        print()
        print(format_env_exports(proxies))

    if not proxies:
        logger = logging.getLogger(__name__)
        logger.warning("No active proxies returned by the API.")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI.

    Returns:
        Configured ArgumentParser instance with all CLI options.
    """
    parser = argparse.ArgumentParser(
        prog="px6-proxy-fetcher",
        description=(
            "Fetch active proxies from PROXY6.net and write them to a "
            "file."
        ),
    )
    parser.add_argument(
        "--api-key",
        help="PX6 API key (defaults to PX6_API_KEY env var)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="proxies.txt",
        help=(
            "Destination file for the proxy list "
            "(default: proxies.txt)"
        ),
    )
    parser.add_argument(
        "--print-env",
        action="store_true",
        help=(
            "Print shell export commands for PROXY_LIST after "
            "writing the file."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help=(
            "HTTP timeout for API requests in seconds (default: 30)"
        ),
    )
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress info logs."
    )
    verbosity.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging for troubleshooting.",
    )
    return parser


def configure_logging(args: argparse.Namespace) -> None:
    """Configure logging based on command-line arguments.

    Args:
        args: Parsed command-line arguments with verbose/quiet flags.
    """
    if args.verbose:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def load_dotenv_if_available() -> None:
    """Load environment variables from .env file if python-dotenv is installed.

    Checks for .env file in the current working directory and loads it
    if found. Silently does nothing if python-dotenv is not installed.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    project_root = Path.cwd()
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)


if __name__ == "__main__":
    sys.exit(main())

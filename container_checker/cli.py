import argparse
from pathlib import Path

from settings import get_oict_creds, get_ste_creds

from .logging_utils import logger
from .orchestrator import normalize_container_numbers, run_checks
from .output import output_csv, output_json, output_table
from .tideworks import TideworksChecker
from .trapac import TrapacChecker


def main():
    parser = argparse.ArgumentParser(description="Check container status across multiple terminals")
    parser.add_argument("container_numbers", nargs="+", help="Container numbers to check")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--output", choices=["csv", "json", "table"], default="json", help="Output format")
    parser.add_argument("--output-file", help="Output file path")
    parser.add_argument("--parallel", action="store_true", help="Run terminal checks in parallel")
    parser.add_argument(
        "--debug-env",
        action="store_true",
        help="Print safe credential diagnostics (paths and value lengths only), then continue",
    )
    args = parser.parse_args()

    if args.debug_env:
        from settings import format_env_debug_report

        print(format_env_debug_report())

    container_numbers = normalize_container_numbers(args.container_numbers)
    logger.info(f"Checking status for containers: {container_numbers}")

    ste_creds = get_ste_creds()
    oict_creds = get_oict_creds()

    checkers = [
        TrapacChecker(),
        TideworksChecker(
            ste_creds.username,
            ste_creds.password,
            "Shippers Transport Express",
            "https://sto.tideworks.com",
            headless=args.headless,
        ),
        TideworksChecker(
            oict_creds.username,
            oict_creds.password,
            "Oakland International Container Terminal",
            "https://b58.tideworks.com/",
            headless=args.headless,
        ),
    ]

    container_results = run_checks(checkers, container_numbers, parallel=args.parallel)
    output_file = args.output_file
    if args.output == "json" and not output_file:
        output_file = str(Path.cwd() / "results.json")

    if args.output == "csv":
        output_csv(container_results, output_file)
    elif args.output == "json":
        output_json(container_results, output_file)
    else:
        output_table(container_results, output_file)


if __name__ == "__main__":
    main()

import csv
import json
import sys

from tabulate import tabulate


def output_csv(container_results, output_file=None):
    headers = [
        "Container Number",
        "Terminal",
        "Available",
        "Line Operator",
        "Dimensions",
        "Location",
        "Customs Hold",
        "Line Hold",
        "CBPA Hold",
        "Terminal Hold",
    ]

    rows = [
        {
            "Container Number": result.container_number,
            "Terminal": result.terminal,
            "Available": result.available or "",
            "Line Operator": result.line_operator or "",
            "Dimensions": result.dimensions or "",
            "Location": result.location or "",
            "Customs Hold": result.customs_hold or "",
            "Line Hold": result.line_hold or "",
            "CBPA Hold": result.cbpa_hold or "",
            "Terminal Hold": result.terminal_hold or "",
        }
        for results in container_results.values()
        for result in results
    ]

    if output_file:
        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Results exported to {output_file}")
        return

    writer = csv.DictWriter(sys.stdout, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)


def output_json(container_results, output_file=None):
    data = {
        container: [
            {
                "terminal": result.terminal,
                "available": result.available,
                "line_operator": result.line_operator,
                "dimensions": result.dimensions,
                "location": result.location,
                "customs_hold": result.customs_hold,
                "line_hold": result.line_hold,
                "cbpa_hold": result.cbpa_hold,
                "terminal_hold": result.terminal_hold,
            }
            for result in results
        ]
        for container, results in container_results.items()
    }

    if output_file:
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Results exported to {output_file}")
        return

    print(json.dumps(data, indent=2))


def output_table(container_results, output_file=None):
    headers = ["Container", "Terminal", "Available", "Line Operator", "Dimensions", "Location", "Customs", "Line", "CBPA", "Terminal Hold"]

    table_data = [
        [
            result.container_number,
            result.terminal,
            result.available or "",
            result.line_operator or "",
            result.dimensions or "",
            result.location or "",
            result.customs_hold or "",
            result.line_hold or "",
            result.cbpa_hold or "",
            result.terminal_hold or "",
        ]
        for _, results in sorted(container_results.items())
        for result in results
    ]

    table = tabulate(table_data, headers=headers, tablefmt="grid")
    if output_file:
        with open(output_file, "w") as f:
            f.write(table)
        print(f"Results exported to {output_file}")
        return

    print("\n" + table)

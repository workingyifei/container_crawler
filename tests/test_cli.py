from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from container_checker import cli


def test_cli_defaults_to_json_file_output():
    with (
        patch("sys.argv", ["cli.py", "MSCU1234567"]),
        patch.object(cli, "get_ste_creds", return_value=SimpleNamespace(username="u", password="p")),
        patch.object(cli, "get_oict_creds", return_value=SimpleNamespace(username="u", password="p")),
        patch.object(cli, "TrapacChecker", return_value=object()),
        patch.object(cli, "TideworksChecker", return_value=object()),
        patch.object(cli, "run_checks", return_value={"MSCU1234567": []}),
        patch.object(cli, "output_json") as output_json_mock,
    ):
        cli.main()

    output_json_mock.assert_called_once()
    _, output_file = output_json_mock.call_args.args
    assert output_file == str(Path.cwd() / "results.json")

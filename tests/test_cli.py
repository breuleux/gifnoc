import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from gifnoc.__main__ import main

here = Path(__file__).parent


def _run_on_org(*args, config=True):
    prefix = ["gifnoc", "-m", "tests.defn_org"]
    if config:
        prefix = [*prefix, "-c", here / "configs/mila.yaml"]
    args = [*prefix, *args]
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


@pytest.mark.skipif(sys.version_info < (3, 13), reason="Python 3.10, then 3.13, changed format")
def test_help(capsys, file_regression):
    with pytest.raises(SystemExit):
        main(["-h"])

    out, err = capsys.readouterr()
    file_regression.check(f"{out}\n===\n{err}")


def test_dump_json(data_regression):
    results = _run_on_org("dump")
    data = json.loads(results.stdout)
    m = data["org"]["members"][0]
    assert m["home"].startswith("/")
    del m["home"]
    data_regression.check(data)


def test_dump_yaml(data_regression):
    results = _run_on_org("dump", "--format", "yaml")
    data = yaml.safe_load(results.stdout)
    m = data["org"]["members"][0]
    assert m["home"].startswith("/")
    del m["home"]
    data_regression.check(data)


def test_check_true():
    results = _run_on_org("check", "org.nonprofit")
    assert results.stdout == b"true\n"
    assert results.returncode == 0


def test_check_false():
    results = _run_on_org("check", "org.members.0.end")
    assert results.stdout == b"false\n"
    assert results.returncode != 0


def test_check_nonexistent():
    results = _run_on_org("check", "org.badfield")
    assert results.stdout == b"nonexistent\n"
    assert results.returncode != 0


def test_schema(data_regression):
    results = _run_on_org("schema", config=False)
    data = json.loads(results.stdout)
    data_regression.check(data)

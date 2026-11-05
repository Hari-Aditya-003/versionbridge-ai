import os
from pathlib import Path
import subprocess

import pytest

COMPILE = ['javac', '-J-Xmx192m', '-d', '/build/classes', 'Main.java']
RUN = ['java', '-Xmx96m', '-cp', '/build/classes', 'Main']
CASES = [(['admin'], 'true'), (['user'], 'false'), (['Admin'], 'false'), ([''], 'false')]


@pytest.fixture(scope="session")
def executable():
    Path("/build/classes").mkdir(exist_ok=True)
    environment = dict(os.environ, GOCACHE="/build/go-cache", GOMAXPROCS="1", GOMEMLIMIT="192MiB")
    result = subprocess.run(COMPILE, capture_output=True, text=True, timeout=60, env=environment)
    assert result.returncode == 0, result.stdout + result.stderr
    return RUN


@pytest.mark.parametrize(("arguments", "expected"), CASES)
def test_compiled_contract(executable, arguments, expected):
    result = subprocess.run(executable + arguments, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected

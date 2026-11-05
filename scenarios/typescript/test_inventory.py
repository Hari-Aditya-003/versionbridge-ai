import json
import subprocess

import pytest


def test_typescript_contract():
    result = subprocess.run(
        ["node", "/opt/versionbridge/typescript/lib/tsc.js",
         "--strict", "--noEmit", "--target", "es2022", "inventory.ts"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(("items", "sku", "expected"), [
    ([{"sku": "A", "available": 7}, {"sku": "B", "available": 9}], "B", 9),
    ([{"sku": "A", "available": 0}], "A", 0),
    ([], "missing", 0),
])
def test_inventory_lookup(items, sku, expected):
    script = """
        import assert from 'node:assert/strict';
        import {availableFor} from './inventory.ts';
        const [items, sku, expected] = JSON.parse(process.argv[1]);
        assert.equal(availableFor(items, sku), expected);
    """
    result = subprocess.run(
        ["node", "--experimental-strip-types", "--input-type=module",
         "-e", script, json.dumps([items, sku, expected])],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr

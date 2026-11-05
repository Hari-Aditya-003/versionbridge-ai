import json
import subprocess

import pytest


@pytest.mark.parametrize(("subtotal", "discount", "cap", "expected"), [
    (1000, 300, 200, 800),
    (1000, 0, 200, 1000),
    (100, 500, 200, 0),
    (1000, 300, 0, 1000),
])
def test_discount_total(subtotal, discount, cap, expected):
    script = """
        import assert from 'node:assert/strict';
        import {discountTotal} from './discount.mjs';
        const [subtotal, discount, cap, expected] = JSON.parse(process.argv[1]);
        assert.equal(discountTotal(subtotal, discount, cap), expected);
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script, json.dumps([subtotal, discount, cap, expected])],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr

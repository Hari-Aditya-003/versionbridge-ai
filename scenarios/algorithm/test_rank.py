from random import Random

import pytest

from rank import count_at_most


@pytest.mark.parametrize(("values", "threshold"), [
    ([], 0), ([2, 2, 2], 2), ([-4, -2, 0, 2], -5), ([-4, -2, 0, 2], 3),
])
def test_rank_boundaries(values, threshold):
    assert count_at_most(values, threshold) == sum(value <= threshold for value in values)


def test_rank_reference():
    rng = Random(1729)
    for _ in range(200):
        values = sorted(rng.choices(range(-25, 26), k=rng.randrange(100)))
        threshold = rng.randrange(-30, 31)
        assert count_at_most(values, threshold) == sum(value <= threshold for value in values)

from bisect import bisect_left, bisect_right


def count_at_most(ordered, threshold):
    """Count values less than or equal to threshold in a sorted sequence."""
    return bisect_left(ordered, threshold)

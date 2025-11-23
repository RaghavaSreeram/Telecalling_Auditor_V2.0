from typing import Tuple


def compute_new_script_stats(usage_count: int, total_score_sum: float, new_score: float) -> Tuple[int, float, float]:
    """
    Given current usage_count and total_score_sum, and a new_score value,
    return (new_usage_count, new_total_score_sum, new_avg_score).
    """
    if usage_count is None:
        usage_count = 0
    if total_score_sum is None:
        total_score_sum = 0.0

    new_usage = usage_count + 1
    new_sum = float(total_score_sum) + float(new_score or 0.0)
    new_avg = (new_sum / new_usage) if new_usage > 0 else 0.0
    return new_usage, new_sum, new_avg

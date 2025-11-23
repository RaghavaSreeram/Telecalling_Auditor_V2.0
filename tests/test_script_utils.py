from backend.script_utils import compute_new_script_stats


def test_compute_new_script_stats_initial():
    new_usage, new_sum, new_avg = compute_new_script_stats(0, 0.0, 80)
    assert new_usage == 1
    assert new_sum == 80.0
    assert new_avg == 80.0


def test_compute_new_script_stats_accumulate():
    # existing 2 usages totaling 150 (avg 75). add new 90 -> new avg = (150+90)/3 = 80
    new_usage, new_sum, new_avg = compute_new_script_stats(2, 150.0, 90)
    assert new_usage == 3
    assert new_sum == 240.0
    assert abs(new_avg - 80.0) < 1e-6

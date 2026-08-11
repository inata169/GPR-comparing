from scripts.run_gamma_acceptance_matrix import summarize_runs


def _run(gamma_type, common, numba_only, pymedphys_only, disagreements):
    return {
        "gamma_type": gamma_type,
        "report": {
            "comparison": {
                "mask": {
                    "common_finite": common,
                    "numba_only": numba_only,
                    "pymedphys_only": pymedphys_only,
                },
                "pass_fail_confusion_on_common_mask": {
                    "total_disagreements": disagreements,
                },
            }
        },
    }


def test_summarize_runs_keeps_global_and_local_observations_separate():
    summary = summarize_runs(
        [
            _run("global", 100, 0, 0, 1),
            _run("local", 50, 1, 0, 2),
        ]
    )

    assert summary["run_count"] == 2
    assert summary["exact_finite_mask_run_count"] == 1
    assert summary["all_runs_have_exact_finite_masks"] is False
    assert summary["common_points"] == 150
    assert summary["pass_fail_disagreements"] == 3
    assert summary["pass_fail_disagreement_percent"] == 2.0
    assert summary["by_gamma_type"]["global"] == {
        "runs": 1,
        "common_points": 100,
        "pass_fail_disagreements": 1,
        "pass_fail_disagreement_percent": 1.0,
    }
    assert summary["by_gamma_type"]["local"] == {
        "runs": 1,
        "common_points": 50,
        "pass_fail_disagreements": 2,
        "pass_fail_disagreement_percent": 4.0,
    }

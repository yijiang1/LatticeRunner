import unittest

from tools.run_balance import expand_rigs, markdown_report, recommendations, summarize


def result(rig, percent, completed=False, seed=1):
    return {
        "specimen": "graphene",
        "mode": "session",
        "profile": "expert",
        "rig": rig,
        "seed": seed,
        "ending": "complete" if completed else "exhausted",
        "completed": completed,
        "percent": percent,
        "dose": 90,
        "damaged": 2,
        "falls": 3,
        "picks": 2,
    }


class BalanceRunnerTests(unittest.TestCase):
    def test_summary_groups_and_interpolates_percentiles(self):
        rows = [result("stock", 20, seed=1), result("stock", 80, True, seed=2)]
        summary = summarize(rows)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["medianPercent"], 50)
        self.assertAlmostEqual(summary[0]["completionRate"], 0.5)
        self.assertEqual(summary[0]["p10Percent"], 26)
        self.assertEqual(summary[0]["p90Percent"], 74)

    def test_marginal_expands_to_every_upgrade(self):
        rigs = expand_rigs("stock,marginal")
        self.assertTrue(rigs.startswith("stock,"))
        self.assertIn("volt3", rigs)
        self.assertIn("shift3", rigs)
        self.assertEqual(len(rigs.split(",")), 11)

    def test_recommendations_flag_dominant_upgrade(self):
        summary = summarize(
            [result("stock", 30), result("volt3", 60, True)]
        )
        notes = recommendations(summary)
        self.assertTrue(any("VOLT" in note and "dominance" in note for note in notes))

    def test_markdown_contains_matrix(self):
        summary = summarize([result("stock", 50)])
        report = markdown_report(
            {"balanceVersion": 2, "fixedDt": 1 / 60, "runsPerCell": 1},
            summary,
        )
        self.assertIn("# Lattice Runner balance report", report)
        self.assertIn("| graphene | session | expert | stock |", report)


if __name__ == "__main__":
    unittest.main()

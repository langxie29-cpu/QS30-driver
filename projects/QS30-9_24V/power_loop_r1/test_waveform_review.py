import unittest
from waveform_review import stats,sustained_entry

class TestIndependentMath(unittest.TestCase):
    def test_nonuniform_samples_use_time_integral(self):
        # Exact y=t on irregular grid: a sample arithmetic mean would be wrong.
        r=stats([0,.01,.02,1],[0,.01,.02,1],.1,.9)
        self.assertAlmostEqual(r['mean'],.5)
        self.assertAlmostEqual(r['pp'],.8)
    def test_transient_reentry_is_not_early_success(self):
        self.assertEqual(sustained_entry([0,1,2,3],[0,170,180,170],164.9,175.1),3)
        self.assertIsNone(sustained_entry([0,1,2],[0,170,180],164.9,175.1))
    def test_reject_window_outside_completed_trace(self):
        with self.assertRaises(ValueError): stats([0,1],[0,170],0,2)

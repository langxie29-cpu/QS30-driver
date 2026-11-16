"""Expected failure: replay current adversarial tests against archived first draft."""
import unittest
import test_safety
from safety_model_r1_failed_snapshot import Safety,Inputs
test_safety.Safety=Safety
test_safety.Inputs=Inputs
if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromModule(test_safety)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)

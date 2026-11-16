"""Agent C independent contract counterexamples, not hardware proof."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'verification'))
from safety_model import Safety, Inputs
def run():
 s=Safety();x=Inputs();s.tick(x);x.request=x.manual=True;s.tick(x)
 x.drv_ok=True;s.tick(x);x.precharge_ok=x.demagnetized=True;s.tick(x)
 x.hv_stable=True;s.tick(x);s.tick(x);assert s.state=='RUN'
 return s,x
class Independent(unittest.TestCase):
 def test_manual_reset_revokes_running_token(self):
  s,x=run();x.reset=True
  self.assertFalse(any(s.tick(x).values()),'REQ01 reset must revoke token even without fault')
 def test_held_reset_blocks_new_arm(self):
  s=Safety();x=Inputs(reset=True);s.tick(x);x.request=x.manual=True
  self.assertFalse(any(s.tick(x).values()),'reset asserted must inhibit new arm')
 def test_fault_dominates_reset(self):
  s,x=run();x.request=x.manual=False;x.reset=True;x.faults=('overvoltage',)
  self.assertFalse(any(s.tick(x).values()));self.assertTrue(s.latched)
 def test_invalid_residual_blocks_reset(self):
  s,x=run();x.faults=('overvoltage',);s.tick(x);x.faults=()
  x.request=x.manual=False;s.tick(x);x.reset=True;x.residual_valid=False
  self.assertFalse(any(s.tick(x).values()));self.assertTrue(s.latched)
if __name__=='__main__': unittest.main(verbosity=2)

"""Independent negative invariants + finite fault coverage; no silicon emulation."""
import itertools
import unittest
from safety_model import Safety, Inputs, FAULTS

def running():
    s=Safety(); x=Inputs(); s.tick(x)
    x.request=x.manual=True; s.tick(x)
    x.drv_ok=True; s.tick(x)
    x.precharge_ok=x.demagnetized=True; s.tick(x)
    x.hv_stable=True; s.tick(x); s.tick(x)
    assert s.state=='RUN'
    return s,x

class SafetyTests(unittest.TestCase):
    def test_drv_loss_latches_and_cuts_branch(self):
        s,x=running();x.drv_ok=False
        self.assertFalse(any(s.tick(x).values()));self.assertTrue(s.latched)
    def test_invalid_residual_blocks_reset(self):
        s,x=running();x.faults=('overvoltage',);s.tick(x);x.faults=()
        x.request=x.manual=False;x.residual_valid=False;s.tick(x);x.reset=True;s.tick(x)
        self.assertTrue(s.latched)
    def test_branch_stuck_blocks_reset(self):
        s,x=running();x.faults=('overvoltage',);s.tick(x);x.faults=()
        x.request=x.manual=False;x.branch_off_confirmed=False;s.tick(x);x.reset=True;s.tick(x)
        self.assertTrue(s.latched)
    def test_invalid_residual_blocks_start(self):
        s=Safety();x=Inputs();x.residual_valid=False;s.tick(x);x.request=x.manual=True
        self.assertFalse(any(s.tick(x).values()))
    def test_gate_off_does_not_stop_passive_path(self):
        # Independent Boolean topology assertion, not a circuit simulation.
        def passive_path(input_present, efuse_stuck, command_on):
            return input_present and (efuse_stuck or command_on)
        self.assertTrue(passive_path(True,True,False))
    def test_mos_short_unaffected_by_gate_command(self):
        def short_path(input_present, efuse_stuck, command_on, mos_short):
            return input_present and (efuse_stuck or command_on) and mos_short
        self.assertTrue(short_path(True,True,False,True))
        self.assertFalse(short_path(True,False,False,True))
    def test_normal_sequence(self):
        s,x=running(); self.assertTrue(all(s.outputs(x).values()))
    def test_initial_stuck_high(self):
        s=Safety();x=Inputs(request=True,manual=True)
        for _ in range(30):self.assertFalse(any(s.tick(x).values()))
    def test_request_without_manual(self):
        s=Safety();x=Inputs();s.tick(x);x.request=True
        self.assertFalse(any(s.tick(x).values()))
    def test_manual_without_request(self):
        s=Safety();x=Inputs();s.tick(x);x.manual=True
        self.assertFalse(any(s.tick(x).values()))
    def test_watchdog_stuck_high(self):
        s,x=running();x.heartbeat=False
        self.assertFalse(any(s.tick(x).values()));self.assertTrue(s.latched)
    def test_reboot(self):
        s,x=running();x.selftest=False
        self.assertFalse(any(s.tick(x).values()))
    def test_stale_reset_cannot_release(self):
        s,x=running();x.reset=True;x.faults=('overvoltage',);s.tick(x)
        x.faults=();x.request=x.manual=False
        self.assertTrue(s.tick(x)==dict.fromkeys(('drv','input_switch','gate','display'),False))
        self.assertTrue(s.latched)
    def test_reset_returns_off(self):
        s,x=running();x.faults=('overvoltage',);s.tick(x)
        x.faults=();x.request=x.manual=False;x.reset=False;s.tick(x)
        x.reset=True;self.assertFalse(any(s.tick(x).values()));self.assertFalse(s.latched)
        x.request=True;self.assertFalse(any(s.tick(x).values()))
    def test_residual_blocks_start(self):
        s=Safety();x=Inputs(residual_safe=False);s.tick(x);x.request=x.manual=True
        self.assertFalse(any(s.tick(x).values()))
    def test_timeout(self):
        s=Safety();x=Inputs();s.tick(x);x.request=x.manual=True
        for _ in range(12):s.tick(x)
        self.assertTrue(s.latched)
    def test_demagnetization_required(self):
        s=Safety();x=Inputs();s.tick(x);x.request=x.manual=True;s.tick(x)
        x.drv_ok=True;s.tick(x);x.precharge_ok=True;s.tick(x)
        self.assertEqual(s.state,'PRECHARGE');self.assertFalse(s.outputs(x)['gate'])
    def test_usb_only(self):
        s=Safety();x=Inputs(power=False,request=True,manual=True)
        self.assertFalse(any(s.tick(x).values()))
    def test_stop_consumes_request(self):
        s,x=running();x.request=False;s.tick(x);x.request=True
        self.assertFalse(any(s.tick(x).values()))

def single_test(fault):
    def t(self):
        s,x=running();x.faults=(fault,);self.assertFalse(any(s.tick(x).values()))
        x.faults=();self.assertFalse(any(s.tick(x).values()));self.assertTrue(s.latched)
    return t
for fault in FAULTS:setattr(SafetyTests,'test_single_'+fault,single_test(fault))

def pair_test(a,b):
    def t(self):
        s,x=running();x.faults=(a,b);self.assertFalse(any(s.tick(x).values()))
        x.faults=();self.assertFalse(any(s.tick(x).values()))
    return t
# Exhaust all pairs of declared detected predicates: 171 pairs, not physical coverage.
for a,b in itertools.combinations(FAULTS,2):setattr(SafetyTests,'test_pair_'+a+'_'+b,pair_test(a,b))

def truth_test(bits):
    def t(self):
        x=Inputs(power=bits[0],thermal=bits[1],interlock=bits[2],heartbeat=bits[3],selftest=bits[4],drv_ok=True,hv_stable=True)
        s=Safety();s.state='RUN';o=s.outputs(x)
        self.assertEqual(all(o.values()),all(bits))
    return t
for bits in itertools.product((False,True),repeat=5):setattr(SafetyTests,'test_truth_'+''.join(str(int(b)) for b in bits),truth_test(bits))

def reset_test(field):
    def t(self):
        s,x=running();x.faults=('overvoltage',);s.tick(x);x.faults=()
        x.request=x.manual=False;x.reset=False;s.tick(x)
        setattr(x,field,False);x.reset=True;s.tick(x);self.assertTrue(s.latched)
    return t
for field in ('power','thermal','interlock','residual_safe'):setattr(SafetyTests,'test_reset_requires_'+field,reset_test(field))

if __name__=='__main__':unittest.main(verbosity=2)

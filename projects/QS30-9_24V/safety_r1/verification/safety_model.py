"""Executable REQUIREMENTS model. No claim of implementation/hardware safety."""
from dataclasses import dataclass

FAULTS = ('cycle_overcurrent','branch_overcurrent','overvoltage','mos_hot','inductor_hot',
          'sensor_open','sensor_short','feedback_open','watchdog','aux_uv','drv_uv','logic_uv',
          'input_loss','input_reverse','interlock_open','bleeder_open','switch_stuck','mos_short','backfeed')

@dataclass
class Inputs:
    power: bool = True
    thermal: bool = True
    interlock: bool = True
    residual_safe: bool = True
    residual_valid: bool = True
    branch_off_confirmed: bool = True
    selftest: bool = True
    heartbeat: bool = True
    request: bool = False
    manual: bool = False
    reset: bool = False
    drv_ok: bool = False
    precharge_ok: bool = False
    demagnetized: bool = False
    hv_stable: bool = False
    faults: tuple = ()

class Safety:
    def __init__(self):
        self.state = 'OFF'
        self.request_armed = False
        self.manual_armed = False
        self.reset_armed = False
        self.latched = False
        self.age = 0

    def tick(self, x):
        # Inputs represent independently qualified hardware predicates, not MCU flags.
        reqedge = self.request_armed and x.request
        manedge = self.manual_armed and x.manual
        resetedge = self.reset_armed and x.reset
        self.request_armed = not x.request
        self.manual_armed = not x.manual
        self.reset_armed = not x.reset
        healthy = x.power and x.thermal and x.interlock
        # Fault detection coverage is assumed only for detected faults. Physical faults
        # such as a shorted MOSFET/eFuse and open bleeder need independent diagnostics.
        bad = bool(x.faults) or not healthy
        if self.state in ('PRECHARGE','BOOST','VERIFY','RUN') and not x.drv_ok:
            bad = True
        if self.state != 'OFF' and (not x.heartbeat or not x.selftest):
            bad = True
        if bad:
            self.latched = True
            self.state = 'FAULT'
        if self.latched:
            if resetedge and not bad and healthy and x.residual_safe and x.residual_valid and x.branch_off_confirmed and not x.request and not x.manual:
                self.latched = False
                self.state = 'OFF'
                self.age = 0
            return self.outputs(x)
        if x.reset:
            self.state = 'OFF'
            self.age = 0
            self.request_armed = False
            self.manual_armed = False
            return self.outputs(x)
        if self.state != 'OFF' and not x.request:
            self.state = 'OFF'
            self.age = 0
        elif self.state == 'OFF':
            if reqedge and manedge and healthy and x.residual_safe and x.residual_valid and x.branch_off_confirmed and x.selftest and x.heartbeat:
                self.state = 'DRV'
                self.age = 0
        elif self.state == 'DRV' and x.drv_ok:
            self.state = 'PRECHARGE'; self.age = 0
        elif self.state == 'PRECHARGE' and x.precharge_ok and x.demagnetized:
            self.state = 'BOOST'; self.age = 0
        elif self.state == 'BOOST' and x.hv_stable:
            self.state = 'VERIFY'; self.age = 0
        elif self.state == 'VERIFY' and x.hv_stable:
            self.state = 'RUN'; self.age = 0
        self.age += 1
        if self.state in ('DRV','PRECHARGE','BOOST','VERIFY') and self.age > 10:
            self.latched = True; self.state = 'FAULT'
        return self.outputs(x)

    def outputs(self, x):
        permit = not self.latched and x.power and x.thermal and x.interlock and x.heartbeat and x.selftest and not x.faults
        return {'drv': permit and self.state in ('DRV','PRECHARGE','BOOST','VERIFY','RUN'),
                'input_switch': permit and self.state in ('PRECHARGE','BOOST','VERIFY','RUN'),
                'gate': permit and x.drv_ok and self.state in ('BOOST','VERIFY','RUN'),
                'display': permit and x.drv_ok and x.hv_stable and self.state == 'RUN'}

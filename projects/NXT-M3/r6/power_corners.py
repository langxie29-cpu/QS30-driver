"""Separate DCM triangular ramps from steady CCM; eta is lumped conversion loss."""
import csv
import math
from pathlib import Path

path = Path(__file__).with_name("POWER_CORNERS.csv")
volts = 170
nominal_lf = 150e-6 * 100e3  # H·Hz = Ω
assert math.isclose(nominal_lf,15)

scenarios = (
    ('ideal_nominal',1,1,1), ('loss_nominal',0.75,1,1),
    ('low_Lf',0.70,0.9,0.9), ('high_Lf',0.70,1.1,1.1),
)
with path.open("w", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    writer.writerow("vin_V bus_W scenario eta L_uH f_kHz hv_input_A module_input_A Ipk_A Imin_A duty_on duty_diode duty_idle boundary_W mode".split())
    for vin in (10.8,12,13.2,21.6,24,26.4):
        for power in (1.15,1.53,2,2.5):
            for case,eta,l_scale,f_scale in scenarios:
                lf = nominal_lf*l_scale*f_scale
                avg = power/eta/vin
                boundary = eta*vin**2*(volts-vin)/(2*volts*lf)
                duty_on = min(1-vin/volts, math.sqrt(2*power*lf*(volts-vin)/(eta*volts))/vin)
                if power <= boundary:
                    mode = 'DCM'
                    peak = duty_on*vin/lf
                    minimum = 0
                    duty_diode = lf*peak/(volts-vin)
                    duty_idle = 1-duty_on-duty_diode
                else:
                    mode = 'CCM'
                    ripple = vin*duty_on/lf
                    peak = avg+ripple/2
                    minimum = avg-ripple/2
                    duty_diode = 1-duty_on
                    duty_idle = 0
                tolerance = [avg, (power/eta+0.45)/vin, peak, minimum, duty_on, duty_diode, duty_idle, boundary]
                writer.writerow([vin,power,case,eta,round(150*l_scale,3),round(100*f_scale,3),
                                 *map(lambda x: round(x,6),tolerance),mode])

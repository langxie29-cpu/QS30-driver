"""Deterministic, solver-free R8 qualification screens and quantity models."""
import csv
from decimal import Decimal
from itertools import product
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
R7 = HERE.parent / "r7"
EVIDENCE = HERE / "evidence"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def table(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        out = csv.writer(handle, lineterminator="\n")
        out.writerow(fields.split(","))
        out.writerows(rows)


def base_current(voh, vbe, series, pulldown, tolerance):
    return max(0.0, (voh-vbe)/(series*(1+tolerance))-vbe/(pulldown*(1-tolerance)))


def driver_screen(setup, destination):
    cfg = read_json(setup)
    tol = cfg["tolerance_fraction"]
    rows = []
    for v, b, r, d, ic in product(cfg["logic_high_sensitivity_V"], cfg["vbe_sensitivity_V"],
                                  cfg["base_series_ohm"], cfg["pulldown_ohm"], cfg["collector_test_mA"]):
        ib = 1000*base_current(v, b, r, d, tol)
        target = ic/cfg["forced_beta_screen"]
        rows.append((v, b, r, d, ic, f"{ib:.6f}", f"{target:.6f}",
                     "SCREEN_MET" if ib >= target else "SCREEN_MISSED"))
    table(destination / "base_current.csv",
          "logic_voh_V,Vbe_assumed_V,series_nominal_ohm,pulldown_nominal_ohm,Ic_mA,Ib_lower_screen_mA,"
          "Ib_target_mA,current_screen", rows)
    rows = []
    for d, logic, collector in product(cfg["pulldown_ohm"], cfg["logic_output_leak_uA"],
                                       cfg["estimated_collector_base_leak_uA"]):
        vb = d*(1+tol)*(logic+collector)*1e-6
        rows.append((d, logic, collector, f"{vb:.6f}",
                     "SCREEN_MET" if vb <= cfg["off_base_voltage_screen_V"] else "SCREEN_MISSED"))
    table(destination / "base_off_leakage.csv",
          "pulldown_nominal_ohm,logic_leak_bound_uA,collector_base_leak_assumption_uA,base_V_upper_screen,status", rows)
    hv = cfg["fault_hv_V"]
    anode = cfg["anode_limit_nominal_ohm"]*(1-cfg["anode_tolerance_fraction"])
    measures = dict(
        nominal_ideal_10k_22k_Ib_mA=(3.3-.9)/10000*1000-.9/22000*1000,
        tolerant_10k_22k_Ib_mA=base_current(3.3,.9,10000,22000,tol)*1000,
        lvc_4p7k_22k_Ib_mA=base_current(2.4,.9,4700,22000,tol)*1000,
        lvc_3k_10k_Ib_mA=base_current(2.4,1.0,3000,10000,tol)*1000,
        off_lvc_22k_15uA_plus_0p1uA_V=22000*(1+tol)*15.1e-6,
        off_lvc_10k_15uA_plus_10uA_V=10000*(1+tol)*25e-6,
        conducted_zero_vbe_total_io_upper_mA=30*3.6/(3000*(1-tol))*1000,
        conducted_zero_vbe_per_chip_upper_mA=8*3.6/(3000*(1-tol))*1000,
        tube_short_partial_conduction_W=hv**2/(4*anode),
        tube_short_partial_conduction_Vce_V=hv/2,
        tube_short_partial_conduction_Ic_mA=hv/(2*anode)*1000,
        thermal_test_board_total_85C_W=(150-85)/417,
        tube_short_saturated_limiting_W=hv**2/anode,
        tube_short_current_limit_mA=hv/anode*1000,
        scope="Sensitivity calculations and counterexamples. The 0.9/1.0 V and hot leakage bounds need validation.")
    assert measures["nominal_ideal_10k_22k_Ib_mA"] < .3
    assert measures["lvc_4p7k_22k_Ib_mA"] < .3
    assert measures["lvc_3k_10k_Ib_mA"] > .33
    assert measures["off_lvc_22k_15uA_plus_0p1uA_V"] > .30
    assert measures["tube_short_partial_conduction_W"] > .3
    if cfg["status"] == "engineering_screen":
        for key in ("lvc_4p7k_22k_Ib_mA", "lvc_3k_10k_Ib_mA",
                    "off_lvc_22k_15uA_plus_0p1uA_V", "off_lvc_10k_15uA_plus_10uA_V",
                    "conducted_zero_vbe_total_io_upper_mA", "conducted_zero_vbe_per_chip_upper_mA"):
            del measures[key]
    write_json(destination / "metrics.json", measures)


def nominal_mapping():
    tree = ET.parse(R7 / "evidence/native.xml")
    native = {}
    for net in tree.findall(".//nets/net"):
        match = re.fullmatch(r"K([123])_([0-9])", net.attrib["name"])
        if match:
            tube, digit = map(int, match.groups())
            socket_nodes = [n for n in net.findall("node") if n.attrib["ref"] == f"V{tube}"]
            assert len(socket_nodes) == 1
            native[tube, digit] = socket_nodes[0].attrib["pin"]
    assert len(native) == 30
    rows = []
    q_pads = (15, 1, 2, 3, 4, 5, 6, 7)
    for bit in range(32):
        idx, q = divmod(bit, 8)
        if bit == 30 or bit == 31:
            rows.append((bit, 31-bit, f"SR{idx+1}", "ABCDEFGH"[q], q_pads[q],
                         "", "", "", "", "", "", "", "", "FORCED_ZERO_IN_FRAME_AND_NO_CONNECTION"))
            continue
        tube, digit = divmod(bit, 10)
        bjt_idx, bjt_die = divmod(bit, 2)
        emitter, base, collector = (1, 2, 6) if bjt_die == 0 else (4, 5, 3)
        tube += 1
        pin = native[tube, digit]
        rows.append((bit, 31-bit, f"SR{idx+1}", "ABCDEFGH"[q], q_pads[q], f"Q{bjt_idx+1}",
                     bjt_die+1, emitter, base, collector, f"V{tube}", pin, f"K{tube}_{digit}",
                     "DRAFT_TO_VERIFY_WITH_OFFICIAL_PACKAGE_AND_G2_ERC"))
    assert len({r[-2] for r in rows[:-2]}) == 30
    table(HERE / "30_CHANNEL_PIN_MAPPING.csv",
          "frame_bit,transmit_index_msb_first,register,parallel_output,register_pin,dual_transistor,die,E_pin,"
          "B_pin,C_pin,R7_tube,R7_socket_pin,cathode_net,status", rows)


def supply_budget():
    profiles = {"off": (0, 0), "light": (1, .0015), "typ": (3, .00225), "max": (3, .003)}
    rows = []
    for modules, vin, eta, (profile, (lit, amps)) in product((1, 3), (4.4, 4.75, 5, 5.5),
                                                           (.65, .70, .80), profiles.items()):
        hv = modules*(170*lit*amps+.464617)
        base = .45*modules
        bias = lit*modules*(3.6/2970)*3.6/.90  # deliberately conservative, zero VBE current bound
        iin = (hv/eta+base+bias)/vin
        cap_E = modules*.5*5.5e-6*160**2
        rows.append((modules, profile, modules*lit, vin, eta, f"{hv:.6f}", f"{base:.4f}", f"{bias:.6f}",
                     f"{iin:.6f}", f"{cap_E:.6f}", f"{(cap_E/.05/eta/vin):.6f}",
                     f"{1-vin/170:.6f}", "R7_LOAD_ARITHMETIC_ONLY_G2_HOLD"))
    table(HERE/"5V_POWER_BUDGET.csv",
          "modules,load,lit,assumed_board_input_V,assumed_eta,HV_W,R7_lv_budget_W,base_drive_reserve_input_W,"
          "input_steady_A,storage_at_160V_J,storage_only_mean_50ms_A,ideal_ccm_duty,scope", rows)


def order_lcsc(entry, needed):
    data = entry["catalogue"]
    minimum, step = int(data["minBuyNumber"]), int(data["split"])
    quantity = ((max(needed, minimum)+step-1)//step)*step
    if quantity > int(data["stockNumber"]):
        return "UNKNOWN", "UNKNOWN"
    return quantity, quantity*min(Decimal(str(p["usdPrice"])) for p in data["productPriceList"] if p["ladder"] <= quantity)


def cost():
    lcsc = {r["mpn"]:r for r in read_json(EVIDENCE/"lcsc_public.json")}
    public = read_json(EVIDENCE/"public_price_tiers.json")
    bjt = public["MMDTA42-7-F"]
    ref = public["HV5622PG-G"]
    rows = []
    discrete_area = 4*5*4.4 + 15*3*1.6 + 60*1.6*.8
    for qty in (1,3,5,10):
        num_bjt = qty*45
        bjt_price = num_bjt*min(Decimal(c) for q,c in bjt["USD_unit_tiers"].items() if int(q)<=num_bjt)
        ref_qty = qty*3
        ref_price = ref_qty*min(Decimal(c) for q,c in ref["USD_unit_tiers"].items() if int(q)<=ref_qty)
        for architecture, logic, active_n, resistor_n, cap_n, auxiliary, area in (
                ("A_R7_HV5622",None,3,0,"UNKNOWN",3,100),
                ("B_HV5524",None,3,0,"UNKNOWN",0,49),
                ("C_HC595_DUAL","SN74HC595PWR",57,180,12,0,discrete_area),
                ("C_REWORK_LVC_DUAL","SN74LVC595APWR",57,180,12,0,discrete_area)):
            order_qty, active_cost, basis = "UNKNOWN", "UNKNOWN", "Full stock quote missing"
            if architecture.startswith("A"):
                active_cost, basis = ref_price, "Frozen R7 DigiKey exact HV5622PG-G, no current stock claim"
            elif logic:
                order_qty, shift_price = order_lcsc(lcsc[logic], qty*12)
                active_cost = bjt_price+shift_price if shift_price != "UNKNOWN" else "UNKNOWN"
                basis = "DigiKey US BJT + LCSC register, inventory snapshots, prices before tax/freight; no China landed quote"
            rows.append((architecture, qty, qty*3, active_n*qty, resistor_n*qty, cap_n if cap_n=="UNKNOWN" else cap_n*qty,
                         auxiliary*qty, area, order_qty, active_cost, "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", basis))
    table(HERE/"DRIVER_COST_COMPARISON.csv",
          "architecture,sets,boards,core_active_placements,bias_resistor_placements,min_local_bypass_placements,"
          "AUX12_count_current_or_goal,body_area_mm2_per_board_not_PCB,register_order_qty,ACTIVE_COMPONENT_COST,"
          "TOTAL_DRIVER_BOM,PCB_AND_ASSEMBLY_COST,FULL_SYSTEM_COST,ONE_TIME_DEVELOPMENT_COST,basis_USD",rows)


if __name__ == "__main__":
    run = EVIDENCE/"runs/offline-discrete-g0"
    driver_screen(HERE/"acceptance.json", run/"round_01/base_drive_bound")
    driver_screen(HERE/"acceptance_rework.json", run/"round_02/base_drive_rework")
    nominal_mapping()
    supply_budget()
    cost()

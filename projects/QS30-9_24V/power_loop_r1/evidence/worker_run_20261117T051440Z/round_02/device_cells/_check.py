import device_cells as dc, fixtures as fx
rec, txt = dc.run_case('dbg_final_st', fx.st_f1(100e-9, 60e-6, 27), ['stp9nk50z.lib'],
                       'wrdata out.dat v(NVSWP) i(Vsense) v(NVGP) v(NVDDP)')
print('st', rec['rc'], rec['errors'][:2], rec['data_rows'])
rows = dc.parse_wrdata(dc.RAW / 'dbg_final_st' / 'out.dat')
print(' rows', len(rows), 'VGmax %.2f' % dc.maxcol(rows, 5),
      'VDSmax %.1f' % dc.maxcol(rows, 1), 'ISmin %.3f' % dc.mincol(rows, 3),
      'VDDP %.1f' % dc.maxcol(rows, 7))
for name, deck, inc, what in [
        ('dbg_final_d', fx.d_f1('US1GD', 'us1g_vishay1999.models', 5e-9, 12e-6, 27),
         ['us1g_vishay1999.models'],
         'wrdata out.dat i(Vf) v(NVKP) v(NVAP,NVKP)'),
        ('dbg_final_boost', fx.l_pulse(5e-9, 10e-6), [],
         'wrdata out.dat i(L1) v(NVDP) v(NVOP) v(NVSW)'),
        ('dbg_final_boost_sat', fx.l_pulse(5e-9, 10e-6, True), [],
         'wrdata out.dat i(L1) v(NVDP) v(NVOP) v(NVSW)')]:
    rec, txt = dc.run_case(name, deck, inc, what)
    print(name, rec['rc'], rec['errors'][:2], rec['data_rows'])
    rows = dc.parse_wrdata(dc.RAW / name / 'out.dat')
    print('  colmax', [round(max(r[i] for r in rows), 3) for i in range(1, len(rows[0]), 2)])

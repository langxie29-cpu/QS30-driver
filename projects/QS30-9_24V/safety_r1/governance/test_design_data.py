"""Data consistency checks; NOT ERC, circuit completeness or electrical validation."""
import csv, hashlib, io, json, pathlib, unittest
BASE=pathlib.Path(__file__).resolve().parents[1]
ROOT=BASE.parents[2]
class DesignDataTests(unittest.TestCase):
    def setUp(self):
        self.pins=list(csv.DictReader(io.StringIO((BASE/'circuit/pin_connections.csv').read_text(encoding='utf-8-sig'))))
        self.bom=list(csv.DictReader(io.StringIO((BASE/'circuit/bom_candidates.csv').read_text(encoding='utf-8-sig'))))
        self.sources=json.loads((BASE/'sources/device_qualification.json').read_text(encoding='utf8'))
    def test_no_duplicate_ref_pin(self):
        keys=[(r['ref'],r['pin']) for r in self.pins]
        self.assertEqual(len(keys),len(set(keys)))
    def test_no_empty_net(self):
        self.assertTrue(all(r['net'].strip() and r['mpn'].strip() for r in self.pins))
    def test_exact_ic_mpn_in_bom(self):
        mpns={r['mpn'] for r in self.bom}
        self.assertFalse({r['mpn'] for r in self.pins if r['ref'].startswith('U') and r['mpn'].startswith(('TPS','UCC','SN74'))}-mpns)
    def test_bom_source_and_package(self):
        sources={r['mpn']:r for r in self.sources}
        for r in self.bom:
            self.assertIn(r['mpn'],sources)
            self.assertEqual(r['package'],sources[r['mpn']]['package'])
            self.assertIn('HOLD',r['lcsc_id'])
    def test_primary_source_hashes(self):
        for r in self.sources:
            self.assertEqual(hashlib.sha256((ROOT/r['source_file']).read_bytes()).hexdigest(),r['source_sha256'])
    def test_efuse_domain_and_defaults(self):
        lookup={(r['ref'],r['pin']):r['net'] for r in self.pins}
        for ref,domain in [('U100','RTN100'),('U101','RTN101')]:
            self.assertEqual(lookup[ref,'15'],domain)
            self.assertEqual(lookup[ref,'EP'],domain)
            self.assertNotEqual(lookup[ref,'14'],'3V3')
        self.assertNotEqual(lookup['U100','15'],lookup['U101','15'])
    def test_holds_cannot_be_silently_removed(self):
        h=json.loads((BASE/'governance/holds.json').read_text(encoding='utf8'))
        self.assertEqual(h['manufacturing'],'HOLD')
        self.assertEqual(h['task_status']['24V-07'],'NOT_PASSED')
        self.assertEqual(h['task_status']['24V-08'],'NOT_ENTERED')
        self.assertEqual(len(h['blockers']),10)
        self.assertTrue(all(b['severity']=='P0' for b in h['blockers']))
    def test_incomplete_netlist_explicit(self):
        scope=json.loads((BASE/'circuit/netlist_scope.json').read_text(encoding='utf8'))
        self.assertEqual(scope['status'],'PARTIAL_PIN_NETLIST_NOT_NATIVE_EDA')
        self.assertEqual(scope['rows'],len(self.pins))
        self.assertGreater(len(scope['unimplemented_blocks']),0)
    def test_all_requirement_ids_unique_and_hold(self):
        data=json.loads((BASE/'architecture/requirements.json').read_text(encoding='utf8'))
        req=data['requirements']
        self.assertEqual(len(req),len({r['id'] for r in req}))
        self.assertTrue(all(r['electrical_qualification']=='HOLD' for r in req))
if __name__=='__main__':unittest.main(verbosity=2)

import tempfile,struct,unittest
from pathlib import Path
import raw_archive
class LosslessEvidenceTests(unittest.TestCase):
 def fixture(self,p):
  h='Title: codec fixture\nFlags: real double forward nocompression\nNo. Variables: 2\nNo. Points: 3\nVariables:\n0 time time\n1 V(hv) voltage\nBinary:\n'.encode('utf-16-le')
  p.write_bytes(h+b''.join(struct.pack('<dd',*r)for r in [(0.,0.),(.1,1.),(1.,2.),(2.,3.)])+b'END')
 def test_partial_tail_and_header_counts_are_preserved_exactly(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);p=d/'partial.raw';self.fixture(p);m=raw_archive.archive(p,d/'parts',d,cap=100)
   self.assertEqual(m['declared_points'],3);self.assertEqual(m['physical_complete_records'],4);self.assertEqual(m['original_trailing_bytes'],3)
   dest=d/'restored.raw';raw_archive.verify(m,d,dest);self.assertEqual(dest.read_bytes(),p.read_bytes())
 def test_corruption_and_external_paths_are_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);p=d/'partial.raw';self.fixture(p);m=raw_archive.archive(p,d/'parts',d,cap=100)
   f=d/m['parts'][0]['path'];b=bytearray(f.read_bytes());b[0]^=1;f.write_bytes(b)
   with self.assertRaises(ValueError):raw_archive.verify(m,d)
   m['parts'][0]['path']='../outside'
   with self.assertRaises(ValueError):raw_archive.verify(m,d)
if __name__=='__main__':unittest.main()

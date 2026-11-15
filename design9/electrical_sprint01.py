"""Sprint01: surgical explicit-NC sync using a fresh native baseline.
Never repositions pads, changes active nets, relaxes rules or rewrites history.
"""
import json, re, sys, hashlib
from pathlib import Path
from reconcile9 import xml_nets
from kicad_gen import load, parts_of, gen_pcb
ROOT=Path(__file__).resolve().parents[1]

def main():
    records=[]
    for board,prefixes,w,h in [('QS30-9_DISPLAY',('MOD_L',),100,100),('QS30-9_MAIN',('MB_','MOD_C'),120,90)]:
        native,groups,refs=xml_nets(ROOT/'kicad/logs/sprint01_before'/f'{board}.xml')
        nc={key:net for key,net in native.items() if net.startswith('unconnected-')}
        assert all(len(groups[n])==1 for n in nc.values())
        path=ROOT/'kicad/projects'/board/f'{board}.kicad_pcb'
        old_bytes=path.read_bytes()
        old=old_bytes.decode('utf-8').replace('\r\n','\n')
        netids=[int(x) for x in re.findall(r'^  \(net (\d+) ',old,re.M)]
        newids={n:max(netids)+i+1 for i,n in enumerate(sorted(nc.values()))}
        changes=[];out=[];ref=None
        for line in old.splitlines():
            if line.startswith('  (footprint '): ref=None
            m=re.search(r'\(property "DesignRef" "([^"]+)"',line)
            if m:ref=m[1]
            m=re.search(r'^    \(pad "([^"]+)"',line)
            if m and (ref,m[1]) in nc:
                assert '(net ' not in line, (ref,m[1])
                net=nc[(ref,m[1])]
                line=line[:-1]+f' (net {newids[net]} "{net}"))'
                changes.append({'ref':ref,'pin':m[1],'net':net})
            out.append(line)
        assert len(changes)==len(nc)
        insert='\n'.join(f'  (net {i} "{n}")' for n,i in newids.items())
        new='\n'.join(out)+'\n'
        new=new.replace('  (net 0 "")','  (net 0 "")\n'+insert,1)
        # Undo exactly the allowed additions, requiring byte-equivalent geometry.
        undone=new.replace('\n'+insert,'',1)
        for n,i in newids.items(): undone=undone.replace(f' (net {i} "{n}")','')
        assert undone==old, 'unintended PCB edit'
        # Compare generator-produced pad assignments with the native NC inventory.
        generated,_,_=gen_pcb(board,parts_of(load(),prefixes),w,h)
        for c in changes:
            assert f'"{c["net"]}"' in generated, c
        new_bytes=new.replace('\n','\r\n').encode('utf-8') if b'\r\n' in old_bytes else new.encode('utf-8')
        path.write_bytes(new_bytes)
        records.append({'board':board,'changes':changes,'geometry_and_active_nets_unchanged':True,
                        'before_sha256':hashlib.sha256(old_bytes).hexdigest(),
                        'after_sha256':hashlib.sha256(new_bytes).hexdigest()})
    dest=ROOT/'kicad/logs/sprint01_nc_patch.json'
    assert not dest.exists()
    dest.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print([(r['board'],len(r['changes'])) for r in records])
if __name__=='__main__':main()

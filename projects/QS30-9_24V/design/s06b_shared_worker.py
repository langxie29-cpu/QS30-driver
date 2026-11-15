"""Process-isolated already-installed KiCad ngspice DLL runner; no model edits."""
from pathlib import Path
import ctypes,hashlib,json,os,sys
d=Path(sys.argv[1]).resolve();os.chdir(d)
dll=Path('C:/Program Files/KiCad/10.0/bin/ngspice.dll')
search=os.add_dll_directory(str(dll.parent));log=(d/'shared_engine.log').open('w',encoding='utf8')
Send=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_void_p)
Exit=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_int,ctypes.c_bool,ctypes.c_bool,ctypes.c_int,ctypes.c_void_p)
BG=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_bool,ctypes.c_int,ctypes.c_void_p)
@Send
def send(s,i,p):log.write((s or b'').decode(errors='replace')+'\n');log.flush();return 0
@Exit
def end(status,immediate,quitexit,i,p):log.write(f'CONTROLLED_EXIT {status} {immediate} {quitexit}\n');log.flush();return 0
@BG
def bg(running,i,p):return 0
lib=ctypes.CDLL(str(dll));lib.ngSpice_Init.argtypes=[ctypes.c_void_p]*7;lib.ngSpice_Init.restype=ctypes.c_int
lib.ngSpice_Command.argtypes=[ctypes.c_char_p];lib.ngSpice_Command.restype=ctypes.c_int
rc=lib.ngSpice_Init(send,send,end,None,None,bg,None)
commands=[]
modules=sorted(Path('C:/Program Files/KiCad/10.0/lib/ngspice').glob('*.cm'))
module_search=os.add_dll_directory(str(modules[0].parent))
short_paths=[]
for p in modules:
 buf=ctypes.create_unicode_buffer(2048);ctypes.windll.kernel32.GetShortPathNameW(str(p),buf,2048);short_paths.append(buf.value.replace('\\','/'))
for cmd in ['version',*[f'codemodel {p}' for p in short_paths],'set ngbehavior=ps','source circuit.cir']:
 os.chdir(d)
 r=lib.ngSpice_Command(cmd.encode('ascii'));commands.append({'command':cmd,'rc':r})
log.close()
(d/'shared_worker.json').write_text(json.dumps({'dll':str(dll),'dll_sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'codemodules':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in modules},'init_rc':rc,'commands':commands},indent=2),encoding='utf8')

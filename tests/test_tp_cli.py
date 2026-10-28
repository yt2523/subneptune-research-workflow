"""Invalid-input CLI checks only: every case must reject before a solver shot."""
import re, subprocess
from pathlib import Path
source=Path(__file__).resolve().parents[1];root=source/'tests/.build/cli-rejections';root.mkdir(parents=True,exist_ok=True)
base=(source/'run/mode0.cfg').read_text()
def cfg_value(text,key,value):
    pattern=r'(?m)^'+re.escape(key)+r'\s*=.*$'
    assert re.search(pattern,text),key
    return re.sub(pattern,key+'='+value,text)
cases=[('missing-profile',{},'missing.csv'),('surface-mismatch',{},'mismatch.csv'),('bad-path',{},'bad path.csv'),('jump',{'temp_jump_1':'10'},'valid.csv'),('zero-gas',{'mass_of_atm':'0'},'valid.csv'),('wrong-mode',{'input_mode':'0.5'},'valid.csv'),('duplicate-TP',{},'valid.csv')]
for name,patch,path in cases:
    out=root/name;out.mkdir(exist_ok=True);output=out/'model.txt';stale=Path(str(output)+'.tp.json');stale.write_text('{"status":"success","old":true}')
    (out/'valid.csv').write_text('P_bar,T_K\n0.1,300\n10000000000,1300\n')
    (out/'mismatch.csv').write_text('P_bar,T_K\n0.1,301\n10000000000,1300\n')
    text=base
    values={'mass_of_core':'1.60875','mass_of_mantle':'3.34125','mass_of_atm':'.05','atm_phasedgm':'"gas_fixed_mu2"','output_file':'"'+str(output)+'"',**patch}
    for key,value in values.items():text=cfg_value(text,key,value)
    text+='\ntp_profile_file="'+path+'"\n'
    if name=='duplicate-TP': text+='tp_profile_file="valid.csv"\n'
    config=out/'run.cfg';config.write_text(text)
    result=subprocess.run([str(source/'planet'),str(config)],cwd=source,capture_output=True,text=True,timeout=10)
    (out/'stdout.log').write_text(result.stdout);(out/'stderr.log').write_text(result.stderr)
    assert result.returncode!=0,(name,'invalid input accepted')
    assert '# of shots' not in result.stdout,(name,'solver reached')
    assert not stale.exists(),(name,'stale success retained')
    print('PASS CLI pre-solver stale guard:',name)
print('CLI validation:7 cases rejected before fitting; full planet runs0')

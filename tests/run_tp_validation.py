"""Bounded synthetic verification; requires existing builds. No installs or provider calls.
Windows+WSL controller. All outputs go to the explicitly supplied new directory.
"""
import argparse, copy, hashlib, json, math, re, shutil, subprocess, sys, time
from pathlib import Path
from check_tp_model import verify

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,obj): Path(path).write_text(json.dumps(obj,indent=2)+'\n')
def linux(path):
    p=str(Path(path).resolve()).replace('\\','/')
    if len(p)>2 and p[1]==':':return '/mnt/'+p[0].lower()+p[2:]
    return p

def run(args):
    source=Path(args.source_root).resolve();baseline=Path(args.baseline_root).resolve();out=Path(args.output_root).resolve()
    contract_path=source/'tests/fixtures/tp_run_contract.json';contract=json.loads(contract_path.read_text())
    assert contract['budget']['max_total_planet_invocations']==20
    out.mkdir(parents=True,exist_ok=False)
    frozen={'numeric_contract_sha256':sha(contract_path),'baseline_source_commit':contract['baseline_source_commit'],'created_unix':time.time(),'cases':[],'full_planet_invocations':0}
    for label,root,binary in [('current',source,Path(args.current_binary).resolve()),('baseline',baseline,Path(args.baseline_binary).resolve())]:
        files=[*sorted((root/'src').glob('*.cpp')),*sorted((root/'src').glob('*.h')),root/'Makefile']
        files.extend(p for p in sorted((root/'tabulated').rglob('*')) if p.is_file())
        files.extend([source/'tests/run_tp_validation.py',source/'tests/check_tp_model.py',Path(args.off_probe_source).resolve(),source/'run/mode0.cfg',contract_path])
        frozen[label]={'root':str(root),'binary':str(binary),'binary_sha256':sha(binary),'files':[{'path':str(p),'sha256':sha(p)} for p in files]}
    frozen['off_current']={'path':str(Path(args.off_current_binary).resolve()),'sha256':sha(args.off_current_binary)}
    dump(out/'frozen-inputs.json',frozen);dump(out/'numeric-contract.json',contract)
    state={'status':'RUNNING','cases':[],'full_planet_invocations':0,'budget':contract['budget']};dump(out/'results.json',state)
    template=(source/'run/mode0.cfg').read_text();threshold=contract['thresholds'];mass=contract['total_mass_earth']
    off_shared=out/'OFF-shared';off_shared.mkdir();offcfg=None
    def configuration(output,fg,controls,profile=None):
        values={'input_mode':'0','mass_of_core':format(mass*(1-fg)*contract['rock_core_fraction'],'.17g'),'mass_of_mantle':format(mass*(1-fg)*(1-contract['rock_core_fraction']),'.17g'),'mass_of_hydro':'0','mass_of_atm':format(mass*fg,'.17g'),'surface_temp':'300','temp_jump_1':'0','temp_jump_2':'0','temp_jump_3':'0','P_surface':'100000','output_file':'"'+linux(output)+'"','atm_phasedgm':'"gas_fixed_mu2"' if profile else '"gas_default"','verbose':'false',**{k:format(v,'.17g') for k,v in controls.items()}}
        text=template
        for key,value in values.items():
            pattern=r'(?m)^'+re.escape(key)+r'\s*=.*$';assert re.search(pattern,text),key;text=re.sub(pattern,key+'='+value,text)
        if profile:text+='\ntp_profile_file="profile.csv"\n'
        return text
    def case(name,slope=None,fg=None,tight=False,refined=False,old=False):
        nonlocal offcfg
        if state['full_planet_invocations']>=contract['budget']['max_total_planet_invocations']:raise RuntimeError('fixed20 invocation cap')
        fg=contract['truth_gas_fraction'] if fg is None else fg
        directory=out/name;directory.mkdir(exist_ok=False);output=directory/'model.txt';profile=None
        controls=dict(contract['solver_controls']);controls.update(contract['tight_controls'] if tight else {})
        if slope is not None:
            profile=directory/'profile.csv';nodes=[.1,1e10] if not refined else [.1,1,10,100,1e3,1e4,1e5,1e6,1e8,1e10]
            profile.write_text('P_bar,T_K\n'+''.join(format(p,'.17g')+','+format(300+slope*math.log(p/.1),'.17g')+'\n' for p in nodes))
            config=directory/'run.cfg';config.write_text(configuration(output,fg,controls,profile))
        else:
            output=off_shared/'model.txt'
            if offcfg is None:offcfg=off_shared/'run.cfg';offcfg.write_text(configuration(output,fg,controls))
            config=directory/'run.cfg';config.write_bytes(offcfg.read_bytes())
            for p in [output,Path(str(output)+'.off.json')]:
                if p.exists():p.unlink()
        chosen=frozen['baseline' if old else 'current'];binary=Path(chosen['binary']) if slope is not None or old else Path(frozen['off_current']['path']);cwd=Path(chosen['root'])
        expected_sha=chosen['binary_sha256'] if slope is not None or old else frozen['off_current']['sha256'];assert sha(binary)==expected_sha,'binary changed after freeze'
        for f in chosen['files']:assert sha(f['path'])==f['sha256'],'source changed after freeze'
        identity={'case':name,'binary':{'path':str(binary),'sha256':expected_sha},'config':{'path':str(config),'sha256':sha(config)},'numeric_contract_sha256':frozen['numeric_contract_sha256'],'gas_fraction':fg,'controls':controls,'full_invocation_ordinal':state['full_planet_invocations']+1}
        if profile:identity['profile']={'path':str(profile),'sha256':sha(profile)}
        dump(directory/'before-run.json',identity);dump(directory/'source-manifest.json',{'files':chosen['files']})
        result={'name':name,'gas_fraction':fg,'status':'STARTED','ordinal':state['full_planet_invocations']+1};state['cases'].append(result);state['full_planet_invocations']+=1;dump(out/'results.json',state)
        print('START',result['ordinal'],name,flush=True);start=time.time()
        command=['wsl','--cd',linux(cwd),'--exec','timeout','--signal=TERM','--kill-after=5',str(contract['budget']['max_seconds_per_case'])+'s',linux(binary),linux(config if profile else offcfg)]
        with (directory/'stdout.log').open('w') as stdout,(directory/'stderr.log').open('w') as stderr:
            try:proc=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=135);code=proc.returncode
            except subprocess.TimeoutExpired:code=124
        result.update(exit_code=code,seconds=time.time()-start,status='FAILED');dump(out/'results.json',state)
        if code!=0:raise RuntimeError(name+' exited '+str(code))
        if not output.is_file():raise RuntimeError(name+' missing actual model output')
        if profile:
            diagnostics=Path(str(output)+'.tp.json');data=json.loads(diagnostics.read_text());runtime=copy.deepcopy(contract);runtime['requested_gas_fraction']=fg
            runtime['artifacts']={key:{'path':str(p),'sha256':sha(p)} for key,p in [('build',binary),('config',config),('profile',profile),('source_manifest',directory/'source-manifest.json'),('diagnostics',diagnostics)]}
            dump(directory/'acceptance-contract.json',runtime);accept=verify(diagnostics,directory/'acceptance-contract.json');dump(directory/'acceptance.json',accept);result['measured_gas_fraction']=accept['measured_gas_fraction']
            radius=data['total_radius_cm'];actual_mass=data['total_mass_g']
        else:
            data=json.loads(Path(str(output)+'.off.json').read_text());assert data['ode_status']==0 and data['status']=='success';radius=data['radius_cm'];actual_mass=data['mass_g']
            shutil.copy2(output,directory/'model.txt');shutil.copy2(Path(str(output)+'.off.json'),directory/'model.txt.off.json')
        expected_mass=mass*contract['earth_mass_g'];assert abs(actual_mass-expected_mass)/expected_mass<=threshold['total_mass_relative_error_max']
        result.update(status='PASS',radius_cm=radius,total_mass_g=actual_mass,model_sha256=sha(output));dump(out/'results.json',state);print('PASS',name,'R_cm',format(radius,'.17g'),flush=True);return result
    try:
        off1=case('OFF-baseline',old=True);off2=case('OFF-current');offrel=abs(off1['radius_cm']-off2['radius_cm'])/off1['radius_cm'];state['off_radius_relative_difference']=offrel
        assert offrel<=threshold['off_default_radius_relative_max'],'OFF radius regression'
        assert (out/'OFF-baseline/model.txt').read_bytes()==(out/'OFF-current/model.txt').read_bytes(),'OFF legacy output byte regression'
        A=case('A-truth',30);B=case('B-truth',40);Bt=case('B-tight',40,tight=True);Ar=case('A-collinear-refined',30,refined=True)
        dt=abs(Bt['radius_cm']-B['radius_cm']);dr=abs(Ar['radius_cm']-A['radius_cm']);signal=abs(B['radius_cm']-A['radius_cm'])
        state['thermal_signal_cm']=signal;state['tight_change_cm']=dt;state['refinement_change_cm']=dr
        assert dt/B['radius_cm']<=threshold['radius_tight_or_refine_relative_max'] and dr/A['radius_cm']<=threshold['radius_tight_or_refine_relative_max'],'numeric change bound'
        assert signal>0 and signal>=threshold['minimum_signal_to_numerical_change']*max(dt,dr),'thermal signal unresolved'
        lo,hi=contract['inverse_bracket'];target=B['radius_cm'];L=case('A-recovery-low',30,lo);H=case('A-recovery-high',30,hi);fL=L['radius_cm']-target;fH=H['radius_cm']-target
        assert fL*fH<=0,'fixed recovery bracket does not straddle target; no inferred composition'
        best=min([L,H],key=lambda r:abs(r['radius_cm']-target));stop=None
        for iteration in range(contract['budget']['max_recovery_iterations']):
            mid=(lo+hi)/2;M=case('A-recovery-'+str(iteration+1).zfill(2),30,mid);fM=M['radius_cm']-target
            if abs(fM)<abs(best['radius_cm']-target):best=M
            if abs(fM)/target<=threshold['recovery_radius_relative_stop']:lo=hi=mid;stop='radius';break
            if fL*fM<=0:hi=mid;fH=fM
            else:lo=mid;fL=fM
            if hi-lo<=threshold['recovery_fraction_bracket_width_stop']:stop='bracket_width';break
        assert stop,'inverse iteration cap reached without frozen stopping condition'
        state.update(status='PASS',recovery={'target_case':'B-truth','inference_curve':'A','true_fraction':contract['truth_gas_fraction'],'fraction_bracket':[lo,hi],'best_evaluated_fraction':best['gas_fraction'],'best_case':best['name'],'radius_relative_error':abs(best['radius_cm']-target)/target,'stop':stop})
    except Exception as error:state['status']='FAILED';state['error']=str(error);print('FAILED',str(error),flush=True)
    dump(out/'results.json',state);return 0 if state['status']=='PASS' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',required=True);p.add_argument('--baseline-root',required=True);p.add_argument('--current-binary',required=True);p.add_argument('--baseline-binary',required=True);p.add_argument('--off-current-binary',required=True);p.add_argument('--off-probe-source',required=True);p.add_argument('--output-root',required=True);sys.exit(run(p.parse_args()))

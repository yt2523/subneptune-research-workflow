"""Separate post-failure reciprocal engineering recovery; no solver edits or APIs.
Requires an active authenticated first-run cache and existing Windows+WSL builds.
"""
import argparse, copy, hashlib, json, math, re, shutil, subprocess, sys, time
from pathlib import Path
import scipy, scipy.optimize._zeros_py as zeros_py, scipy.optimize._zeros as zeros_binary
from check_tp_model import verify
from tp_recovery_search import recover

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def linux(path):
 p=str(Path(path).resolve()).replace('\\','/')
 return '/mnt/'+p[0].lower()+p[2:] if len(p)>2 and p[1]==':' else p

def config_values(path):
 result={}
 for line in Path(path).read_text().splitlines():
  line=line.split('#',1)[0].strip()
  if '=' in line:
   key,value=line.split('=',1)
   if key.strip() in result:raise ValueError('duplicate cached config option')
   result[key.strip()]=value.strip()
 return result

def authenticate_cached_file(cache, relative, index):
 path=(cache/relative).resolve()
 if not path.is_relative_to(cache.resolve()):raise ValueError('cache artifact escapes root')
 expected=index['sha256'].get('data/'+Path(relative).as_posix())
 if not expected or not path.is_file() or sha(path)!=expected:raise ValueError('original archive artifact hash mismatch: '+relative)
 return sha(path)

def screen(case_dir,diag,contract):
 baseM=diag['gas_base_mass']/contract['base_acceptance']['earth_mass_g'];baseP=diag['gas_base_pressure']/1e10;candidates=[]
 for line in (case_dir/'model.txt').read_text().splitlines():
  a=line.split()
  try:
   if len(a)<7 or not a[0].isdigit():continue
   m,p,t,rho=float(a[3]),float(a[2]),float(a[5]),float(a[4]);phase=' '.join(a[6:])
  except ValueError:continue
  if phase=='Ideal Gas':continue
  if abs(m-baseM)<=2e-7*baseM and abs(p-baseP)<=2e-7*baseP and abs(t-diag['gas_base_temperature'])<=2e-7*diag['gas_base_temperature']:
   candidates.append((abs(p-baseP),rho,phase))
 if not candidates:raise ValueError('missing identifiable rounded solid-side base row')
 _,solid,phase=min(candidates);gas=diag['gas_rows'][0]['density_g_cm3'];margin=contract['branch_screen']['relative_margin']
 if not math.isfinite(solid) or solid<=0:raise ValueError('invalid solid-side density')
 result={'gas_density':gas,'rounded_solid_density':solid,'solid_phase':phase,'ratio':gas/solid,'relative_margin':margin,'pass':gas<solid*(1-margin),'meaning':'branch screen only, not physical validity/stability'}
 if not result['pass']:raise ValueError('gas/solid density branch screen failed or ambiguous')
 return result

def run(args):
 repo=Path(args.source_root).resolve();cache=Path(args.cache_root).resolve();cp=Path(args.contract).resolve();out=Path(args.output_root).resolve();contract=json.loads(cp.read_text())
 if any(c.isspace() for c in str(out)):raise ValueError('output path whitespace is unsupported by legacy cfg parsing')
 if out==cache or out.is_relative_to(cache) or cache.is_relative_to(out):raise ValueError('new output/cache directories overlap')
 if not args.preflight_only and contract['status']!='FROZEN_BEFORE_ANY_NEW_FIT':raise ValueError('contract not frozen')
 out.mkdir(parents=True,exist_ok=False)
 state={'status':'PREFLIGHT','old_contract_status':'FAILED','prior_full_fits':8,'new_full_fits':0,'cumulative_full_fits':8,'cases':[],'new_provider_calls':0,'selection_disclosure':contract['selection_disclosure']};dump(out/'results.json',state)
 try:
  trusted=contract['trusted_original_archive']
  if not re.fullmatch('[0-9a-f]{40}',trusted['commit']):raise ValueError('invalid trusted archive commit')
  original_index_bytes=subprocess.check_output(['git','-C',str(repo),'show',trusted['commit']+':'+trusted['index_path']])
  if hashlib.sha256(original_index_bytes).hexdigest()!=trusted['index_sha256']:raise ValueError('trusted archive index differs')
  original_index=json.loads(original_index_bytes)
  for name in ['results.json','numeric-contract.json','frozen-inputs.json']:authenticate_cached_file(cache,name,original_index)
  old=json.loads((cache/'results.json').read_text());base=json.loads((cache/'numeric-contract.json').read_text());binary=repo/'planet'
  if sha(cache/'results.json')!=contract['old_run']['results_sha256'] or old['status']!='FAILED' or old['full_planet_invocations']!=8:raise ValueError('old failed cache identity changed')
  if sha(cache/'numeric-contract.json')!=contract['frozen_base_contract_sha256']:raise ValueError('old numeric contract changed')
  if contract['base_acceptance']!=base:raise ValueError('embedded acceptance differs from authenticated original contract')
  caps=contract['budget']
  if caps['max_new_full_fits']>12 or caps['max_cumulative_full_fits']>20 or caps['max_new_search_full_fits']+caps['max_new_confirmation_full_fits']>caps['max_new_full_fits']:raise ValueError('unsupported fit budget')
  rows={x['name']:x for x in old['cases']};reused={};entries={}
  for name in [contract['truth']['cached_case'],contract['cached_upper_case'],contract['cached_target_check_case'],'B-tight']:
   d=cache/name
   for artifact in ['run.cfg','profile.csv','model.txt','model.txt.tp.json','acceptance-contract.json','acceptance.json','before-run.json','source-manifest.json','stdout.log','stderr.log']:authenticate_cached_file(cache,name+'/'+artifact,original_index)
   if sha(d/'model.txt')!=rows[name]['model_sha256']:raise ValueError('cached model differs from authenticated original result')
   diag=json.loads((d/'model.txt.tp.json').read_text());accept=json.loads((d/'acceptance-contract.json').read_text())
   if rows[name]['status']!='PASS' or rows[name]['exit_code']!=0:raise ValueError('cached model not passed')
   verify(d/'model.txt.tp.json',d/'acceptance-contract.json')
   if accept['artifacts']['build']['sha256']!=sha(binary):raise ValueError('cached/current solver binaries differ')
   if diag['total_radius_cm']!=rows[name]['radius_cm']:raise ValueError('cached radius differs from diagnostic')
   entries[name]=diag;reused[name]={'directory':str(d),'original_acceptance_contract_sha256':sha(d/'acceptance-contract.json'),'diagnostics_sha256':sha(d/'model.txt.tp.json'),'original_config_sha256':sha(d/'run.cfg'),'radius_cm':diag['total_radius_cm'],'requested_fraction':rows[name]['gas_fraction'],'original_controller_identity':'retained in original source manifest; not relabelled as followup'}
  target_name=contract['truth']['cached_case'];upper_name=contract['cached_upper_case'];target=entries[target_name]['total_radius_cm']
  if target!=contract['truth']['radius_cm']:raise ValueError('truth target changed')
  if contract['bracket_fraction'][1]!=rows[upper_name]['gas_fraction'] or contract['truth']['gas_fraction']!=rows[target_name]['gas_fraction']:raise ValueError('cached endpoint/truth fraction mismatch')
  av=config_values(cache/target_name/'run.cfg');bv=config_values(cache/upper_name/'run.cfg')
  if {k:v for k,v in av.items() if k!='output_file'}!={k:v for k,v in bv.items() if k!='output_file'}:raise ValueError('cached target/upper physical settings differ')
  if bv['tp_profile_file']!='"profile.csv"':raise ValueError('cached TP profile is not the declared cfg-relative file')
  for k,v in base['solver_controls'].items():
   if float(bv[k])!=v:raise ValueError('cached upper controls differ')
  if bv['atm_phasedgm']!='"gas_fixed_mu2"' or rows[target_name]['gas_fraction']!=.01 or rows[upper_name]['gas_fraction']!=.01:raise ValueError('cached EOS/truth fraction differs')
  for name,slope in [(target_name,30),(upper_name,40)]:
   pts=[list(map(float,line.split(','))) for line in (cache/name/'profile.csv').read_text().splitlines()[1:] if line.strip()]
   for pressure,temp in pts:
    if abs(temp-(300+slope*math.log(pressure/.1)))>1e-12*max(1,temp):raise ValueError('cached curve identity differs')
   reused[name]['branch_screen']=screen(cache/name,entries[name],contract)
  expected_source=json.loads((cache/target_name/'source-manifest.json').read_text())['files'];frozen_files={str(Path(f['path']).resolve()):f['sha256'] for f in expected_source}
  for path,expected in frozen_files.items():
   if sha(path)!=expected:raise ValueError('cached scientific/verifier source changed: '+path)
  new_files=[cp,Path(__file__).resolve(),repo/'tests/tp_recovery_search.py',repo/'tests/test_tp_recovery_search.py',repo/'tests/test_tp_reciprocal_screen.py',Path(zeros_py.__file__),Path(zeros_binary.__file__)]
  for path in new_files:frozen_files[str(path.resolve())]=sha(path)
  cache_files={str(p.resolve()):sha(p) for p in cache.rglob('*') if p.is_file()}
  freeze={'contract_sha256':sha(cp),'binary':{'path':str(binary),'sha256':sha(binary)},'source_files':[{'path':p,'sha256':v} for p,v in frozen_files.items()],'cached_files':[{'path':p,'sha256':v} for p,v in cache_files.items()],'reused_evidence':reused,'python_version':sys.version,'scipy_version':scipy.__version__,'new_api_calls':0}
  dump(out/'frozen-inputs.json',freeze);shutil.copy2(cp,out/'followup-contract.json');state['status']='PREFLIGHT_PASS';dump(out/'results.json',state)
  if args.preflight_only:print('PREFLIGHT PASS; authenticated caches/build/sources;0 new fits/APIs',flush=True);return 0
  profile_bytes=(cache/upper_name/'profile.csv').read_bytes();template=(cache/upper_name/'run.cfg').read_text();budget=contract['budget'];search_count=0;confirmation_count=0
  def run_case(name,fg,kind='search',variant=None):
   nonlocal search_count,confirmation_count
   if not math.isfinite(fg) or not contract['bracket_fraction'][0]<=fg<=contract['bracket_fraction'][1]:raise ValueError('requested fraction outside frozen follow-up bracket')
   if kind=='search' and search_count>=budget['max_new_search_full_fits']:raise RuntimeError('search fit cap')
   if kind!='search' and confirmation_count>=budget['max_new_confirmation_full_fits']:raise RuntimeError('confirmation cap')
   if state['new_full_fits']>=budget['max_new_full_fits'] or state['cumulative_full_fits']>=budget['max_cumulative_full_fits']:raise RuntimeError('full fit cap')
   for path,expected in {**frozen_files,**cache_files}.items():
    if sha(path)!=expected:raise ValueError('frozen source/cache changed: '+path)
   if sha(binary)!=freeze['binary']['sha256']:raise ValueError('binary changed')
   d=out/name;d.mkdir(exist_ok=False);profile=d/'profile.csv';profile.write_bytes(profile_bytes)
   if variant=='refined':profile.write_text('P_bar,T_K\n'+''.join(format(p,'.17g')+','+format(300+40*math.log(p/.1),'.17g')+'\n' for p in [.1,1,10,100,1e3,1e4,1e5,1e6,1e8,1e10]))
   controls=dict(base['solver_controls']);controls.update(base['tight_controls'] if variant=='tight' else {})
   mass=base['total_mass_earth'];values={'tp_profile_file':'"profile.csv"','mass_of_core':format(mass*(1-fg)*base['rock_core_fraction'],'.17g'),'mass_of_mantle':format(mass*(1-fg)*(1-base['rock_core_fraction']),'.17g'),'mass_of_atm':format(mass*fg,'.17g'),'output_file':'"'+linux(d/'model.txt')+'"',**{k:format(v,'.17g') for k,v in controls.items()}}
   text=template
   for key,value in values.items():
    pattern=r'(?m)^'+re.escape(key)+r'\s*=.*$'
    if not re.search(pattern,text):raise ValueError('missing cfg option '+key)
    text=re.sub(pattern,key+'='+value,text)
   cfg=d/'run.cfg';cfg.write_text(text);dump(d/'source-manifest.json',{'files':freeze['source_files']})
   ordinal=state['new_full_fits']+1;before={'followup_contract_sha256':freeze['contract_sha256'],'binary':freeze['binary'],'config':{'path':str(cfg),'sha256':sha(cfg)},'profile':{'path':str(profile),'sha256':sha(profile)},'requested_fraction':fg,'controls':controls,'kind':kind,'variant':variant,'new_fit_ordinal':ordinal,'cumulative_fit_ordinal':state['cumulative_full_fits']+1};dump(d/'before-run.json',before)
   item={'case':name,'gas_fraction':fg,'kind':kind,'variant':variant,'status':'STARTED','new_fit_ordinal':ordinal};state['cases'].append(item);state['new_full_fits']+=1;state['cumulative_full_fits']+=1
   if kind=='search':search_count+=1
   else:confirmation_count+=1
   dump(out/'results.json',state);print('START',state['cumulative_full_fits'],name,'fg',format(fg,'.17g'),flush=True);start=time.time()
   with (d/'stdout.log').open('w') as stdout,(d/'stderr.log').open('w') as stderr:
    try:result=subprocess.run(['wsl','--cd',linux(repo),'--exec','timeout','--signal=TERM','--kill-after=5',str(budget['max_seconds_per_case'])+'s',linux(binary),linux(cfg)],stdout=stdout,stderr=stderr,timeout=135)
    except subprocess.TimeoutExpired:
     item.update(exit_code=124,seconds=time.time()-start,status='FAILED');dump(out/'results.json',state)
     raise RuntimeError(name+' timeout; fit counted and contract stopped')
   item.update(exit_code=result.returncode,seconds=time.time()-start,status='FAILED');dump(out/'results.json',state)
   if result.returncode:raise RuntimeError(name+' model exit '+str(result.returncode))
   diagpath=d/'model.txt.tp.json';diag=json.loads(diagpath.read_text());runtime=copy.deepcopy(base);runtime['requested_gas_fraction']=fg;runtime['followup_contract_sha256']=freeze['contract_sha256'];runtime['artifacts']={k:{'path':str(p),'sha256':sha(p)} for k,p in [('build',binary),('config',cfg),('profile',profile),('source_manifest',d/'source-manifest.json'),('diagnostics',diagpath)]};dump(d/'acceptance-contract.json',runtime)
   accepted=verify(diagpath,d/'acceptance-contract.json');dump(d/'acceptance.json',accepted);branch=screen(d,diag,contract);dump(d/'branch-screen.json',branch)
   item.update(status='PASS',model_sha256=sha(d/'model.txt'),diagnostics_sha256=sha(diagpath),radius_cm=diag['total_radius_cm'],measured_gas_fraction=accepted['measured_gas_fraction'],target_relative_residual=(diag['total_radius_cm']-target)/target,branch_screen=branch);dump(out/'results.json',state);print('PASS',name,'radius_error',format(item['target_relative_residual'],'.8g'),flush=True);return dict(item)
  state['status']='RUNNING';dump(out/'results.json',state)
  lowfg,highfg=contract['bracket_fraction'];low=run_case('search-01-lower',lowfg);high={'case':'cached-'+upper_name,'gas_fraction':highfg,'radius_cm':entries[upper_name]['total_radius_cm'],'cached':True}
  def evaluate(fg):return run_case('search-'+str(search_count+1).zfill(2),fg)
  sr=contract['search'];search=recover(evaluate,low,high,target,radius_rtol=sr['nominal_radius_relative_max'],fraction_width=sr['signed_fraction_bracket_width_max'],max_new_evaluations=budget['max_new_search_full_fits']-search_count,xtol=sr['xtol_log_fraction'],rtol=sr['rtol'],maxiter=sr['max_brent_iterations']);state['search']=search;dump(out/'results.json',state)
  estimate=search['candidate'];fg=estimate['gas_fraction'];confirmed=[]
  for name,variant in [('confirm-tight','tight'),('confirm-refined','refined')]:
   point=run_case(name,fg,kind='confirmation',variant=variant);change=abs(point['radius_cm']-estimate['radius_cm'])/estimate['radius_cm']
   if abs(point['target_relative_residual'])>contract['confirmation']['radius_relative_max'] or change>contract['confirmation']['relative_change_from_nominal_max']:raise ValueError(name+' independent numerical target check failed')
   if abs(point['radius_cm']-entries[contract['cached_target_check_case']]['total_radius_cm'])/target>contract['confirmation']['radius_relative_max']:raise ValueError(name+' refined-target consistency failed')
   confirmed.append({'case':name,'same_fraction':fg,'target_relative_residual':point['target_relative_residual'],'relative_change_from_nominal':change})
  state.update(status='PASS_LOCAL_ENGINEERING_RECOVERY',stage4_claim='one selected reciprocal local recovery; original direction remains FAILED',recovery={'truth_profile':'A30','fit_profile':'B40','true_fraction':contract['truth']['gas_fraction'],'inferred_fraction':fg,'signed_bias_fraction':fg-contract['truth']['gas_fraction'],'relative_bias':fg/contract['truth']['gas_fraction']-1,'signed_bracket_fraction':[search['lower']['gas_fraction'],search['upper']['gas_fraction']],'nominal_radius_relative_residual':estimate['residual'],'confirmation':confirmed,'unique_root_proven':False,'statistical_confidence_interval':False})
  print('PASS LOCAL RECIPROCAL RECOVERY',json.dumps(state['recovery']),flush=True)
 except Exception as error:
  state.update(status='FAILED',error=type(error).__name__+': '+str(error));print('FAILED',state['error'],flush=True)
 dump(out/'results.json',state);return 0 if state['status']=='PASS_LOCAL_ENGINEERING_RECOVERY' else 1

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-root',required=True);p.add_argument('--cache-root',required=True);p.add_argument('--contract',required=True);p.add_argument('--output-root',required=True);p.add_argument('--preflight-only',action='store_true');sys.exit(run(p.parse_args()))

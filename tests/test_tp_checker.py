"""Protocol fixtures only: hashes/thresholds cannot turn these into real solver evidence."""
import copy, hashlib, json
from pathlib import Path
from check_tp_model import verify
root=Path(__file__).resolve().parent/'.build/checker-fixtures';root.mkdir(parents=True,exist_ok=True)
def dump(path,value): path.write_text(json.dumps(value,allow_nan=True))
def entry(path): return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
for name in ['build','config','source.cpp']: (root/name).write_text('independent checker protocol fixture\n')
profile=root/'profile.csv';profile.write_text('P_bar,T_K\n0.1,300\n100,500\n')
manifest=root/'source-manifest.json';dump(manifest,{'files':[entry(root/'source.cpp')]})
mp,kb,ME=1.672621777e-24,1.3806488e-16,5.9722e27
rows=[{'mass_g':4.95*ME,'pressure_cgs':1e8,'temperature_K':500,'density_g_cm3':1e8*2*mp/(kb*500)}, {'mass_g':5*ME,'pressure_cgs':1e5,'temperature_K':300,'density_g_cm3':1e5*2*mp/(kb*300)}]
rows.insert(1,{'mass_g':4.975*ME,'pressure_cgs':1e6*(10**.5),'temperature_K':400,'density_g_cm3':1e6*(10**.5)*2*mp/(kb*400)})
base={'schema_version':1,'status':'success','ode_status':0,'corrected_fit':False,'eos_selector':'gas_fixed_mu2','mmol':2,'n':2,'pressure_unit':'dyn/cm2','temperature_unit':'K','mass_unit':'g','profile_min_pressure_cgs':1e5,'profile_max_pressure_cgs':1e8,'outer_pressure_cgs':1e5,'outer_temperature_K':300,'gas_pressure_min':1e5,'gas_pressure_max':1e8,'accepted_gas_pressure_max':1e8,'fit_mass':ME,'gas_base_mass':4.95*ME,'gas_base_pressure':1e8,'gas_base_temperature':500,'total_mass_g':5*ME,'total_radius_cm':1e9,'fit_raw':{'Ri':1e9,'Ro':1e9,'Pi':1e13,'Po':1e13,'Ti':1000,'To':1000},'fit_residual':{'radius':0,'pressure':0,'temperature':0},'gas_rows':rows,'max_effective_relative':0,'max_density_relative':0,'max_pre_projection_relative':1e-8,'max_knot_pressure_projection_relative':0}
contract={'requested_gas_fraction':.01,'outer_pressure_bar':.1,'outer_temperature_K':300,'total_mass_earth':5,'earth_mass_g':ME,'density_formula':{'mmol':2,'mp':mp,'kb':kb},'thresholds':{'normalized_fit_residual_max':1e-6,'effective_temperature_relative_max':1e-12,'stored_density_relative_max':1e-10,'accepted_pre_projection_temperature_relative_max':1e-6,'total_mass_relative_error_max':1e-8},'artifacts':{key:entry(path) for key,path in [('build',root/'build'),('config',root/'config'),('profile',profile),('source_manifest',manifest)]}}
diag=root/'diagnostics.json';cp=root/'contract.json';count=0
def case(name,mutate=None,contract_mutate=None,expected=None):
 global count
 d=copy.deepcopy(base);c=copy.deepcopy(contract)
 if mutate:mutate(d)
 dump(diag,d);c['artifacts']['diagnostics']=entry(diag)
 if contract_mutate:contract_mutate(c)
 dump(cp,c)
 try: result=verify(diag,cp)
 except (ValueError,KeyError,TypeError) as error:
  if expected is None or expected not in str(error):raise AssertionError(name+': wrong rejection '+str(error))
 else:
  if expected is not None:raise AssertionError(name+': invalid fixture accepted')
  assert result['status']=='PASS'
 count+=1
case('valid')
case('wrong status',lambda d:d.update(ode_status=2),expected='ODE')
case('corrected',lambda d:d.update(corrected_fit=True),expected='corrected')
case('nonfinite',lambda d:d.update(total_radius_cm=float('nan')),expected='nonfinite')
case('coverage',lambda d:d.update(gas_pressure_min=1),expected='coverage')
case('stored T',lambda d:d['gas_rows'][1].update(temperature_K=510),expected='stored T')
case('stored rho',lambda d:d['gas_rows'][1].update(density_g_cm3=1),expected='stored density')
case('raw T',lambda d:d.update(max_pre_projection_relative=.01),expected='pre-projection')
case('missing threshold',contract_mutate=lambda c:c['thresholds'].pop('stored_density_relative_max'),expected='stored_density_relative_max')
case('hash mismatch',contract_mutate=lambda c:c['artifacts']['diagnostics'].update(sha256='0'*64),expected='hash mismatch')
case('missing build identity',contract_mutate=lambda c:c['artifacts'].pop('build'),expected='build')
case('fit rank',lambda d:d.update(fit_mass=4.99*ME),expected='fitting mass')
case('fit raw discrepancy',lambda d:d['fit_residual'].update(radius=.01),expected='differs from raw')
def bad_fit(d):
 d['fit_raw']['Ri']*=1.01;a=d['fit_raw'];d['fit_residual']['radius']=(a['Ri']-a['Ro'])/(a['Ri']+a['Ro'])
case('fit tolerance',bad_fit,expected='fit residual radius')
case('missing rows',lambda d:d.update(gas_rows=[]),expected='gas rows')
case('wrong EOS',lambda d:d.update(mmol=3),expected='EOS')
case('truncated gas base mass',lambda d:d['gas_rows'][0].update(mass_g=4.96*ME),expected='gas-base mass anchor')
case('truncated gas base P',lambda d:d['gas_rows'][0].update(pressure_cgs=5e7),expected='gas-base P/T anchor')
case('truncated surface mass',lambda d:d['gas_rows'][-1].update(mass_g=4.99*ME),expected='surface total-mass anchor')
case('wrong requested composition',contract_mutate=lambda c:c.update(requested_gas_fraction=.02),expected='requested gas mass interval')
print('Independent diagnostic checker:',count,'protocol cases passed; no scientific solver evidence')

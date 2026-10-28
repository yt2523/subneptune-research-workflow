"""Independent prescribed-TP acceptance. Does not launch models or relax a run contract."""
import argparse, bisect, csv, hashlib, json, math
from pathlib import Path

def require(ok, reason):
    if not ok: raise ValueError(reason)

def finite_tree(value):
    if isinstance(value, float): require(math.isfinite(value), 'nonfinite JSON number')
    elif isinstance(value, dict):
        for item in value.values(): finite_tree(item)
    elif isinstance(value, list):
        for item in value: finite_tree(item)

def close(a, b, tol):
    return math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tol*max(1,abs(b))

def verify(diagnostics_path, contract_path):
    diagnostics_path, contract_path = Path(diagnostics_path).resolve(), Path(contract_path).resolve()
    c=json.loads(contract_path.read_text()); d=json.loads(diagnostics_path.read_text())
    finite_tree(c); finite_tree(d)
    artifacts=c['artifacts']; resolved={}
    def artifact(entry):
        p=Path(entry['path']); p=p if p.is_absolute() else contract_path.parent/p
        require(p.is_file(), 'missing identity artifact: '+str(p))
        require(hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'], 'artifact hash mismatch: '+str(p))
        return p.resolve()
    for key in ['build','config','profile','source_manifest','diagnostics']: resolved[key]=artifact(artifacts[key])
    require(resolved['diagnostics']==diagnostics_path, 'wrong diagnostics identity path')
    source=json.loads(resolved['source_manifest'].read_text())
    require(bool(source['files']), 'empty source identity manifest')
    for entry in source['files']: artifact(entry)
    require(d['schema_version']==1 and d['status']=='success', 'sidecar status/schema')
    require(d['ode_status']==0 and d['corrected_fit'] is False, 'ODE failure or corrected fit')
    require(d['eos_selector']=='gas_fixed_mu2' and d['mmol']==2 and d['n']==2, 'wrong fixed density EOS')
    require((d['pressure_unit'],d['temperature_unit'],d['mass_unit'])==('dyn/cm2','K','g'), 'units')
    t=c['thresholds']; names=['normalized_fit_residual_max','effective_temperature_relative_max','stored_density_relative_max','accepted_pre_projection_temperature_relative_max','total_mass_relative_error_max']
    for name in names: require(type(t[name]) in (int,float) and math.isfinite(t[name]) and t[name]>0, 'missing/invalid threshold '+name)
    with resolved['profile'].open(newline='') as f:
        reader=csv.reader(f); require(next(reader)==['P_bar','T_K'], 'profile header')
        points=[(float(row[0])*1e6,float(row[1])) for row in reader if row]
    require(len(points)>=2, 'profile requires two points')
    for i,(p,temp) in enumerate(points): require(math.isfinite(p) and math.isfinite(temp) and p>0 and temp>0 and (i==0 or p>points[i-1][0]), 'profile data')
    pressures=[p for p,_ in points]
    def temperature(p):
        require(pressures[0]<=p<=pressures[-1], 'gas evaluation outside profile coverage')
        i=min(max(bisect.bisect_right(pressures,p)-1,0),len(points)-2)
        p0,t0=points[i]; p1,t1=points[i+1]
        return t0+(t1-t0)*math.log(p/p0)/math.log(p1/p0)
    require(close(d['profile_min_pressure_cgs'],pressures[0],1e-14) and close(d['profile_max_pressure_cgs'],pressures[-1],1e-14),'profile bounds identity')
    p0=c['outer_pressure_bar']*1e6; T0=c['outer_temperature_K']
    require(close(d['outer_pressure_cgs'],p0,1e-12) and close(d['outer_temperature_K'],T0,1e-12),'outer boundary identity')
    require(close(temperature(p0),T0,1e-12),'profile outer anchor')
    require(pressures[0]<=d['gas_pressure_min']<=d['gas_pressure_max']<=pressures[-1], 'trial coverage range')
    require(d['gas_pressure_min']<=d['accepted_gas_pressure_max']<=d['gas_pressure_max'], 'accepted/trial pressure range')
    require(0<d['fit_mass']<d['gas_base_mass']<d['total_mass_g'], 'actual fitting mass must be below gas')
    require(d['total_radius_cm']>0, 'positive radius')
    constants=c['density_formula']; require(constants['mmol']==2 and constants['mp']>0 and constants['kb']>0,'density constants')
    expected_mass=c['total_mass_earth']*c['earth_mass_g']
    require(abs(d['total_mass_g']-expected_mass)/expected_mass<=t['total_mass_relative_error_max'],'total mass residual')
    requested=c['requested_gas_fraction']; require(0<requested<1,'requested gas fraction')
    expected_base=expected_mass*(1-requested)
    require(abs(d['gas_base_mass']-expected_base)/expected_mass<=t['total_mass_relative_error_max'],'requested gas mass interval')
    measured=1-d['gas_base_mass']/d['total_mass_g']
    require(abs(measured-requested)<=t['total_mass_relative_error_max'],'measured/requested gas fraction')
    require(close(d['gas_base_temperature'],temperature(d['gas_base_pressure']),t['effective_temperature_relative_max']),'gas-base effective temperature')
    raw=d['fit_raw']; residual=d['fit_residual']
    for key,a,b in [('radius','Ri','Ro'),('pressure','Pi','Po'),('temperature','Ti','To')]:
        require(raw[a]>0 and raw[b]>0,'positive raw fit state')
        actual=(raw[a]-raw[b])/(raw[a]+raw[b])
        require(close(residual[key],actual,1e-14),'reported fit residual differs from raw '+key)
        require(abs(actual)<=t['normalized_fit_residual_max'],'fit residual '+key)
    maxT=maxrho=0.; rows=d['gas_rows']; require(len(rows)>=2,'missing actual gas rows')
    edge=64*2.220446049250313e-16
    require(close(rows[0]['mass_g'],d['gas_base_mass'],edge), 'gas-base mass anchor')
    require(close(rows[0]['pressure_cgs'],d['gas_base_pressure'],1e-12) and close(rows[0]['temperature_K'],d['gas_base_temperature'],1e-12), 'gas-base P/T anchor')
    require(close(rows[-1]['mass_g'],d['total_mass_g'],edge), 'surface total-mass anchor')
    previous=-math.inf
    for row in rows:
        mass,p,temp,rho=[row[k] for k in ['mass_g','pressure_cgs','temperature_K','density_g_cm3']]
        slack=64*2.220446049250313e-16*max(1,d['total_mass_g'])
        require(mass>=previous and d['gas_base_mass']-slack<=mass<=d['total_mass_g']+slack,'gas mass interval/order'); previous=mass
        require(temp>0 and rho>0 and p>0,'positive gas state')
        expectedT=temperature(p); expectedrho=p*constants['mmol']*constants['mp']/(constants['kb']*expectedT)
        maxT=max(maxT,abs(temp-expectedT)/max(1,abs(expectedT))); maxrho=max(maxrho,abs(rho-expectedrho)/expectedrho)
    require(maxT<=t['effective_temperature_relative_max'],'actual stored T mismatch')
    require(maxrho<=t['stored_density_relative_max'],'actual stored density mismatch')
    require(close(d['max_effective_relative'],maxT,5e-15) and close(d['max_density_relative'],maxrho,5e-15),'reported maxima disagree with gas rows')
    require(0<=d['max_pre_projection_relative']<=t['accepted_pre_projection_temperature_relative_max'],'raw pre-projection T mismatch')
    require(0<=d['max_knot_pressure_projection_relative']<=128*2.220446049250313e-16,'knot projection beyond roundoff')
    require(close(rows[-1]['pressure_cgs'],p0,1e-12) and close(rows[-1]['temperature_K'],T0,1e-12),'actual surface gas state')
    return {'status':'PASS','gas_rows':len(rows),'max_effective_relative':maxT,'max_density_relative':maxrho,'radius_cm':d['total_radius_cm'],'requested_gas_fraction':requested,'measured_gas_fraction':measured}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--diagnostics',required=True);parser.add_argument('--contract',required=True);args=parser.parse_args()
    try: print(json.dumps(verify(args.diagnostics,args.contract)))
    except (ValueError,KeyError,OSError,TypeError,ZeroDivisionError,StopIteration) as error: parser.exit(1,'FAIL '+str(error)+'\n')

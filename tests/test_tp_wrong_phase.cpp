// Serialization-only guard fixture. No fitting search or scientific acceptance.
#include "hydro.h"
#include "EOSlist.h"
#include "tp_diagnostics.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <iomanip>

double rho_eps_rel=1e-11,T_eps_rel=1e-11,ode_eps_rel0=1e-7,ode_eps_rel1=1e-10,ode_eps_rel2=1e-10,R_eps_rel=2e-5,P_eps_rel=1e-10,fit_eps_rel=1e-4;
int fit_iter=0,count_shoot=0,count_step=0;bool verbose=false;
static void req(bool v,const char* why){if(!v)throw std::runtime_error(why);}
static EOS* mixed_atmosphere(double pressure,double temperature){
 if(!(pressure>0 && temperature>0))return nullptr;
 return pressure<2e5 ? Gas_iso : Gas;
}
int main(int argc,char** argv){
 gsl_set_error_handler_off();
 try{
  req(argc==2,"test directory required");
  const std::string dir=argv[1],profile=dir+"/phase-tp.csv",output=dir+"/wrong-phase-model.txt";
  {std::ofstream f(profile);f<<std::setprecision(17)<<"P_bar,T_K\n0.1,300\n10000000000,"<<300+40*std::log(1e11)<<"\n";}
  const TPProfile tp=TPProfile::load_csv(profile);
  PhaseDgm inconsistent("test_atmosphere_mixed_eos",mixed_atmosphere);
  vector<PhaseDgm> comps={core,mant,water,inconsistent};
  vector<double> masses={1.60875,3.34125,0,.05},gaps={0,0,0,300};
  double Ri=0,Pi=0,Ti=0,Ro=0,Po=0,To=0;
  hydro model(2*RE,1e14,3000,comps,masses,gaps,false,ME,1e-4,1e5,Ri,Pi,Ti,Ro,Po,To,&tp);
  std::cout<<std::setprecision(17)<<"constructor rows="<<model.getsize()<<" status="<<model.getstatus()<<" error="<<model.tp_diagnostics().error<<'\n';
  req(model.getsize()>0,"fixture constructor must be usable");
  const TPDiagnostics& d=model.tp_diagnostics();
  req(d.error.empty() && !d.corrected_fit,"fixture must avoid constructor error/correction rejection");
  int wrong=0,deep=0,bases=0;
  const double mass_eps=64*std::numeric_limits<double>::epsilon()*d.gas_base_mass;
  for(int i=0;i<model.getsize();++i){
   const double mass=model.getM(i),pressure=model.getP(i);
   if(std::abs(mass-d.gas_base_mass)<=mass_eps && model.getphase(i)==Gas)++bases;
   if(mass>d.gas_base_mass+mass_eps){
    if(model.getphase(i)==Gas_iso){++wrong;req(pressure<2e5,"wrong-EOS fixture pressure");}
    else if(model.getphase(i)==Gas)++deep;
    else throw std::runtime_error("unexpected EOS in atmosphere fixture");
   }
  }
  std::cout<<"gas_base_P="<<d.gas_base_pressure<<" Gas_boundary_rows="<<bases<<" deep_Gas_rows="<<deep<<" near_surface_Gas_iso_rows="<<wrong<<'\n';
  req(bases>0 && d.gas_base_pressure>2e5,"actual Gas phase required at gas base");
  req(deep>0 && wrong>0,"fixture needs both valid deep Gas and wrong near-surface EOS rows");
  req(model.getphase(model.getsize()-1)==Gas_iso,"surface must exercise wrong phase");
  model.setstatus(0); // Simulate successful status only to reach serializer validation.
  {std::ofstream f(output+".tp.json");f<<"STALE";}
  std::string error;
  try{write_tp_diagnostics(output,model,tp,1e5,300);}catch(const std::exception& e){error=e.what();}
  std::cout<<"writer_error="<<error<<'\n';
  req(error=="Non-Gas phase inside gas mass interval","writer must reject actual wrong gas-interval EOS, without skipping its rows");
  req(!std::ifstream(output+".tp.json"),"rejected writer must remove stale success sidecar");
  req(!std::ifstream(output+".tp.json.tmp"),"rejected writer must leave no temporary success sidecar");
  std::cout<<"PASS wrong-phase serialization guard\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}

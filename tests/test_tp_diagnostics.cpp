// Writer I/O fixture: setstatus(0) below simulates a successful solver for serialization only.
// This is not a converged model or scientific acceptance case.
#include "hydro.h"
#include "EOSlist.h"
#include "tp_diagnostics.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <cmath>
double rho_eps_rel=1e-11,T_eps_rel=1e-11,ode_eps_rel0=1e-7,ode_eps_rel1=1e-10,ode_eps_rel2=1e-10,R_eps_rel=2e-5,P_eps_rel=1e-10,fit_eps_rel=1e-4;
int fit_iter=0,count_shoot=0,count_step=0; bool verbose=false;
static int checks=0;
static void req(bool ok,const char* msg){++checks;if(!ok)throw std::runtime_error(msg);}
static bool exists(const std::string& p){return bool(std::ifstream(p));}
int main(int argc,char**argv){try{
 req(argc==2,"fixture directory required");gsl_set_error_handler_off();std::string dir=argv[1],csv=dir+"/diag-tp.csv",out=dir+"/diag-model.txt";
 {std::ofstream f(csv);f<<std::setprecision(17)<<"P_bar,T_K\n0.1,300\n10000000000,"<<300+40*std::log(1e11)<<"\n";}
 auto tp=TPProfile::load_csv(csv);std::vector<PhaseDgm> comp={core,mant,water,atm_fixed_mu2};std::vector<double> mass={1.60875,3.34125,0,.05},gaps={0,0,0,300};double Ri,Pi,Ti,Ro,Po,To;
 hydro model(2*RE,1e14,3000,comp,mass,gaps,false,ME,1e-4,1e5,Ri,Pi,Ti,Ro,Po,To,&tp);
 req(model.getsize()>0,"usable controlled constructor");
 {std::ofstream f(out+".tp.json");f<<"STALE";}
 bool threw=false;try{write_tp_diagnostics(out,model,tp,1e5,300);}catch(const std::exception&){threw=true;}
 req(threw&&!exists(out+".tp.json"),"unconverged fixture must reject and clear stale sidecar");
 model.setstatus(0);write_tp_diagnostics(out,model,tp,1e5,300);
 std::ifstream f(out+".tp.json");std::string contents((std::istreambuf_iterator<char>(f)),{});
 req(!contents.empty()&&contents.front()=='{'&&contents.back()!='\0',"writer must emit real JSON object");
 req(contents.find("gas_rows")!=std::string::npos,"actual gas rows must be emitted");
 threw=false;try{write_tp_diagnostics(out,model,tp,1e5,std::numeric_limits<double>::quiet_NaN());}catch(const std::exception&){threw=true;}
 req(threw&&!exists(out+".tp.json"),"nonfinite input must reject with no stale success");
 threw=false;try{write_tp_diagnostics(out,model,tp,1e5,-1);}catch(const std::exception&){threw=true;}
 req(threw&&!exists(out+".tp.json"),"nonpositive input must reject");
 write_tp_diagnostics(out,model,tp,1e5,300);
 req(!exists(out+".tp.json.tmp"),"successful atomic write leaves no temporary sidecar");
 {std::ofstream e(dir+"/diag-expected.txt");e<<std::setprecision(17)<<model.tp_diagnostics().fit_Ri<<' '<<model.tp_diagnostics().fit_Ro<<' '<<model.tp_diagnostics().max_pre_projection_relative<<'\n';}
 std::cout<<"Diagnostic writer I/O fixture: "<<checks<<" checks passed; simulated solver status only\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}

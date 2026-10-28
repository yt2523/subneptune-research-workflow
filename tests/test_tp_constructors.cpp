// Independent construction/storage checks, not converged planet inference.
#include "hydro.h"
#include "EOSlist.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <cmath>
double rho_eps_rel=1e-11,T_eps_rel=1e-11,ode_eps_rel0=1e-7,ode_eps_rel1=1e-10,ode_eps_rel2=1e-10,R_eps_rel=2e-5,P_eps_rel=1e-10,fit_eps_rel=1e-4;
int fit_iter=0,count_shoot=0,count_step=0;
bool verbose=false;
static int n=0;
static void req(bool ok,const char* msg){++n;if(!ok)throw std::runtime_error(msg);}
static void near(double a,double b,double tol,const char*msg){req(std::isfinite(a)&&std::abs(a-b)<=tol*std::max(std::abs(b),1e-300),msg);}
static void gas_rows(hydro& h,const TPProfile& tp,double base){req(h.getsize()>0,"construction needs usable rows");int gas=0;for(int i=0;i<h.getsize();++i){if(h.getM(i)>base+64*std::numeric_limits<double>::epsilon()*base){++gas;auto x=tp.at_cgs(h.getP(i));near(h.getT(i),x.temperature_K,1e-12,"stored gas T must equal prescribed T");near(h.getrho(i),Gas->density(h.getP(i),x.temperature_K,-1),1e-10,"stored gas density must use same prescribed T");}}req(gas>2,"gas rows exercised");}
int main(int argc,char**argv){try{req(argc==2,"fixture directory");gsl_set_error_handler_off();std::string dir=argv[1];{std::ofstream f(dir+"/constructor-tp.csv");f<<std::setprecision(17)<<"P_bar,T_K\n0.1,300\n10000000000,"<<300+40*std::log(1e11)<<"\n";}
 auto tp=TPProfile::load_csv(dir+"/constructor-tp.csv");std::vector<PhaseDgm> comp={core,mant,water,atm_fixed_mu2};std::vector<double> masses={1.60875,3.34125,0,0.05},gaps={0,0,0,300};double base=(masses[0]+masses[1])*ME;
 hydro first(2*RE,comp,masses,gaps,1e-4,1e5,false,&tp);gas_rows(first,tp,base);
 double Ri,Pi,Ti,Ro,Po,To;
 hydro both(2*RE,1e14,3000,comp,masses,gaps,false,ME,1e-4,1e5,Ri,Pi,Ti,Ro,Po,To,&tp);gas_rows(both,tp,base);
 const auto& d=both.tp_diagnostics();req(d.max_pre_projection_relative>1e-12,"loose integration exercises nonzero preprojection mismatch");near(d.gas_base_mass,base,1e-12,"gas-base mass is actual nongas mass in grams");near(d.gas_base_temperature,tp.at_cgs(d.gas_base_pressure).temperature_K,1e-12,"gas-base T consistent");
 bool boundary=false;for(int i=1;i<both.getsize();++i){if(both.getM(i)==both.getM(i-1)&&std::abs(both.getM(i)-base)<=64*std::numeric_limits<double>::epsilon()*base){near(both.getT(i),both.getT(i-1),1e-12,"zero-water gas/solid T continuity");boundary=true;}}req(boundary,"actual gas/solid interface rows checked");
 {std::ofstream f(dir+"/short-tp.csv");f<<"P_bar,T_K\n1,300\n10000000000,1300\n";}auto bad=TPProfile::load_csv(dir+"/short-tp.csv");
 hydro failed(2*RE,1e14,3000,comp,masses,gaps,false,ME,1e-4,1e5,Ri,Pi,Ti,Ro,Po,To,&bad);req(failed.getsize()==0&&!failed.tp_diagnostics().error.empty(),"surface lookup failure leaves no partial usable model");
 hydro wrongfit(2*RE,1e14,3000,comp,masses,gaps,false,4.99*ME,1e-4,1e5,Ri,Pi,Ti,Ro,Po,To,&tp);req(wrongfit.getsize()==0,"gas-located fitting point rejected");
 std::cout<<"Independent TP constructor checks: "<<n<<" assertions passed\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}

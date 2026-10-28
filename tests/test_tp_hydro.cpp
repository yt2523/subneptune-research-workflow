// Fixed independent coordinator callback acceptance; builder must not edit.
#include "hydro.h"
#include "EOSlist.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <cmath>
double rho_eps_rel=1e-11,T_eps_rel=1e-11,ode_eps_rel0=1e-7,ode_eps_rel1=1e-10,ode_eps_rel2=1e-10,R_eps_rel=2e-5,P_eps_rel=1e-10,fit_eps_rel=1e-4;
int fit_iter=0,count_shoot=0,count_step=0;
bool verbose=false;
extern int derivs_m2(double,const double[],double[],void*);
extern int derivs_m3(double,const double[],double[],void*);
static int n=0;
static void req(bool p,const char* msg){++n;if(!p)throw std::runtime_error(msg);}
static void near(double a,double b,const char* msg){req(std::isfinite(a)&&std::abs(a-b)<=1e-11*std::max(std::abs(b),1e-300),msg);}
int main(int argc,char**argv){try{req(argc==2,"fixture directory");std::string path=std::string(argv[1])+"/hydro-tp.csv";{std::ofstream f(path);f<<"P_bar,T_K\n1,300\n10000,700\n";}
 auto tp=TPProfile::load_csv(path);TPDiagnostics diag;diag.enabled=true;
 std::vector<double> masses={1,3.95,0,0.05};
 for(bool inward:{true,false}){
  mass_params p={{1e-4,0.},masses,Gas,&tp,true,&diag};
  double y[3]={2*RE,1e8,800},d[3];auto v=tp.at_cgs(y[1]);
  double expected_rho=Gas->density(y[1],v.temperature_K,-1.);
  int code=inward?derivs_m2(0.1*ME,y,d,&p):derivs_m3(0.1*ME,y,d,&p);
  req(code==GSL_SUCCESS,"callback success");near(p.x[0],expected_rho,"density must use prescribed T, not stale yT");
  near(d[0],(inward?-1.:1.)/(4*pi*y[0]*y[0]*expected_rho),"radius derivative density");
  near(d[2],v.dT_dP_cgs*d[1],"signed TP chain rule despite old thermal=0");
  req(inward?d[1]>0:d[1]<0,"pressure derivative direction");
  y[1]=1e12;code=inward?derivs_m2(0.1*ME,y,d,&p):derivs_m3(0.1*ME,y,d,&p);
  req(code==GSL_EBADFUNC,"coverage failure propagated through GSL");req(!diag.error.empty(),"coverage error recorded");diag.error.clear();
 }
 mass_params inactive={{1e-4,0.},masses,Gas,&tp,false,&diag};double y[3]={2*RE,1e12,800},d[3];
 req(derivs_m3(0.1*ME,y,d,&inactive)==GSL_SUCCESS,"non-gas does not query TP outside coverage");near(d[2],0.,"legacy thermal unchanged when inactive");
 req(find_phase_gas_fixed_mu2(1e5,300)==Gas&&find_phase_gas_fixed_mu2(1e10,300)==Gas,"same gas EOS across100bar");
 std::cout<<"Independent TP hydro callbacks: "<<n<<" assertions passed\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}

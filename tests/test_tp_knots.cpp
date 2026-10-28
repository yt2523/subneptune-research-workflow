// Independent coordinator knot-control acceptance.
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
#ifdef TP_RED_STUB
// Test fixture only: legacy behavior, proves lack of explicit knot handling.
int tp_evolve_step(gsl_odeiv2_evolve* e,gsl_odeiv2_control* c,gsl_odeiv2_step* s,gsl_odeiv2_system* sys,double* m,double mmax,double* h,double y[]){return gsl_odeiv2_evolve_apply(e,c,s,sys,m,mmax,h,y);}
#endif
static int n=0;
static void req(bool ok,const char* msg){++n;if(!ok)throw std::runtime_error(msg);}
int main(int argc,char**argv){try{req(argc==2,"fixture directory");gsl_set_error_handler_off();std::string path=std::string(argv[1])+"/knot-tp.csv";{std::ofstream f(path);f<<"P_bar,T_K\n1,300\n10,400\n1000,200\n";}
 auto tp=TPProfile::load_csv(path);TPDiagnostics diag;diag.enabled=true;std::vector<double> masses={1,3.95,0,0.05};
 mass_params p={{1e-4,0.},masses,Gas,&tp,true,&diag};gsl_odeiv2_system sys={derivs_m2,nullptr,3,&p};
 auto* step=gsl_odeiv2_step_alloc(gsl_odeiv2_step_rkf45,3);auto* control=gsl_odeiv2_control_y_new(1e-15,1e-10);auto* evolve=gsl_odeiv2_evolve_alloc(3);
 double m=0,h=1e23,y[3]={2*RE,1e6,300};const double end=5e23;int iterations=0;bool landed=false;
 while(m<end&&iterations++<10000){double before=m;int code=tp_evolve_step(evolve,control,step,&sys,&m,end,&h,y);req(code==GSL_SUCCESS,"knot-aware GSL step must succeed");req(m>before,"mass must advance");if(y[1]==1e7)landed=true;auto expected=tp.at_cgs(y[1]);req(std::isfinite(y[2])&&std::abs(y[2]-expected.temperature_K)<=1e-6*expected.temperature_K,"integrated T follows prescribed kink");}
 req(iterations<10000&&m==end,"bounded integration completes");req(y[1]>1e7&&y[1]<1e9,"trajectory crosses internal knot within coverage");
 req(diag.knot_snaps>=1&&landed,"explicit knot control lands on stored node");req(diag.max_knot_pressure_projection_relative<=128*std::numeric_limits<double>::epsilon(),"pressure projection is roundoff bounded");
 gsl_odeiv2_evolve_free(evolve);gsl_odeiv2_control_free(control);gsl_odeiv2_step_free(step);
 std::cout<<"Independent TP knot control: "<<n<<" assertions passed in "<<iterations<<" steps\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}

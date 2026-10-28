#include "hydro.h"
#include <iomanip>
#include <cstdlib>
#include <string>

double rho_eps_rel=1e-11,T_eps_rel=1e-11;
double ode_eps_rel0=1e-7,ode_eps_rel1=1e-10,ode_eps_rel2=1e-10;
double R_eps_rel=2e-5,P_eps_rel=1e-10,fit_eps_rel=1e-4;
int fit_iter=0,count_shoot=0,count_step=0;
bool verbose=false;
static EOS* fixture_eos=nullptr;
static double density(double,double,double) {return 10;}
static EOS* phase(double,double) {return fixture_eos;}
static void check(bool v,const char* why){if(!v)throw std::runtime_error(why);}
static double central(double mass){return 1e6+(2*pi*G/3)*100*std::pow(3*mass/(4*pi*10),2./3.);}
static void dump(hydro& h){
  std::cout<<"rows "<<h.getsize()<<" status "<<h.getstatus()<<'\n';
  for(int i=0;i<h.getsize();++i)std::cout<<i<<' '<<h.getR(i)<<' '<<h.getP(i)<<' '<<h.getM(i)<<' '<<h.getT(i)<<' '<<h.getrho(i)<<'\n';
}
int main(int argc,char** argv){
 gsl_set_error_handler_off();
 try {
  check(argc>=2,"usage: callback_regressions inner|outer|coverage [short.csv]");
  std::cout<<std::setprecision(17);
  EOS eos("independent density10",density,nullptr); fixture_eos=&eos;
  vector<PhaseDgm> comps;for(int i=0;i<4;++i)comps.emplace_back("fixture",phase);
  vector<double> masses={4.95,0,0,.05}, gaps={0,0,0,300};
  std::string mode=argv[1];
  if(mode=="inner" || mode=="outer"){
   const double Rp= mode=="inner" ? std::cbrt(3*5*ME/(4*pi*10)) : 1e7;
   const double Pc=central((mode=="inner"?.9:2)*ME);
   double Ri=0,Pi=0,Ti=0,Ro=0,Po=0,To=0;
   hydro h(Rp,Pc,300,comps,masses,gaps,true,ME,1e-10,1e6,Ri,Pi,Ti,Ro,Po,To);
   check(h.getsize()>0,"legacy correction must retain rows");
   if(mode=="inner"){
    bool early=false;for(int i=0;i<h.getsize();++i)if(h.getM(i)<.999*ME && h.getP(i)<=1e6)early=true;
    check(early,"fixture must trigger historical inner correction");
   }else{
    bool early=false;for(int i=0;i<h.getsize();++i)if(h.getM(i)>1.004*ME && h.getP(i)>9e14)early=true;
    check(early,"fixture must trigger historical outer correction");
   }
   std::cout<<"fitting "<<Ri<<' '<<Pi<<' '<<Ti<<' '<<Ro<<' '<<Po<<' '<<To<<'\n';dump(h);
   loop_params p={};p.x={ME,1e-10,1e6};p.Comp=comps;p.M=masses;p.Tgap=gaps;p.iso=true;p.model=nullptr;
   gsl_vector* x=gsl_vector_alloc(3);gsl_vector* f=gsl_vector_alloc(3);
   gsl_vector_set(x,0,Rp);gsl_vector_set(x,1,Pc);gsl_vector_set(x,2,300);
   int status=fitting_error(x,&p,f);
   check(status==GSL_SUCCESS && p.model!=nullptr,"legacy correction callback must retain model");
   std::cout<<"callback "<<status<<' '<<p.model->getsize()<<' '<<gsl_vector_get(f,0)<<' '<<gsl_vector_get(f,1)<<' '<<gsl_vector_get(f,2)<<'\n';
   delete p.model;gsl_vector_free(f);gsl_vector_free(x);
  }
#ifdef CURRENT_TP
  else if(mode=="coverage"){
   check(argc==3,"coverage requires short.csv");
   const TPProfile tp=TPProfile::load_csv(argv[2]);
   const double Rp=std::cbrt(3*5*ME/(4*pi*10));
   double Ri=0,Pi=0,Ti=0,Ro=0,Po=0,To=0;
   hydro direct(Rp,central(2*ME),300,comps,masses,gaps,true,ME,1e-10,1e6,Ri,Pi,Ti,Ro,Po,To,&tp);
   const std::string expected=direct.tp_diagnostics().error;
   std::cout<<"direct_error "<<expected<<'\n';
   check(direct.getsize()==0 && !expected.empty(),"short coverage direct failure");
   check(expected.find("1000000")!=std::string::npos && expected.find("1000100")!=std::string::npos,"diagnostic must retain configured range");
   loop_params p={};p.x={ME,1e-10,1e6};p.Comp=comps;p.M=masses;p.Tgap=gaps;p.iso=true;p.model=nullptr;p.tp=&tp;
   gsl_vector* x=gsl_vector_alloc(3);gsl_vector* f=gsl_vector_alloc(3);
   gsl_vector_set(x,0,Rp);gsl_vector_set(x,1,central(2*ME));gsl_vector_set(x,2,300);
   int status=fitting_error(x,&p,f);
   std::cout<<"fit_status "<<status<<" retained "<<p.tp_error<<'\n';
   bool fit_ok=status==GSL_EBADFUNC && p.model==nullptr && p.tp_error==expected;
   gsl_vector_set(x,2,-999);
   int repeated=fitting_error(x,&p,f);
   check(repeated==GSL_EBADFUNC && p.model==nullptr && p.tp_error==expected,"latched fitting failure must reject later trial and retain first reason");
   delete p.model;p.model=nullptr;gsl_vector_free(f);gsl_vector_free(x);
   p.tp_error.clear();p.x={0,0,1e6};
   double residual=R_hydro(Rp,&p);
   std::cout<<"radius_residual "<<residual<<" sentinel "<<p.x[1]<<" retained "<<p.tp_error<<'\n';
   const bool radius_sentinel=std::isnan(residual) && p.x[1]==-1;
   const bool radius_reason=!p.tp_error.empty() && p.tp_error.find("1000000")!=std::string::npos && p.tp_error.find("1000100")!=std::string::npos;
   const std::string radius_original=p.tp_error;
   check(std::isnan(R_hydro(Rp*1.01,&p)) && p.x[1]==-1 && p.tp_error==radius_original,"latched radius failure must retain original reason across later trial");
   std::cout<<"fit_reason_assertion "<<(fit_ok?"PASS":"FAIL")<<" radius_sentinel_assertion "<<(radius_sentinel?"PASS":"FAIL")<<" radius_reason_assertion "<<(radius_reason?"PASS":"FAIL")<<'\n';
   check(radius_sentinel,"radius failure sentinel must be -1 in x[1]");
   check(fit_ok && radius_reason,"callbacks must retain original TP pressure/range error");
  }
#endif
  else throw std::runtime_error("unknown mode");
  std::cout<<"PASS "<<mode<<'\n';return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}

#include "hydro.h"
#include <iomanip>

double rho_eps_rel=1e-11,T_eps_rel=1e-11;
double ode_eps_rel0=1e-7,ode_eps_rel1=1e-12,ode_eps_rel2=1e-10;
double R_eps_rel=2e-5,P_eps_rel=1e-10,fit_eps_rel=1e-4;
int fit_iter=0,count_shoot=0,count_step=0;
bool verbose=false;
static EOS* constant_eos=nullptr;
static double density(double,double,double) { return 10; }
static EOS* phase(double,double) { return constant_eos; }
int main(int argc,char** argv) {
    gsl_set_error_handler_off();
    try {
        if(argc!=2) throw std::runtime_error("usage: truncation_guard broad.csv");
        TPProfile tp=TPProfile::load_csv(argv[1]);
        EOS test_eos("Independent constant-density guard fixture",density,nullptr);
        constant_eos=&test_eos;
        vector<PhaseDgm> components;
        for(int i=0;i<4;++i) components.emplace_back("independent_constant",phase);
        const double P0=1e6, rho=10, Mcrit=.9995*ME;
        const double Pc=P0+(2*pi*G/3)*rho*rho*std::pow(3*Mcrit/(4*pi*rho),2./3.);
        const double Rp=std::cbrt(3*5*ME/(4*pi*rho));
        double Ri=0,Pi=0,Ti=0,Ro=0,Po=0,To=0;
        hydro model(Rp,Pc,300,components,{4.95,0,0,.05},{0,0,0,300},true,ME,1e-12,P0,Ri,Pi,Ti,Ro,Po,To,&tp);
        const TPDiagnostics& d=model.tp_diagnostics();
        double inner_mass=-1;
        for(int i=1;i<model.getsize();++i) {
            if(model.getM(i)<ME && model.getP(i)<=P0) inner_mass=model.getM(i)/ME;
        }
        std::cout<<std::setprecision(17)<<"truncation size="<<model.getsize()<<" status="<<model.getstatus()<<" inner_mass_ME="<<inner_mass<<" Pi="<<Pi<<" corrected="<<d.corrected_fit<<" error="<<d.error<<'\n';
        // Analytical pressure zero occurs 0.05% before Mfit, inside the legacy 0.1% exemption.
        if(model.getsize()!=0 && !(inner_mass>.999 && inner_mass<1)) throw std::runtime_error("fixture did not isolate the old 0.1% inner-truncation window");
        if(model.getsize()!=0) throw std::runtime_error("TP inner branch truncated before Mfit must be rejected/empty");
        if(d.error.empty()) throw std::runtime_error("TP rejection needs a diagnostic");
        std::cout<<"PASS truncation guard\n";
        return 0;
    } catch(const std::exception& e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}

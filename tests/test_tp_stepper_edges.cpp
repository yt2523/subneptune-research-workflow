#include "hydro.h"
#include <algorithm>
#include <cstdlib>
#include <iomanip>
#include <string>

static void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
static double gradient;
static int synthetic_rhs(double, const double y[], double dy[], void* context) {
    const mass_params& p = *static_cast<mass_params*>(context);
    try {
        dy[0] = 0;
        dy[1] = gradient;
        dy[2] = p.tp->at_cgs(y[1]).dT_dP_cgs * gradient;
        return GSL_SUCCESS;
    } catch (...) { return GSL_EBADFUNC; }
}
struct Integrator {
    gsl_odeiv2_step* s = gsl_odeiv2_step_alloc(gsl_odeiv2_step_rkf45, 3);
    gsl_odeiv2_evolve* e = gsl_odeiv2_evolve_alloc(3);
    gsl_odeiv2_control* c = gsl_odeiv2_control_y_new(1e-10, 1e-12);
    ~Integrator() { gsl_odeiv2_control_free(c); gsl_odeiv2_evolve_free(e); gsl_odeiv2_step_free(s); }
};
static void reverse(const TPProfile& tp) {
    TPDiagnostics diag;
    mass_params p = {{}, {}, nullptr, &tp, true, &diag};
    gsl_odeiv2_system sys = {synthetic_rhs, nullptr, 3, &p};
    Integrator ode;
    gradient = -1e6;
    double x=0, h=95, y[]={123, 1e8, tp.at_cgs(1e8).temperature_K};
    bool hit=false;
    size_t calls=0;
    double max_temperature_error=0;
    while (x<95 && calls++<2000) {
        double previous_x=x, previous_p=y[1];
        require(tp_evolve_step(ode.e, ode.c, ode.s, &sys, &x, 95, &h, y)==GSL_SUCCESS, "reverse step status");
        require(x>previous_x || y[1]!=previous_p, "reverse neither advances nor snaps");
        if (!(y[1]<=previous_p && y[1]>=5e6)) std::cout<<std::setprecision(17)<<"reverse boundary x="<<x<<" P="<<y[1]<<" previous="<<previous_p<<'\n';
        require(y[1]<=previous_p && y[1]>=5e6-1e-5, "reverse pressure monotonicity/range");
        require(std::abs(y[1]-(1e8-1e6*x))<=1e-12*1e8, "reverse pressure/mass drift");
        require(y[0]==123, "reverse radius drift");
        if (y[1]==1e7) hit=true;
        if (!hit) require(y[1]>=1e7, "reverse skipped exact 10-bar knot");
        max_temperature_error=std::max(max_temperature_error,std::abs(y[2]-tp.at_cgs(y[1]).temperature_K));
        require(max_temperature_error<1e-7, "reverse integrated T tracking");
    }
    require(x==95 && calls<2000, "reverse bounded completion");
    require(hit, "reverse exact 10-bar event missing");
    require(std::abs(y[1]-5e6)<=1e-5, "reverse final pressure");
    std::cout << "PASS reverse calls=" << calls << " max_T_abs=" << max_temperature_error << " snaps=" << diag.knot_snaps << '\n';
}
static void near_knot(const TPProfile& tp, double offset=0) {
    TPDiagnostics diag;
    mass_params p = {{}, {}, nullptr, &tp, true, &diag};
    gsl_odeiv2_system sys = {synthetic_rhs, nullptr, 3, &p};
    Integrator ode;
    gradient=1e6;
    double x=offset, h=.5, initial_p=std::nextafter(1e7,0.0);
    double y[]={123,initial_p,tp.at_cgs(initial_p).temperature_K};
    int status=tp_evolve_step(ode.e,ode.c,ode.s,&sys,&x,offset+1,&h,y);
    std::cout << std::setprecision(17) << "near status=" << status << " x=" << x << " P=" << y[1] << " snaps=" << diag.knot_snaps << '\n';
    require(status==GSL_SUCCESS,"near-knot step status");
    require(x>offset,"near-knot SUCCESS must advance mass in this call");
    require(diag.knot_snaps>=1,"near-knot entry must snap");
    require(y[0]==123 && y[1]>=1e7,"near-knot state/direction");
    require(std::abs(y[1]-(1e7+gradient*(x-offset)))<=1e-12*1e7,"near-knot pressure/mass drift");
    require(std::abs(y[2]-tp.at_cgs(y[1]).temperature_K)<1e-7,"near-knot integrated T tracking");
    std::cout << "PASS near-knot\n";
}
int main(int argc,char** argv) {
    gsl_set_error_handler_off();
    try {
        require(argc==3,"usage: stepper_regression profile.csv reverse|near");
        TPProfile tp=TPProfile::load_csv(argv[1]);
        if (std::string(argv[2])=="reverse") reverse(tp);
        else if (std::string(argv[2])=="near") near_knot(tp);
        else if (std::string(argv[2])=="near-offset") near_knot(tp,1000);
        else throw std::runtime_error("unknown test");
        return 0;
    } catch(const std::exception& e) { std::cerr<<"FAIL "<<e.what()<<'\n'; return 1; }
}

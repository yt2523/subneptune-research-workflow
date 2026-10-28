// Verification probe only. Existing fitting_method unchanged; no prescribed TP.
// Build the same probe against the unchanged baseline and current source.
#include "hydro.h"
#include "EOSlist.h"
#include "parser.h"
#include <fstream>
#include <iomanip>
#include <limits>
#include <iostream>
#include <stdexcept>
double rho_eps_rel=1e-11,T_eps_rel=1e-11,ode_eps_rel0=1e-7,ode_eps_rel1=1e-10,ode_eps_rel2=1e-10,R_eps_rel=2e-5,P_eps_rel=1e-10,fit_eps_rel=1e-6;
int fit_iter=0,count_shoot=0,count_step=0; bool verbose=false;
int main(int argc,char**argv){
 gsl_set_error_handler_off();
 try{
  if(argc!=2)throw std::runtime_error("OFF probe requires one fixed fixture cfg");
  Settings options(argv[1]);options.LoadSettings();
  if(options.GetOptionDouble("input_mode")!=0 || options.GetOptionString("core_phasedgm")!="Fe_default" || options.GetOptionString("mantle_phasedgm")!="Si_default" || options.GetOptionString("hydro_phasedgm")!="water_default" || options.GetOptionString("atm_phasedgm")!="gas_default")throw std::runtime_error("OFF probe supports only frozen default-selector mode0 fixture");
  rho_eps_rel=options.GetOptionDouble("rho_eps_rel");T_eps_rel=options.GetOptionDouble("T_eps_rel");ode_eps_rel0=options.GetOptionDouble("ode_eps_rel0");ode_eps_rel1=options.GetOptionDouble("ode_eps_rel1");ode_eps_rel2=options.GetOptionDouble("ode_eps_rel2");R_eps_rel=options.GetOptionDouble("R_eps_rel");P_eps_rel=options.GetOptionDouble("P_eps_rel");fit_eps_rel=options.GetOptionDouble("fit_eps_rel");verbose=options.GetOptionBool("verbose");
  vector<PhaseDgm> components={core,mant,water,atm};
  vector<double> masses={options.GetOptionDouble("mass_of_core"),options.GetOptionDouble("mass_of_mantle"),options.GetOptionDouble("mass_of_hydro"),options.GetOptionDouble("mass_of_atm")};
  vector<double> gaps={options.GetOptionDouble("temp_jump_3"),options.GetOptionDouble("temp_jump_2"),options.GetOptionDouble("temp_jump_1"),options.GetOptionDouble("surface_temp")};
  vector<double> densities={options.GetOptionDouble("ave_rho_core"),options.GetOptionDouble("ave_rho_mantle"),options.GetOptionDouble("ave_rho_hydro"),options.GetOptionDouble("ave_rho_atm")};
  hydro* model=fitting_method(components,masses,gaps,densities,options.GetOptionDouble("P_surface"),false);
  if(!model)throw std::runtime_error("OFF solve returned null");
  if(model->getstatus()!=0||model->getsize()==0){delete model;throw std::runtime_error("OFF solve did not converge with status0");}
  const double radius=model->totalR(),mass=model->totalM();
  if(!std::isfinite(radius)||!std::isfinite(mass)||radius<=0||mass<=0){delete model;throw std::runtime_error("OFF nonfinite/invalid model");}
  const std::string output=options.GetOptionString("output_file");model->print(output,false);
  std::ofstream file(output+".off.json");file<<std::setprecision(std::numeric_limits<double>::max_digits10)<<"{\"schema_version\":1,\"status\":\"success\",\"ode_status\":"<<model->getstatus()<<",\"radius_cm\":"<<radius<<",\"mass_g\":"<<mass<<"}\n";file.close();delete model;
  if(!file)throw std::runtime_error("OFF probe JSON write failed");
  std::cout<<"OFF high-precision verification probe completed\n";return 0;
 }catch(const std::exception&error){std::cerr<<"OFF probe failure: "<<error.what()<<'\n';return 1;}
}

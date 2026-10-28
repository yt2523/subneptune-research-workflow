#include "tp_settings.h"
#include "parser.h"
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
static int n=0;
static void req(bool ok,const char* msg){++n;if(!ok)throw std::runtime_error(msg);}
template<class F>static void rejects(F f,const char* msg){bool bad=false;try{f();}catch(const std::exception&){bad=true;}req(bad,msg);}
static tp_settings::TPOptions valid(bool enabled=true,const std::string& selector="gas_fixed_mu2",int mode=0,double gas=1,double core=1,double jump=0){return tp_settings::validate(mode,core,3,0,gas,jump,0,0,selector,enabled,"\"curve.csv\"","/fixtures");}
int main(int argc,char** argv){try{req(argc==2,"directory");
 auto x=valid();req(x.enabled&&x.resolved_path=="/fixtures/curve.csv","valid enabled");
 req(!valid(false,"gas_default",3,-1,-1,1).enabled,"legacy absent retains behavior");
 rejects([]{valid(false);},"fixed selector without TP");
 rejects([]{valid(true,"gas_default");},"mixed selector");
 rejects([]{valid(true,"gas_fixed_mu2",3);},"unsupported mode");
 rejects([]{valid(true,"gas_fixed_mu2",0,0);},"zero gas");
 rejects([]{valid(true,"gas_fixed_mu2",0,-1);},"negative gas");
 rejects([]{valid(true,"gas_fixed_mu2",0,NAN);},"nan gas");
 rejects([]{valid(true,"gas_fixed_mu2",0,1,1,1);},"jump");
 rejects([]{valid(true,"gas_fixed_mu2",0,1,INFINITY);},"infinite core");
 rejects([]{tp_settings::validate(0,1e308,1e308,0,1,0,0,0,"gas_fixed_mu2",true,"\"x\"",".");},"mass sum overflow");
 for(const std::string& s:{"","\"\"","123","\"a b.csv\"","\"a\tb\"","\"broken","\"x\"junk","\"D:relative\""})rejects([&]{tp_settings::validate_raw_tp_path_value(s);},"malformed raw path");
 req(tp_settings::validate_raw_tp_path_value(" \"D:/data/p.csv\" #comment")=="D:/data/p.csv","absolute windows raw");
 req(tp_settings::resolve_relative("/cfg","/abs/x")=="/abs/x","unix absolute");
 req(tp_settings::resolve_relative("/cfg","D:/abs/x")=="D:/abs/x","drive absolute");
 std::string p=std::string(argv[1])+"/settings-acceptance.cfg";
 {std::ofstream o(p.c_str());o<<"input_mode=0\ntp_profile_file = \"curve.csv\" # note\n";}
 bool present=false;std::string raw;tp_settings::read_raw_tp_option(p,present,raw);req(present,"raw present");
 req(tp_settings::validate_raw_tp_path_value(raw)=="curve.csv","raw quoted path");
 Settings s(p.c_str());s.LoadSettings();const Settings& cs=s;req(cs.HasOption("tp_profile_file"),"const HasOption present");req(!cs.HasOption("missing"),"HasOption absent");
 {std::ofstream o(p.c_str());o<<"tp_profile_file=\"x\"\ntp_profile_file=\"y\"\n";}
 rejects([&]{tp_settings::read_raw_tp_option(p,present,raw);},"duplicate option");
 std::cout<<"Independent settings acceptance: "<<n<<" assertions passed\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}

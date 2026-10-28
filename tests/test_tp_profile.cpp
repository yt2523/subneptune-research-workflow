// Independent coordinator acceptance; builder must not edit.
#include "tp_profile.h"
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
static int checked=0;
static void require(bool p,const char* msg){++checked;if(!p)throw std::runtime_error(msg);}
static void near(double x,double y,const char* msg){require(std::isfinite(x)&&std::abs(x-y)<=1e-12*std::max(1.,std::abs(y)),msg);}
static std::string file(const std::string& dir,const std::string& text){std::string p=dir+"/acceptance.csv";std::ofstream o(p.c_str(),std::ios::binary);o<<text;o.close();return p;}
int main(int argc,char** argv){try{
 require(argc==2,"fixture directory required");std::string d=argv[1];
 TPProfile p=TPProfile::load_csv(file(d,"P_bar,T_K\n1,300\n100,500\n10000,400\n"));
 near(p.at_cgs(1e6).temperature_K,300,"outer node");
 near(p.at_cgs(1e7).temperature_K,400,"log interpolation");
 near(p.at_cgs(1e7).dT_dP_cgs,200/std::log(100.)/1e7,"cgs derivative");
 near(p.at_cgs(1e8).dT_dP_cgs,-100/std::log(100.)/1e8,"right knot");
 near(p.at_cgs(1e10).dT_dP_cgs,-100/std::log(100.)/1e10,"last knot");
 near(p.min_pressure_cgs(),1e6,"minimum unit");near(p.max_pressure_cgs(),1e10,"maximum unit");
 for(double q:std::vector<double>{0.,-1.,1e5,1e11,std::nan(""),INFINITY}){bool bad=false;try{p.at_cgs(q);}catch(const std::runtime_error&){bad=true;}require(bad,"invalid lookup must reject");}
 for(const std::string& s:std::vector<std::string>{
 "P_bar,T_K\n1,300\n1,400\n","P_bar,T_K\n2,300\n1,400\n",
 "P_bar,T_K\n0,300\n1,400\n","P_bar,T_K\n1,NaN\n2,400\n",
 "P_bar,T_K\n1,300\nInf,400\n","P_bar,T_K\n1,300\n1e308,400\n",
 "P_bar,T_K\n1,300\n2,400bad\n","P_bar,T_K\n1,300,9\n2,400\n",
 "P_bar,T_K\n1,300\n2,-1\n","P_bar,T_K\n1,300\n",
 "P,T\n1,300\n2,400\n","P_bar,T_K\n1,300\n2,\n",
 "\xEF\xBB\xBFP_bar,T_K\n1,300\n2,400\n"," P_bar,T_K\n1,300\n2,400\n"}){
 bool bad=false;try{TPProfile::load_csv(file(d,s));}catch(const std::runtime_error&){bad=true;}require(bad,"invalid input must reject");}
 TPProfile wide=TPProfile::load_csv(file(d,"P_bar,T_K\n1e-300,300\n1e290,500\n"));
 double mid=std::exp((std::log(1e-294)+std::log(1e296))/2.);
 near(wide.at_cgs(mid).temperature_K,400,"wide finite range, no ratio overflow");
 TPProfile close=TPProfile::load_csv(file(d,"P_bar,T_K\n10000000000,300\n10000000000.00001,400\n"));
 near(close.at_cgs(1e16+4).temperature_K,340,"close pressure stable log ratio");
 require(std::isfinite(close.at_cgs(1e16).dT_dP_cgs),"finite close derivative");
 TPProfile large=TPProfile::load_csv(file(d,"P_bar,T_K\n1,1\n2,1.7e308\n"));
 near(large.at_cgs(1e6).temperature_K,1,"exact first node without inf zero");
 require(std::isfinite(large.at_cgs(1.5e6).temperature_K),"finite convex interpolation");
 require(std::isfinite(large.at_cgs(1e6).dT_dP_cgs),"finite large cgs derivative");
 TPProfile drop=TPProfile::load_csv(file(d,"P_bar,T_K\n1,1e100\n2,1\n"));
 near(drop.at_cgs(2e6).temperature_K,1,"exact last node without cancellation");
 double q=std::nextafter(2e6,0.);
 long double w0=std::log1p((2000000.L-static_cast<long double>(q))/static_cast<long double>(q))/std::log(2.L);
 near(drop.at_cgs(q).temperature_K,static_cast<double>(w0*1e100L+(1.L-w0)),"near endpoint avoids subtracting large temperatures");
 TPProfile blank=TPProfile::load_csv(file(d,"P_bar,T_K\n\n1,300\n \t\r\n2,400\n"));
 near(blank.at_cgs(1e6).temperature_K,300,"blank rows permitted");
 TPProfile tiny=TPProfile::load_csv(file(d,"P_bar,T_K\n1e-310,300\n1e-300,400\n"));
 require(tiny.min_pressure_cgs()>0,"positive finite subnormal input");
 std::cout<<"Independent TP acceptance: "<<checked<<" assertions passed\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}

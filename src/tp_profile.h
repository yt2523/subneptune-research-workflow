#ifndef TP_PROFILE_H_
#define TP_PROFILE_H_

#include <string>
#include <vector>

// Prescribed gas T(P) evaluator (C++11, standard library only).
// Linear interpolation in ln(P): T(P) = T_i + b_i * ln(P / P_i) with
// b_i = (T_{i+1} - T_i) / ln(P_{i+1} / P_i). No extrapolation/clamp.

struct TPState {
    double temperature_K;   // K
    double dT_dP_cgs;       // K / (dyn cm^-2)
};

class TPProfile {
public:
    // Load a UTF-8 ASCII CSV with exact header "P_bar,T_K" and >= 2 data rows.
    // Throws std::runtime_error on any format/content error.
    static TPProfile load_csv(const std::string& path);

    // Evaluate T and dT/dP at pressure_cgs (dyn cm^-2). Endpoints inclusive;
    // throws std::runtime_error outside [min,max]. Internal knots use the
    // right (interval starting at the knot) derivative; the last node uses
    // the left interval.
    TPState at_cgs(double pressure_cgs) const;

    double min_pressure_cgs() const;
    double max_pressure_cgs() const;

private:
    TPProfile() {}  // populated by load_csv
    std::vector<double> p_cgs_;     // strictly increasing
    std::vector<double> lnp_cgs_;   // ln(p_cgs_) precomputed
    std::vector<double> t_k_;
};

#endif // TP_PROFILE_H_

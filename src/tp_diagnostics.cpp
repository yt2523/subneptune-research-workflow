#include "tp_diagnostics.h"

#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "EOSlist.h"
#include "hydro.h"
#include "tp_profile.h"

namespace {

// JSON number formatting: always max_digits10, finite required.
std::string format_double(double v) {
    if (!std::isfinite(v)) throw std::runtime_error("Non-finite double in diagnostics");
    std::ostringstream oss;
    oss << std::setprecision(std::numeric_limits<double>::max_digits10) << v;
    return oss.str();
}

// Write JSON string (no escaping needed for fixed labels).
void write_json_string(std::ostream& os, const std::string& s) {
    os << '\"';
    for (char c : s) {
        switch (c) {
            case '\\': os << "\\\\"; break;
            case '\"': os << "\\\""; break;
            default: os << c;
        }
    }
    os << '\"';
}

struct GasRow {
    double mass_g;
    double pressure_cgs;
    double temperature_K;
    double density_g_cm3;
};

// Compute actual gas rows using component mass interval boundaries and EOS pointers.
std::vector<GasRow> collect_gas_rows(hydro& model) {
    const TPDiagnostics& diag = model.tp_diagnostics();
    const double gas_base_mass = diag.gas_base_mass;
    const double total_mass = model.totalM();
    const double eps = 64.0 * std::numeric_limits<double>::epsilon();

    // Identify boundaries with tolerance.
    std::vector<int> layer_indices;
    const int size = model.getsize();
    if (size <= 0) throw std::runtime_error("hydro model has no layers");

    // Find candidate gas-side boundary: first layer whose M is within eps of gas_base_mass
    // and whose phase is Gas. Also ensure it is not a duplicated solid-side boundary.
    int gas_base_idx = -1;
    for (int i = 0; i < size; ++i) {
        const double m = model.getM(i);
        if (std::abs(m - gas_base_mass) <= eps * std::max(1.0, std::abs(gas_base_mass))) {
            const EOS* phase = model.getphase(i);
            if (phase == Gas) {
                gas_base_idx = i;
                break;
            }
        }
    }
    if (gas_base_idx < 0) throw std::runtime_error("gas_base_mass not found at Gas phase boundary");

    // Collect rows from gas_base_idx up to last layer inclusive.
    std::vector<GasRow> rows;
    for (int i = gas_base_idx; i < size; ++i) {
        const double mass = model.getM(i);
        // Validate mass range with tolerance relative to magnitudes.
        if (!(mass >= gas_base_mass - eps * std::max(1.0, std::abs(gas_base_mass)) &&
              mass <= total_mass + eps * std::max(1.0, std::abs(total_mass)))) {
            throw std::runtime_error("gas row mass outside valid interval");
        }
        if (model.getphase(i) != Gas) {
            // Allow skipped duplicated SOLID-side boundary row only if mass is within roundoff of gas_base_mass (zero-jump interface).
            if (std::abs(mass - gas_base_mass) <= eps * std::max(1.0, std::abs(gas_base_mass))) {
                continue;
            } else {
                throw std::runtime_error("Non-Gas phase inside gas mass interval");
            }
        }
        // Exclude any mass beyond total mass (should not happen).
        if (mass > total_mass + eps * std::max(1.0, std::abs(total_mass))) {
            throw std::runtime_error("gas row mass exceeds total mass");
        }

        const double p = model.getP(i);
        const double t = model.getT(i);
        const double rho = model.getrho(i);
        if (!(std::isfinite(mass) && std::isfinite(p) && std::isfinite(t) && std::isfinite(rho))) {
            throw std::runtime_error("Non-finite value in gas row");
        }
        if (p <= 0.0 || rho <= 0.0) {
            throw std::runtime_error("Non-positive pressure or density in gas row");
        }

        GasRow row;
        row.mass_g = mass;
        row.pressure_cgs = p;
        row.temperature_K = t;
        row.density_g_cm3 = rho;
        rows.push_back(row);
    }

    if (rows.empty()) throw std::runtime_error("No gas rows collected");
    return rows;
}

// Validate all required diagnostics and model state.
void validate_inputs(hydro& model, double surfaceP_cgs, double surfaceT_K) {
    const TPDiagnostics& diag = model.tp_diagnostics();
    if (!diag.enabled) throw std::runtime_error("TPD diagnostics not enabled");
    if (model.getstatus() != 0) throw std::runtime_error("hydro ode_status != 0");
    if (!diag.error.empty()) throw std::runtime_error("TPD error string non-empty");
    if (diag.corrected_fit) throw std::runtime_error("corrected_fit is true");

    if (!(std::isfinite(surfaceP_cgs) && std::isfinite(surfaceT_K))) {
        throw std::runtime_error("surface pressure/temperature not finite");
    }
    if (surfaceP_cgs <= 0.0) throw std::runtime_error("surface pressure must be positive");

    // Check required TPD fields are finite.
    const double fields[] = {
        diag.gas_pressure_min,
        diag.gas_pressure_max,
        diag.accepted_gas_pressure_max,
        diag.gas_base_pressure,
        diag.gas_base_temperature,
        diag.gas_base_mass,
        diag.fit_mass,
        diag.max_pre_projection_relative,
        diag.max_effective_relative,
        diag.max_density_relative,
        diag.fit_Ri, diag.fit_Ro,
        diag.fit_Pi, diag.fit_Po,
        diag.fit_Ti, diag.fit_To,
        diag.max_knot_pressure_projection_relative
    };
    for (double v : fields) {
        if (!std::isfinite(v)) throw std::runtime_error("Non-finite TPD field");
    }

    if (diag.gas_pressure_min <= 0.0 || diag.gas_pressure_max <= 0.0 ||
        diag.accepted_gas_pressure_max <= 0.0 || diag.gas_base_pressure <= 0.0 ||
        diag.gas_base_mass <= 0.0 || diag.fit_mass <= 0.0) {
        throw std::runtime_error("Physically positive field non-positive");
    }

    if (diag.max_pre_projection_relative < 0.0 ||
        diag.max_effective_relative < 0.0 ||
        diag.max_density_relative < 0.0 ||
        diag.max_knot_pressure_projection_relative < 0.0) {
        throw std::runtime_error("Non-negative relative field is negative");
    }
}

// Build JSON string in memory.
std::string build_json(hydro& model, const TPProfile& tp,
                       double surfaceP_cgs, double surfaceT_K,
                       const std::vector<GasRow>& gas_rows) {
    const TPDiagnostics& diag = model.tp_diagnostics();
    std::ostringstream json;
    json << std::setprecision(std::numeric_limits<double>::max_digits10);

    const double profile_min_p = tp.min_pressure_cgs();
    const double profile_max_p = tp.max_pressure_cgs();
    if (!(std::isfinite(profile_min_p) && std::isfinite(profile_max_p)) ||
        profile_min_p <= 0.0 || profile_max_p <= 0.0 || profile_min_p > profile_max_p) {
        throw std::runtime_error("Invalid TP profile pressure range");
    }

    if (gas_rows.empty()) {
        throw std::runtime_error("No gas rows collected");
    }

    double max_effective_rel = 0.0;
    double max_density_rel = 0.0;

    EOS* gas_eos = Gas;
    if (gas_eos == nullptr) {
        throw std::runtime_error("Gas EOS pointer is null");
    }

    for (const GasRow& row : gas_rows) {
        const double expected_T = tp.at_cgs(row.pressure_cgs).temperature_K;
        if (!std::isfinite(expected_T) || expected_T <= 0.0) {
            throw std::runtime_error("Invalid expected temperature in gas row");
        }

        const double expected_rho = gas_eos->density(row.pressure_cgs, expected_T, -1);
        if (!std::isfinite(expected_rho) || expected_rho <= 0.0) {
            throw std::runtime_error("Invalid expected density in gas row");
        }
        if (!(row.density_g_cm3 > 0.0) || !std::isfinite(row.density_g_cm3)) {
            throw std::runtime_error("Stored density non-positive or non-finite");
        }

        const double eff_rel = std::abs(row.temperature_K - expected_T) / std::max(1.0, std::abs(expected_T));
        if (eff_rel > max_effective_rel) max_effective_rel = eff_rel;

        const double den_rel = std::abs(expected_rho - row.density_g_cm3) / expected_rho;
        if (den_rel > max_density_rel) max_density_rel = den_rel;
    }

    const double fit_Ri = diag.fit_Ri;
    const double fit_Ro = diag.fit_Ro;
    const double fit_Pi = diag.fit_Pi;
    const double fit_Po = diag.fit_Po;
    const double fit_Ti = diag.fit_Ti;
    const double fit_To = diag.fit_To;
    const double denom_R = fit_Ri + fit_Ro;
    const double denom_P = fit_Pi + fit_Po;
    const double denom_T = fit_Ti + fit_To;
    if (denom_R == 0.0 || !std::isfinite(denom_R) ||
        denom_P == 0.0 || !std::isfinite(denom_P) ||
        denom_T == 0.0 || !std::isfinite(denom_T)) {
        throw std::runtime_error("Zero or non-finite fit residual denominator");
    }

    const double total_mass = model.totalM();
    const double total_radius = model.totalR();
    if (!(total_mass > 0.0) || !(total_radius > 0.0) ||
        !std::isfinite(total_mass) || !std::isfinite(total_radius)) {
        throw std::runtime_error("Invalid total mass or radius");
    }
    if (!(surfaceT_K > 0.0) || !std::isfinite(surfaceT_K)) {
        throw std::runtime_error("Invalid surface temperature");
    }
    if (!(diag.gas_base_temperature > 0.0) || !std::isfinite(diag.gas_base_temperature)) {
        throw std::runtime_error("Invalid gas base temperature");
    }

    auto emit_double = [&json](const char* name, double value) {
        json << "\"" << name << "\":" << format_double(value) << ",";
    };

    json << "{";
    json << "\"schema_version\":1,";
    json << "\"status\":\"success\",";
    json << "\"eos_selector\":\"gas_fixed_mu2\",";
    json << "\"mmol\":2,";
    json << "\"n\":2,";
    json << "\"pressure_unit\":\"dyn/cm2\",";
    json << "\"temperature_unit\":\"K\",";
    json << "\"mass_unit\":\"g\",";
    emit_double("outer_pressure_cgs", surfaceP_cgs);
    emit_double("outer_temperature_K", surfaceT_K);
    emit_double("profile_min_pressure_cgs", profile_min_p);
    emit_double("profile_max_pressure_cgs", profile_max_p);
    emit_double("gas_pressure_min", diag.gas_pressure_min);
    emit_double("gas_pressure_max", diag.gas_pressure_max);
    emit_double("accepted_gas_pressure_max", diag.accepted_gas_pressure_max);
    emit_double("gas_base_pressure", diag.gas_base_pressure);
    emit_double("gas_base_temperature", diag.gas_base_temperature);
    emit_double("gas_base_mass", diag.gas_base_mass);
    emit_double("fit_mass", diag.fit_mass);
    emit_double("max_pre_projection_relative", diag.max_pre_projection_relative);
    emit_double("max_effective_relative", max_effective_rel);
    emit_double("max_density_relative", max_density_rel);
    emit_double("max_knot_pressure_projection_relative", diag.max_knot_pressure_projection_relative);
    json << "\"knot_snaps\":" << diag.knot_snaps << ",";
    json << "\"ode_status\":" << model.getstatus() << ",";
    json << "\"corrected_fit\":" << (diag.corrected_fit ? "true" : "false") << ",";
    emit_double("total_mass_g", total_mass);
    emit_double("total_radius_cm", total_radius);

    json << "\"fit_raw\":{";
    emit_double("Ri", fit_Ri);
    emit_double("Ro", fit_Ro);
    emit_double("Pi", fit_Pi);
    emit_double("Po", fit_Po);
    emit_double("Ti", fit_Ti);
    emit_double("To", fit_To);
    json.seekp(-1, json.cur);
    json << "},";

    json << "\"fit_residual\":{";
    emit_double("radius", (fit_Ri - fit_Ro) / denom_R);
    emit_double("pressure", (fit_Pi - fit_Po) / denom_P);
    emit_double("temperature", (fit_Ti - fit_To) / denom_T);
    json.seekp(-1, json.cur);
    json << "},";

    json << "\"gas_rows\":[";
    for (size_t i = 0; i < gas_rows.size(); ++i) {
        const GasRow& row = gas_rows[i];
        json << "{";
        emit_double("mass_g", row.mass_g);
        emit_double("pressure_cgs", row.pressure_cgs);
        emit_double("temperature_K", row.temperature_K);
        emit_double("density_g_cm3", row.density_g_cm3);
        json.seekp(-1, json.cur);
        json << "}";
        if (i != gas_rows.size() - 1) json << ",";
    }
    json << "]";

    json << "}";
    return json.str();
}
} // namespace

void write_tp_diagnostics(const std::string& output_file, hydro& model,
                          const TPProfile& tp, double surfaceP_cgs,
                          double surfaceT_K) {
    // Remove prior sidecar first.
    remove_tp_sidecar(output_file);

    // Validate model and inputs.
    validate_inputs(model, surfaceP_cgs, surfaceT_K);

    // Collect gas rows.
    std::vector<GasRow> gas_rows = collect_gas_rows(model);
    if (gas_rows.empty()) throw std::runtime_error("No gas rows");

    // Build JSON.
    std::string json = build_json(model, tp, surfaceP_cgs, surfaceT_K, gas_rows);

    // Atomic write: write to temporary then rename.
    const std::string tmp_file = output_file + ".tp.json.tmp";
    const std::string final_file = output_file + ".tp.json";
    {
        std::ofstream out(tmp_file, std::ios::out | std::ios::trunc);
        if (!out) {
            std::remove(tmp_file.c_str());
            throw std::runtime_error("Failed to open temporary file for writing");
        }
        out << json;
        out.flush();
        if (!out.good()) {
            out.close();
            std::remove(tmp_file.c_str());
            throw std::runtime_error("Failed to write JSON to temporary file");
        }
        out.close();
        if (!out.good()) {
            std::remove(tmp_file.c_str());
            throw std::runtime_error("Failed to close temporary file");
        }
    }
    if (std::rename(tmp_file.c_str(), final_file.c_str()) != 0) {
        std::remove(tmp_file.c_str());
        throw std::runtime_error("Failed to rename temporary file to final sidecar");
    }
}

void remove_tp_sidecar(const std::string& output_file) {
    const std::string sidecar = output_file + ".tp.json";
    if (std::remove(sidecar.c_str()) != 0) {
        if (errno != ENOENT) {
            throw std::runtime_error(std::string("Failed to remove sidecar: ") + std::strerror(errno));
        }
        // ENOENT: nothing to remove, OK.
    }
}

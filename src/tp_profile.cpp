#include "tp_profile.h"

#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

// Trim whitespace (spaces, tabs) from both ends, but do NOT remove newline or carriage return.
// Only remove trailing '\r' from lines read in text mode with CRLF.
std::string trim_field(const std::string& s) {
    const char* whitespace = " \t";
    size_t first = s.find_first_not_of(whitespace);
    if (first == std::string::npos) return std::string();
    size_t last = s.find_last_not_of(whitespace);
    // Remove trailing '\r' if present (CRLF line ending)
    if (last != std::string::npos && s[last] == '\r') {
        --last;
        // After removing '\r', also trim spaces/tabs before it if any
        while (last != std::string::npos && (s[last] == ' ' || s[last] == '\t')) {
            --last;
        }
        if (last == std::string::npos) return std::string();
    }
    return s.substr(first, last - first + 1);
}

// Strictly parse a finite positive double from a trimmed string.
// Returns true on success, false on any failure.
bool parse_positive_double(const std::string& s, double& value) {
    if (s.empty()) return false;
    errno = 0;
    char* endptr = nullptr;
    value = std::strtod(s.c_str(), &endptr);
    // Reject if any characters left, no conversion, or endptr points to start.
    if (endptr != s.c_str() + s.size() || endptr == s.c_str()) return false;
    // Reject non-finite or non-positive.
    if (!std::isfinite(value) || value <= 0.0) return false;
    return true;
}

} // namespace

TPProfile TPProfile::load_csv(const std::string& path) {
    std::ifstream file(path.c_str());
    if (!file.is_open()) {
        throw std::runtime_error("TPProfile::load_csv: cannot open file: " + path);
    }

    TPProfile profile;
    std::string line;
    unsigned long long line_number = 0;

    // Read and validate header line.
    if (!std::getline(file, line)) {
        throw std::runtime_error("TPProfile::load_csv: file is empty: " + path);
    }
    ++line_number;
    // Reject BOM if present: header must start exactly with 'P'
    if (line.size() >= 3 &&
        static_cast<unsigned char>(line[0]) == 0xEF &&
        static_cast<unsigned char>(line[1]) == 0xBB &&
        static_cast<unsigned char>(line[2]) == 0xBF) {
        throw std::runtime_error("TPProfile::load_csv: BOM not allowed: " + path + " line " + std::to_string(line_number));
    }
    // Header must be exactly "P_bar,T_K" with no leading/trailing whitespace,
    // but allow trailing '\r' if present (CRLF).
    std::string header = line;
    if (!header.empty() && header.back() == '\r') {
        header.pop_back();
        // If there is a trailing '\r' and then more characters? getline reads up to '\n',
        // so the '\r' is the last char before '\n' if CRLF. So popping is enough.
    }
    // Reject any other whitespace around header: header must be exactly "P_bar,T_K".
    if (header != "P_bar,T_K") {
        throw std::runtime_error("TPProfile::load_csv: invalid header (expected 'P_bar,T_K'): " + path + " line " + std::to_string(line_number));
    }

    double prev_p_cgs = -std::numeric_limits<double>::infinity();

    // Read data lines.
    while (std::getline(file, line)) {
        ++line_number;
        // We do not ignore blank lines: they are invalid.
        // Use trim_field which handles spaces/tabs and trailing '\r' only.
        std::string trimmed_line = trim_field(line);
        if (trimmed_line.empty()) {
            // Skip blank lines.
            continue;
        }

        // Split on comma, exactly two fields required.
        size_t comma_pos = trimmed_line.find(',');
        if (comma_pos == std::string::npos) {
            throw std::runtime_error("TPProfile::load_csv: missing comma in data row: " + path + " line " + std::to_string(line_number));
        }
        std::string p_str = trim_field(trimmed_line.substr(0, comma_pos));
        std::string t_str = trim_field(trimmed_line.substr(comma_pos + 1));
        // Check for extra commas: if t_str contains comma, invalid.
        if (t_str.find(',') != std::string::npos) {
            throw std::runtime_error("TPProfile::load_csv: extra fields in data row: " + path + " line " + std::to_string(line_number));
        }

        double p_bar = 0.0;
        double t_k = 0.0;
        if (!parse_positive_double(p_str, p_bar)) {
            throw std::runtime_error("TPProfile::load_csv: invalid pressure field: " + path + " line " + std::to_string(line_number));
        }
        if (!parse_positive_double(t_str, t_k)) {
            throw std::runtime_error("TPProfile::load_csv: invalid temperature field: " + path + " line " + std::to_string(line_number));
        }

        // Convert bar to cgs: 1 bar = 1e6 dyn/cm^2.
        // Use long double to check for overflow before conversion.
        long double p_bar_ld = static_cast<long double>(p_bar);
        long double p_cgs_ld = p_bar_ld * 1.0e6L;
        if (p_cgs_ld > static_cast<long double>(std::numeric_limits<double>::max())) {
            throw std::runtime_error("TPProfile::load_csv: pressure overflow after conversion: " + path + " line " + std::to_string(line_number));
        }
        double p_cgs = static_cast<double>(p_cgs_ld);

        // Check strictly increasing.
        if (!(p_cgs > prev_p_cgs)) {
            throw std::runtime_error("TPProfile::load_csv: pressures must be strictly increasing (duplicate or descending): " + path + " line " + std::to_string(line_number));
        }

        profile.p_cgs_.push_back(p_cgs);
        profile.lnp_cgs_.push_back(std::log(p_cgs));
        profile.t_k_.push_back(t_k);
        prev_p_cgs = p_cgs;
    }

    if (profile.p_cgs_.size() < 2) {
        throw std::runtime_error("TPProfile::load_csv: need at least 2 data rows: " + path);
    }

    return profile;
}

TPState TPProfile::at_cgs(double pressure_cgs) const {
    if (!std::isfinite(pressure_cgs)) {
        throw std::runtime_error("TPProfile::at_cgs: pressure must be finite");
    }

    const double min_p = min_pressure_cgs();
    const double max_p = max_pressure_cgs();
    if (pressure_cgs < min_p || pressure_cgs > max_p) {
        throw std::runtime_error("TPProfile::at_cgs: pressure out of range [" +
                                 std::to_string(min_p) + ", " +
                                 std::to_string(max_p) + "]");
    }

    // Helper lambda (C++11 compatible) for stable log ratio.
    auto log_ratio = [](long double p1, long double p0) -> long double {
        if (p1 == p0) return 0.0L;
        long double ratio_minus_1 = (p1 - p0) / p0;
        if (std::fabs(ratio_minus_1) < 1.0e-4L) {
            return std::log1p(ratio_minus_1);
        } else {
            return std::log(p1) - std::log(p0);
        }
    };

    const size_t n = p_cgs_.size();
    size_t i;

    // Determine interval index i such that p is in [p_cgs_[i], p_cgs_[i+1]],
    // or i = n-2 for the last pressure (max_p) where p_cgs_[n-2] <= p <= p_cgs_[n-1].
    // For p == min_p, the interval is [0,1], so i=0.
    // For p == max_p, the interval is [n-2, n-1], so i=n-2.
    // For other p, upper_bound gives first element > p, so interval is (it-1, it).
    if (pressure_cgs == max_p) {
        i = n - 2;
    } else {
        std::vector<double>::const_iterator it = std::upper_bound(p_cgs_.begin(), p_cgs_.end(), pressure_cgs);
        if (it == p_cgs_.begin()) {
            // Should not happen due to range check, but for safety.
            i = 0;
        } else {
            i = static_cast<size_t>(it - p_cgs_.begin()) - 1;
        }
    }

    // Compute derivative using the selected interval.
    const long double p0 = static_cast<long double>(p_cgs_[i]);
    const long double p1 = static_cast<long double>(p_cgs_[i + 1]);
    const long double t0 = static_cast<long double>(t_k_[i]);
    const long double t1 = static_cast<long double>(t_k_[i + 1]);
    const long double ln_ratio_full = log_ratio(p1, p0);
    const long double b = (t1 - t0) / ln_ratio_full;

    // Determine node equality: if pressure_cgs equals either endpoint of the interval,
    // assign stored temperature exactly. For derivative, use the interval's derivative
    // (right derivative for internal knots, left for last node).
    long double temperature;
    long double derivative;

    if (pressure_cgs == p_cgs_[i]) {
        temperature = t_k_[i];
        derivative = b / p0;  // right derivative for internal knot, left for last
    } else if (pressure_cgs == p_cgs_[i + 1]) {
        temperature = t_k_[i + 1];
        derivative = b / p1;  // left derivative for this interval
    } else {
        // Interpolate using independent positive weights to avoid cancellation near endpoints.
        const long double p_query = static_cast<long double>(pressure_cgs);
        const long double ln_query_ratio = log_ratio(p_query, p0);
        const long double lower = log_ratio(p1, p_query) / ln_ratio_full;
        const long double upper = log_ratio(p_query, p0) / ln_ratio_full;
        temperature = t0 * lower + t1 * upper;
        derivative = b / p_query;
    }

    // Ensure results are finite and representable as double.
    if (!std::isfinite(static_cast<double>(temperature)) ||
        !std::isfinite(static_cast<double>(derivative))) {
        throw std::runtime_error("TPProfile::at_cgs: result not representable as finite double");
    }

    TPState state;
    state.temperature_K = static_cast<double>(temperature);
    state.dT_dP_cgs = static_cast<double>(derivative);
    return state;
}

double TPProfile::min_pressure_cgs() const {
    if (p_cgs_.empty()) {
        throw std::runtime_error("TPProfile: no data loaded");
    }
    return p_cgs_.front();
}

double TPProfile::max_pressure_cgs() const {
    if (p_cgs_.empty()) {
        throw std::runtime_error("TPProfile: no data loaded");
    }
    return p_cgs_.back();
}

#include "tp_settings.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace tp_settings {

namespace {

std::string trim(const std::string& s) {
    size_t first = s.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return "";
    size_t last = s.find_last_not_of(" \t\r\n");
    return s.substr(first, last - first + 1);
}

bool is_absolute_path(const std::string& p) {
    // Unix absolute path
    if (!p.empty() && p[0] == '/') return true;
    // Windows drive absolute path: e.g. C:\foo or C:/foo
    if (p.length() >= 3 && std::isalpha(static_cast<unsigned char>(p[0])) &&
        p[1] == ':' && (p[2] == '\\' || p[2] == '/')) {
        return true;
    }
    return false;
}

bool is_windows_drive_relative(const std::string& p) {
    // Reject only drive prefix without slash/backslash after colon.
    if (p.length() >= 2 && std::isalpha(static_cast<unsigned char>(p[0])) && p[1] == ':') {
        if (p.length() == 2 || (p[2] != '\\' && p[2] != '/')) {
            return true;
        }
    }
    return false;
}

} // namespace

bool tp_option_from_line(const std::string& line, std::string& raw_value) {
    raw_value.clear();
    // Trim leading whitespace and ignore comment-only lines
    size_t pos = line.find_first_not_of(" \t\r\n");
    if (pos == std::string::npos || line[pos] == '#') return false;

    // Find '=' outside of quotes (though key before '=' should not have quotes)
    size_t eq = std::string::npos;
    bool in_quote = false;
    for (size_t i = pos; i < line.size(); ++i) {
        char c = line[i];
        if (c == '"') {
            in_quote = !in_quote;
        } else if (c == '=' && !in_quote) {
            eq = i;
            break;
        } else if (c == '#' && !in_quote) {
            // comment before '=' means no assignment; ignore line
            return false;
        }
    }
    if (eq == std::string::npos) return false;

    // Extract key before '=' and trim
    std::string key = trim(line.substr(pos, eq - pos));
    if (key != "tp_profile_file") return false;

    // Extract raw value after '=' (preserve exactly, including whitespace, quotes, comments)
    raw_value = line.substr(eq + 1);
    return true;
}

void read_raw_tp_option(const std::string& cfg_path, bool& present,
                        std::string& raw_value) {
    present = false;
    raw_value.clear();
    std::ifstream file(cfg_path.c_str());
    if (!file) {
        throw std::runtime_error("Error opening settings file.");
    }
    std::string line;
    while (std::getline(file, line)) {
        std::string val;
        if (tp_option_from_line(line, val)) {
            if (present) {
                throw std::runtime_error("Duplicate tp_profile_file option.");
            }
            present = true;
            raw_value = val;
        }
    }
}

std::string validate_raw_tp_path_value(const std::string& raw_value) {
    std::string trimmed = trim(raw_value);
    if (trimmed.empty()) {
        throw std::runtime_error("tp_profile_file value is empty.");
    }

    // Check for comments: '#' outside quotes truncates the value
    bool in_quote = false;
    for (size_t i = 0; i < trimmed.size(); ++i) {
        char c = trimmed[i];
        if (c == '"') {
            in_quote = !in_quote;
        } else if (c == '#' && !in_quote) {
            trimmed = trimmed.substr(0, i);
            trimmed = trim(trimmed);
            break;
        }
    }

    // Must be a quoted string: starts and ends with double quote
    if (trimmed.size() < 2 || trimmed[0] != '"' || trimmed[trimmed.size()-1] != '"') {
        throw std::runtime_error("tp_profile_file must be a quoted string.");
    }

    std::string inner = trimmed.substr(1, trimmed.size() - 2);

    // Reject any whitespace inside the quoted path
    for (size_t i = 0; i < inner.size(); ++i) {
        if (std::isspace(static_cast<unsigned char>(inner[i]))) {
            throw std::runtime_error("Whitespace not allowed inside quoted tp_profile_file path.");
        }
    }

    // Reject '#' inside the quoted path (v1 restriction)
    if (inner.find('#') != std::string::npos) {
        throw std::runtime_error("Hash character not allowed inside tp_profile_file path in v1.");
    }

    // Reject unbalanced quotes: if there is an extra quote inside, it would have ended the string earlier;
    // but we also check that there are exactly two quotes (start and end) and no embedded quotes.
    if (inner.find('"') != std::string::npos) {
        throw std::runtime_error("Unbalanced quotes in tp_profile_file value.");
    }

    if (inner.empty()) {
        throw std::runtime_error("tp_profile_file path is empty.");
    }

    // Windows drive relative path rejected explicitly
    if (is_windows_drive_relative(inner)) {
        throw std::runtime_error("Windows drive-relative paths are not supported for tp_profile_file.");
    }

    return inner;
}

std::string resolve_relative(const std::string& cfg_dir, const std::string& path) {
    if (is_absolute_path(path)) {
        return path;
    }
    // Reject Windows UNC paths (starting with two backslashes)
    if (path.size() >= 2 && path[0] == char(92) && path[1] == char(92)) {
        throw std::runtime_error("UNC paths are not supported.");
    }
    if (cfg_dir.empty() || cfg_dir == ".") {
        return path;
    }
    if (cfg_dir[cfg_dir.size()-1] == '/') {
        return cfg_dir + path;
    }
    return cfg_dir + "/" + path;
}

std::string dirname_of(const std::string& cfg_path) {
    size_t pos = cfg_path.find_last_of("/\\");
    if (pos == std::string::npos) {
        return ".";
    }
    if (pos == 0) {
        // Root directory
        return "/";
    }
    return cfg_path.substr(0, pos);
}

TPOptions validate(int mode,
                   double mass_core, double mass_mantle,
                   double mass_hydro, double mass_atm,
                   double jump_atm_hydro, double jump_hydro_mantle,
                   double jump_mantle_core,
                   const std::string& atm_phasedgm,
                   bool has_tp_option,
                   const std::string& raw_tp_value,
                   const std::string& cfg_dir) {
    // If has_tp_option is false, check if atm_phasedgm is gas_fixed_mu2 (must have TP profile)
    if (!has_tp_option) {
        if (atm_phasedgm == "gas_fixed_mu2") {
            throw std::runtime_error("tp_profile_file required when atm_phasedgm is gas_fixed_mu2.");
        }
        return TPOptions(false, "");
    }

    // TP profile present: require mode 0
    if (mode != 0) {
        throw std::runtime_error("tp_profile_file can only be used with input_mode=0.");
    }
    // Require atmosphere selector gas_fixed_mu2
    if (atm_phasedgm != "gas_fixed_mu2") {
        throw std::runtime_error("tp_profile_file requires atm_phasedgm=gas_fixed_mu2.");
    }

    // Validate mass values: individual finite nonnegative
    double masses[4] = {mass_core, mass_mantle, mass_hydro, mass_atm};
    for (int i = 0; i < 4; ++i) {
        if (!std::isfinite(masses[i]) || masses[i] < 0.0) {
            throw std::runtime_error("Mass values must be finite and nonnegative.");
        }
    }
    // Positive gas total (mass_atm)
    if (mass_atm <= 0.0) {
        throw std::runtime_error("mass_of_atm must be positive when using a TP profile.");
    }
    // Non-gas mass sum must be finite and positive (individual finite may overflow when summed)
    double non_gas_total = mass_core + mass_mantle + mass_hydro;
    if (!std::isfinite(non_gas_total)) {
        throw std::runtime_error("Non-gas mass sum overflow.");
    }
    if (non_gas_total <= 0.0) {
        throw std::runtime_error("Non-gas mass total must be positive when using a TP profile.");
    }
    // Full mass sum (non-gas + gas) must be finite (individual finite may overflow when summed)
    double full_mass_total = non_gas_total + mass_atm;
    if (!std::isfinite(full_mass_total)) {
        throw std::runtime_error("Full mass sum overflow.");
    }

    // Exactly three jumps zero
    double jumps[3] = {jump_atm_hydro, jump_hydro_mantle, jump_mantle_core};
    int zero_count = 0;
    for (int i = 0; i < 3; ++i) {
        if (jumps[i] == 0.0) {
            zero_count++;
        }
    }
    if (zero_count != 3) {
        throw std::runtime_error("Exactly three temperature jumps must be zero when using a TP profile.");
    }

    // Validate and resolve path
    std::string path = validate_raw_tp_path_value(raw_tp_value);
    std::string resolved = resolve_relative(cfg_dir, path);

    // Ideally we would also check that the file exists/readable, but that will be done in main.
    return TPOptions(true, resolved);
}

} // namespace tp_settings

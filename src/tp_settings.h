#ifndef TP_SETTINGS_H_
#define TP_SETTINGS_H_

#include <string>

namespace tp_settings {

// Immutable validated TP options.
struct TPOptions {
    bool enabled;
    std::string resolved_path;   // resolved profile path (empty when disabled)
    TPOptions() : enabled(false), resolved_path("") {}
    TPOptions(bool e, const std::string& p) : enabled(e), resolved_path(p) {}
};

// Extract the raw (pre-normalization) tp_profile_file value from one raw cfg
// line. Returns true and sets raw_value when the line is a tp_profile_file
// assignment (key may have surrounding whitespace; value kept raw after '=').
// Returns false for blank/comment lines and other keys.
bool tp_option_from_line(const std::string& line, std::string& raw_value);

// Read a cfg file and report whether tp_profile_file is present and its raw
// (unstripped) value, for whitespace validation before the legacy parser.
void read_raw_tp_option(const std::string& cfg_path, bool& present,
                        std::string& raw_value);

// Validate a raw tp_profile_file value: trims surrounding whitespace and an
// optional pair of double quotes; rejects empty values and any whitespace
// inside a (quoted) path. Returns the trimmed, un-quoted path.
std::string validate_raw_tp_path_value(const std::string& raw_value);

// Resolve a profile path relative to cfg_dir (leading '/' left unchanged).
std::string resolve_relative(const std::string& cfg_dir, const std::string& path);

// Directory portion of a config path ("." when none).
std::string dirname_of(const std::string& cfg_path);

// Full standalone configuration validation. Throws std::runtime_error with a
// useful message on any invalid combination. When tp_profile_file is absent,
// returns disabled options and never resolves/reads a profile.
TPOptions validate(int mode,
                   double mass_core, double mass_mantle,
                   double mass_hydro, double mass_atm,
                   double jump_atm_hydro, double jump_hydro_mantle,
                   double jump_mantle_core,
                   const std::string& atm_phasedgm,
                   bool has_tp_option,
                   const std::string& raw_tp_value,
                   const std::string& cfg_dir);

} // namespace tp_settings

#endif // TP_SETTINGS_H_

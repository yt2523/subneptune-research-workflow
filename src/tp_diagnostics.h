#ifndef TP_DIAGNOSTICS_H_
#define TP_DIAGNOSTICS_H_

#include <string>

class hydro;
class TPProfile;

// Write tp_diagnostics JSON sidecar. Throws std::runtime_error on invalid
// model/diagnostics or I/O errors. Removes any prior sidecar first.
void write_tp_diagnostics(const std::string& output_file, hydro& model,
                          const TPProfile& tp, double surfaceP_cgs,
                          double surfaceT_K);

// Remove the generated .tp.json sidecar. ENOENT is ignored; other errors throw.
void remove_tp_sidecar(const std::string& output_file);

#endif // TP_DIAGNOSTICS_H_

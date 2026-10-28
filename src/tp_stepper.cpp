#include <algorithm>
#include <cmath>
#include <limits>
#include <gsl/gsl_errno.h>
#include <gsl/gsl_odeiv2.h>
#include "hydro.h"

int tp_evolve_step(gsl_odeiv2_evolve* e, gsl_odeiv2_control* c, gsl_odeiv2_step* s,
                   gsl_odeiv2_system* sys, double* m, double mmax, double* h, double y[])
{
    mass_params* params = static_cast<mass_params*>(sys->params);
    if (params == nullptr) {
        return gsl_odeiv2_evolve_apply(e, c, s, sys, m, mmax, h, y);
    }

    if (!(params->tp != nullptr && params->tp_gas)) {
        return gsl_odeiv2_evolve_apply(e, c, s, sys, m, mmax, h, y);
    }

    const TPProfile* tp = params->tp;
    TPDiagnostics* diag = params->tp_diagnostics;

    if (!std::isfinite(*m) || !std::isfinite(*h) || *h <= 0.0) {
        if (diag) diag->error = "Invalid initial step or mass";
        return GSL_EBADFUNC;
    }
    if (!std::isfinite(y[0]) || !std::isfinite(y[1]) || !std::isfinite(y[2])) {
        if (diag) diag->error = "Non-finite initial state";
        return GSL_EBADFUNC;
    }

    double dydx[3];
    int rhs_status = sys->function(*m, y, dydx, sys->params);
    if (rhs_status != GSL_SUCCESS) {
        if (diag && diag->error.empty()) {
            diag->error = "RHS evaluation failed in tp_evolve_step";
        }
        return rhs_status;
    }
    double dPdm = dydx[1];
    if (!std::isfinite(dPdm)) {
        if (diag) diag->error = "Non-finite dP/dm";
        return GSL_EBADFUNC;
    }

    const std::vector<double>& pknots = tp->pressures_cgs();
    if (pknots.empty()) {
        if (diag) diag->error = "Empty pressure knot list";
        return GSL_EBADFUNC;
    }

    const double direction = (dPdm > 0.0) ? 1.0 : ((dPdm < 0.0) ? -1.0 : 0.0);
    if (direction == 0.0) {
        return gsl_odeiv2_evolve_apply(e, c, s, sys, m, mmax, h, y);
    }

    double currentP = y[1];
    const double eps = 64.0 * std::numeric_limits<double>::epsilon();

    // Find next strict knot in direction
    int target_idx = -1;
    double target_knot = 0.0;
    if (direction > 0.0) {
        for (size_t i = 0; i < pknots.size(); ++i) {
            if (pknots[i] > currentP) {
                target_idx = static_cast<int>(i);
                target_knot = pknots[i];
                break;
            }
        }
    } else {
        for (int i = static_cast<int>(pknots.size()) - 1; i >= 0; --i) {
            if (pknots[i] < currentP) {
                target_idx = i;
                target_knot = pknots[i];
                break;
            }
        }
    }

    if (target_idx == -1) {
        return gsl_odeiv2_evolve_apply(e, c, s, sys, m, mmax, h, y);
    }

    // Check if current pressure is already within roundoff of target knot
    double scale = std::max(1.0, std::abs(currentP));
    if (std::abs(currentP - target_knot) <= eps * scale) {
        // Snap to knot
        double oldP = y[1];
        y[1] = target_knot;
        currentP = y[1];
        if (diag) {
            double relerr = std::abs((oldP - target_knot) / (target_knot != 0.0 ? target_knot : 1.0));
            diag->max_knot_pressure_projection_relative = std::max(diag->max_knot_pressure_projection_relative, relerr);
            diag->knot_snaps++;
        }
        gsl_odeiv2_step_reset(s);
        gsl_odeiv2_evolve_reset(e);

        // Find next strict node from updated P in direction
        int new_target_idx = -1;
        double new_target_knot = 0.0;
        if (direction > 0.0) {
            for (size_t i = 0; i < pknots.size(); ++i) {
                if (pknots[i] > currentP) {
                    new_target_idx = static_cast<int>(i);
                    new_target_knot = pknots[i];
                    break;
                }
            }
        } else {
            for (int i = static_cast<int>(pknots.size()) - 1; i >= 0; --i) {
                if (pknots[i] < currentP) {
                    new_target_idx = i;
                    new_target_knot = pknots[i];
                    break;
                }
            }
        }
        if (new_target_idx == -1) {
            return gsl_odeiv2_evolve_apply(e, c, s, sys, m, mmax, h, y);
        }
        target_idx = new_target_idx;
        target_knot = new_target_knot;
        // Fall through to subsequent pressure_gap/max_dm logic
    }
    const double pressure_gap = std::abs(target_knot - currentP);
    const double abs_dPdm = std::abs(dPdm);
    if (abs_dPdm <= 0.0) {
        return gsl_odeiv2_evolve_apply(e, c, s, sys, m, mmax, h, y);
    }

    const double max_dm = 0.5 * pressure_gap / abs_dPdm;
    if (!std::isfinite(max_dm) || max_dm <= 0.0) {
        if (diag) diag->error = "Invalid step cap computed";
        return GSL_EBADFUNC;
    }

    double m_save = *m;
    double y_save[3] = { y[0], y[1], y[2] };
    double h_save = *h;

    double h_try = std::min(h_save, max_dm);
    if (!std::isfinite(h_try) || h_try <= 0.0) {
        if (diag) diag->error = "Invalid capped step size";
        return GSL_EBADFUNC;
    }

    const int max_retries = 32;
    int retry_count = 0;

    while (true) {
        *h = h_try;
        int status = gsl_odeiv2_evolve_apply(e, c, s, sys, m, mmax, h, y);
        if (status != GSL_SUCCESS) {
            *m = m_save;
            y[0] = y_save[0];
            y[1] = y_save[1];
            y[2] = y_save[2];
            *h = h_save;
            gsl_odeiv2_step_reset(s);
            gsl_odeiv2_evolve_reset(e);
            if (diag && diag->error.empty()) diag->error = "GSL step failed in tp_evolve_step";
            return status;
        }

        double newP = y[1];
        if (!std::isfinite(newP)) {
            *m = m_save;
            y[0] = y_save[0];
            y[1] = y_save[1];
            y[2] = y_save[2];
            *h = h_save;
            gsl_odeiv2_step_reset(s);
            gsl_odeiv2_evolve_reset(e);
            if (diag) diag->error = "Non-finite state after step";
            return GSL_EBADFUNC;
        }

        // Check for overshoot beyond roundoff tolerance
        bool overshoot = (direction > 0.0 && newP > target_knot + eps * std::max(1.0, std::abs(target_knot))) ||
                         (direction < 0.0 && newP < target_knot - eps * std::max(1.0, std::abs(target_knot)));

        if (overshoot) {
            if (retry_count >= max_retries) {
                *m = m_save;
                y[0] = y_save[0];
                y[1] = y_save[1];
                y[2] = y_save[2];
                *h = h_save;
                gsl_odeiv2_step_reset(s);
                gsl_odeiv2_evolve_reset(e);
                if (diag) diag->error = "Maximum retries exceeded in tp_evolve_step";
                return GSL_EBADFUNC;
            }

            double actual_dm = *m - m_save;
            if (actual_dm <= 0.0 || !std::isfinite(actual_dm)) {
                *m = m_save;
                y[0] = y_save[0];
                y[1] = y_save[1];
                y[2] = y_save[2];
                *h = h_save;
                gsl_odeiv2_step_reset(s);
                gsl_odeiv2_evolve_reset(e);
                if (diag) diag->error = "Non-advancing or invalid step";
                return GSL_EBADFUNC;
            }

            // Rollback to saved state
            *m = m_save;
            y[0] = y_save[0];
            y[1] = y_save[1];
            y[2] = y_save[2];
            gsl_odeiv2_step_reset(s);
            gsl_odeiv2_evolve_reset(e);

            h_try = actual_dm * 0.5;
            if (!std::isfinite(h_try) || h_try <= 0.0) {
                *h = h_save;
                if (diag) diag->error = "Invalid halved step";
                return GSL_EBADFUNC;
            }
            retry_count++;
            continue;
        }

        // Step accepted (no overshoot beyond tolerance)
        // Check if new pressure is within roundoff of any knot (could be target or another)
        double newP_scale = std::max(1.0, std::abs(newP));
        for (size_t i = 0; i < pknots.size(); ++i) {
            if (std::abs(newP - pknots[i]) <= eps * newP_scale) {
                double oldP = y[1];
                y[1] = pknots[i];
                if (diag) {
                    double relerr = std::abs((oldP - pknots[i]) / (pknots[i] != 0.0 ? pknots[i] : 1.0));
                    diag->max_knot_pressure_projection_relative = std::max(diag->max_knot_pressure_projection_relative, relerr);
                    diag->knot_snaps++;
                }
                gsl_odeiv2_step_reset(s);
                gsl_odeiv2_evolve_reset(e);
                break;
            }
        }
        return GSL_SUCCESS;
    }
}

"""Verification-only bracketed inversion using existing SciPy; no physical solver."""
import math
from scipy.optimize import brentq

class RecoveryBudgetExhausted(RuntimeError):
    """No extra radius callback is allowed after the declared search budget."""

class _Reached(Exception):
    pass

def recover(radius_function, lower, upper, target, *, radius_rtol, fraction_width,
            max_new_evaluations, xtol=1e-8, rtol=1e-12, maxiter=12):
    if not math.isfinite(target) or target <= 0:
        raise ValueError('target must be finite and positive')
    if radius_rtol <= 0 or fraction_width <= 0 or max_new_evaluations < 0:
        raise ValueError('invalid recovery tolerances or budget')
    def entry(point, coordinate=None):
        f=float(point['gas_fraction']);radius=float(point['radius_cm'])
        if not (math.isfinite(f) and 0<f<1 and math.isfinite(radius) and radius>0):
            raise ValueError('fraction/radius must be finite, positive and in range')
        result=dict(point);result.update(gas_fraction=f,radius_cm=radius,
            residual=(radius-target)/target,x=math.log(f) if coordinate is None else coordinate)
        return result
    lo,hi=entry(lower),entry(upper)
    if lo['gas_fraction']>=hi['gas_fraction']:
        raise ValueError('fraction bracket must be ordered')
    if lo['residual']*hi['residual']>0:
        raise ValueError('endpoints do not bracket target; this does not rule out interior roots')
    initial_x=(lo['x'],hi['x']);pool={lo['x'].hex():lo,hi['x'].hex():hi}
    used=0;cleanup=0;optimizer_status='not_started'
    def best():
        return min((p for p in pool.values() if lo['x']<=p['x']<=hi['x']),key=lambda p:abs(p['residual']))
    def ready():
        return abs(best()['residual'])<=radius_rtol and hi['gas_fraction']-lo['gas_fraction']<=fraction_width
    def answer():
        return dict(converged=True,candidate=dict(best()),lower=dict(lo),upper=dict(hi),
            fraction_width=hi['gas_fraction']-lo['gas_fraction'],new_evaluations=used,
            cleanup_evaluations=cleanup,optimizer_status=optimizer_status,
            acceptance_reason='actual_radius_and_signed_bracket',unique_root_proven=False)
    def sample(x):
        nonlocal lo,hi,used
        x=float(x);key=x.hex()
        if key in pool:
            point=pool[key]
        else:
            if used>=max_new_evaluations:
                raise RecoveryBudgetExhausted('fixed search evaluation budget exhausted')
            used+=1
            f=math.exp(x);point=entry(radius_function(f),x)
            if point['gas_fraction']!=f:
                raise ValueError('returned fraction differs from requested fraction')
            pool[key]=point
        # Only actual evaluated points may tighten the signed bracket.
        if lo['x']<x<hi['x']:
            if lo['residual']*point['residual']<=0:hi=point
            else:lo=point
        if ready():raise _Reached()
        return point['residual']
    if ready():return answer()
    try:
        _,info=brentq(sample,*initial_x,xtol=xtol,rtol=rtol,maxiter=maxiter,
                      full_output=True,disp=False)
        optimizer_status='brent_converged' if info.converged else 'brent_iteration_limit'
    except _Reached:
        optimizer_status='stopped_on_verified_criteria';return answer()
    # Library convergence alone cannot certify the separately required bracket width.
    while not ready():
        midpoint=(lo['x']+hi['x'])/2
        if midpoint==lo['x'] or midpoint==hi['x']:
            raise RuntimeError('floating-point bracket cannot shrink to required criteria')
        cleanup+=1
        try:sample(midpoint)
        except _Reached:break
    return answer()

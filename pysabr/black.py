import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize


def lognormal_call(k, f, t, v, r, cp='call'):
    """Compute an option premium using a lognormal vol."""
    d1 = (np.log(f/k) + v**2 * t/2) / (v * t**0.5)
    d2 = d1 - v * t**0.5
    if cp == 'call':
        pv = np.exp(-r*t) * (f * norm.cdf(d1) - k * norm.cdf(d2))
    elif cp == 'put':
        pv = np.exp(-r*t) * (-f * norm.cdf(-d1) + k * norm.cdf(-d2))
    else:
        pv = 0
    return pv


def shifted_lognormal_call(k, f, s, t, v, r, cp='call'):
    """Compute an option premium using a shifted-lognormal vol."""
    return lognormal_call(k+s, f+s, t, v, r, cp)


def normal_call(k, f, t, v, r, cp='call'):
    """Compute the premium for a call or put option using a normal vol."""
    d1 = (f - k) / (v * t**0.5)
    cp_sign = {'call': 1., 'put': -1.}[cp]
    pv = np.exp(-r*t) * (
        cp_sign * (f - k) * norm.cdf(cp_sign * d1) +
        v * (t / (2 * np.pi))**0.5 * np.exp(-d1**2 / 2))
    return pv


def normal_to_shifted_lognormal(k, f, s, t, v_n):
    """Convert a normal vol for a given strike to a shifted lognormal vol."""
    n = 1e2  # Plays an important role in the optimizer convergence.
    target_premium = n * normal_call(k, f, t, v_n, 0.)
    # Simple first guess:
    v_sln_0 = v_n / (f + s)
    # Hagan's formula first guess:
    # v_sln_0 = hagan_normal_to_lognormal(k, f, s, t, v_n)

    def premium_square_error(v_sln):
        premium = n * shifted_lognormal_call(k, f, s, t, v_sln, 0.)
        return (premium - target_premium) ** 2

    res = minimize(
            fun=premium_square_error,
            x0=v_sln_0,
            jac=None,
            options={'gtol': 1e-8,
                     'eps': 1e-9,
                     'maxiter': 10,
                     'disp': False},
            method='CG'
    )
    return res.x[0]


def hagan_normal_to_lognormal(k, f, s, t, v_n):
    """
    Convert N vol to SLN using Hagan's 2002 paper formula (B.63).

    Warning: this function was initially implemented for performance gains, but
    its current implementation is actually very slow. For this reason it won't
    be used as a first guess in the normal_to_shifted_lognormal function.
    """
    k = k + s
    f = f + s
    # Handle the ATM K=F case
    if abs(np.log(f/k)) <= 1e-8:
        factor = k
    else:
        factor = (f - k) / np.log(f/k)
    p = [
        factor * (-1/24) * t,
        0.,
        factor,
        -v_n
    ]
    roots = np.roots(p)
    roots_real = np.extract(np.isreal(roots), np.real(roots))
    v_sln_0 = v_n / f
    i_min = np.argmin(np.abs(roots_real - v_sln_0))
    return roots_real[i_min]


def shifted_lognormal_to_normal(k, f, s, t, v_sln):
    """Convert a normal vol for a given strike to a shifted lognormal vol."""
    target_premium = shifted_lognormal_call(k, f, s, t, v_sln, 0.)
    v_n_0 = v_sln * (f + s)

    def premium_square_error(v_n):
        premium = normal_call(k, f, t, v_n, 0.)
        return 1e5 * (premium - target_premium) ** 2

    res = minimize(fun=premium_square_error, x0=v_n_0, method='BFGS')
    return res.x[0]

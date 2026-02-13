import numpy as np
from hdr.constants import Constants

def neel_relaxation_time(tau0: float, K: float, V: float, T: float) -> float:
    """
    Calculate Neel relaxation time (Rosensweig, Eq. 11/12a).
    tau_N = tau0 * (sqrt(pi) / 2) * exp(Gamma) / Gamma^(1/2)
    where Gamma = K*V / (kB*T)
    """
    if T == 0:
        return float('inf')
    gamma = (K * V) / (Constants.kB * T)
    if gamma == 0:
        return tau0
    return tau0 * (np.sqrt(np.pi) / 2.0) * np.exp(gamma) / np.sqrt(gamma)

def brown_relaxation_time(viscosity: float, V_hydro: float, T: float) -> float:
    """
    Calculate Brownian relaxation time.
    tau_B = (3 * viscosity * V_hydro) / (kB * T)
    """
    if T == 0:
        return float('inf')
    return (3 * viscosity * V_hydro) / (Constants.kB * T)

def effective_relaxation_time(tau_N: float, tau_B: float) -> float:
    """
    Calculate effective relaxation time.
    tau_eff = (tau_N * tau_B) / (tau_N + tau_B)
    """
    if tau_N == 0 or tau_B == 0:
        return 0.0
    return (tau_N * tau_B) / (tau_N + tau_B)

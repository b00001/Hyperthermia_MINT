import numpy as np
from config import Constants

def neel_relaxation_time(tau0: float, K: float, V: float, T: float) -> float:
    """
    Calculate Neel relaxation time.
    tau_N = tau0 * exp(K*V / (kB*T))
    """
    if T == 0:
        return float('inf')
    kv_kbt = (K * V) / (Constants.kB * T)
    return tau0 * np.exp(kv_kbt)

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

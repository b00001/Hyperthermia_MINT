import numpy as np
from hdr.constants import Constants

def calculate_effective_field(
    t: float, 
    m_vector: np.ndarray, 
    H_ext: np.ndarray, 
    H_dip: np.ndarray, 
    anisotropy_axis: np.ndarray, 
    K: float, 
    Ms: float,
    alpha: float,
    V: float,
    T: float,
    dt: float,
    gamma: float
) -> np.ndarray:
    """
    Calculate the total effective magnetic field H_eff for the stochastic LLG equation.
    H_eff = H_ext(t) + H_ani + H_dip + H_th
    
    Args:
        t: Current time [s]
        m_vector: Normalized magnetization vector (3,)
        H_ext: External field vector [A/m] (3,)
        H_dip: Dipolar field vector [A/m] (3,)
        anisotropy_axis: Unit vector of easy axis (3,)
        K: Anisotropy constant [J/m^3]
        Ms: Saturation magnetization [A/m]
        alpha: Damping parameter
        V: Particle volume [m^3]
        T: Temperature [K]
        dt: Time step [s]
        gamma: Gyromagnetic ratio [rad/(s*T)] (Used for H_th variance scaling)
        
    Returns:
        H_eff: Total effective field [A/m]
    """
    # 1. Anisotropy Field
    # H_ani = (2K / (mu0 * Ms)) * (m . k) * k
    # Note: mu0 is in the denominator if defined as field H. 
    # Standard derivation: E = - K (m.k)^2 * V  (or sin^2 depending on convention)
    # Field H = -(1/mu0) dE/dM
    # M = Ms * m_vector
    # Resulting H_ani = (2 * K / (mu0 * Ms)) * (m_vector . k) * k
    
    dot_prod = np.dot(m_vector, anisotropy_axis)
    H_ani_mag = (2.0 * K) / (Constants.mu0 * Ms)
    H_ani = H_ani_mag * dot_prod * anisotropy_axis
    
    # 2. Thermal Field (Stochastic)
    # Variance of each component <H_th_i^2> = (2 * alpha * kB * T) / (gamma * mu0 * Ms * V * dt)
    # (assuming 1/(1+alpha^2) is handled in the integrator or consistent with Ito/Stratonovich choice)
    # We use the standard micromagnetic implementation form.
    if T > 0 and dt > 0:
        variance_numerator = 2.0 * alpha * Constants.kB * T
        variance_denominator = gamma * Constants.mu0 * Ms * V * dt
        sigma_th = np.sqrt(variance_numerator / variance_denominator)
        H_th = np.random.normal(scale=sigma_th, size=3)
    else:
        H_th = np.zeros(3)
        
    # Total Effective Field
    H_eff = H_ext + H_ani + H_dip + H_th
    return H_eff

def solve_llg_step(
    m_old: np.ndarray, 
    H_eff: np.ndarray, 
    gamma: float, 
    alpha: float, 
    dt: float
) -> np.ndarray:
    """
    Integrate the LLG equation for one time step using Heun's method (Predictor-Corrector) 
    or a simplified Euler method for small dt. 
    Using Euler here for consistency with the requested level of complexity unless specified otherwise.
    
    dm/dt = -gamma/(1+alpha^2) * [ m x H_eff + alpha * m x (m x H_eff) ]
    
    Args:
        m_old: Previous magnetization orientation (3,)
        H_eff: Effective field (3,)
        gamma: Gyromagnetic ratio
        alpha: Damping
        dt: Time step
        
    Returns:
        m_new: New magnetization orientation (normalized)
    """
    
    # LLG Derivative Calculation
    def llg_derivative(m, H):
        m_cross_H = np.cross(m, H)
        m_cross_m_cross_H = np.cross(m, m_cross_H)
        prefactor = -gamma / (1.0 + alpha**2)
        return prefactor * (m_cross_H + alpha * m_cross_m_cross_H)

    # Euler Step
    dmdt = llg_derivative(m_old, H_eff)
    m_new = m_old + dmdt * dt
    
    # Renormalize
    norm = np.linalg.norm(m_new)
    if norm > 0:
        m_new /= norm
        
    return m_new

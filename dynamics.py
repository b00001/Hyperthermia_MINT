import numpy as np
from config import Constants

def llg_equation(m_dir: np.ndarray, H_eff: np.ndarray, gamma: float, alpha: float) -> np.ndarray:
    """
    Landau-Lifshitz-Gilbert (LLG) equation derivative.
    dm/dt = -gamma/(1+alpha^2) * [ (m x H_eff) + alpha * m x (m x H_eff) ]
    
    Args:
        m_dir: (3,) Normalized magnetization vector
        H_eff: (3,) Effective magnetic field vector
        gamma: Gyromagnetic ratio
        alpha: Damping parameter
        
    Returns:
        dm_dt: (3,) derivative vector
    """
    # Precompute cross products
    m_cross_H = np.cross(m_dir, H_eff)
    m_cross_m_cross_H = np.cross(m_dir, m_cross_H)
    
    prefactor = -gamma / (1.0 + alpha**2)
    
    dmdt = prefactor * (m_cross_H + alpha * m_cross_m_cross_H)
    return dmdt

def stochastic_thermal_field(alpha: float, volume: float, T: float, dt: float, Ms: float) -> np.ndarray:
    """
    Calculate stochastic thermal field vector H_th for integration steps.
    Standard deviation sigma = sqrt( (2 * alpha * kB * T) / (gamma * Ms * V * dt) )
    (Note: The exact formulation depends on the interpretation of the stochastic calculus (Stratonovich vs Ito))
    Here effectively adding a random field component.
    """
    if T <= 0:
        return np.zeros(3)
        
    # Gamma is usually needed here too, but simplistically assuming normalized later or handled by caller context.
    # A common form for Langevin dynamics H_fluc variance:
    # <H_i(t) H_j(t')> = (2 alpha k_B T / (gamma mu0 M_s V)) * delta_ij * delta(t-t') 
    
    # We will return a placeholder random vector scaled appropriately in the loop if needed.
    # For now, return a standard normal vector to be scaled outside.
    return np.random.normal(size=3)

# --- Brownian Dynamics ---

def calculate_translational_gamma(viscosity: float, diameter: float) -> float:
    """
    Calculate translational drag coefficient gamma_t = 3 * pi * eta * d
    """
    return 3.0 * np.pi * viscosity * diameter

def calculate_rotational_gamma(viscosity: float, diameter: float) -> float:
    """
    Calculate rotational drag coefficient gamma_r = pi * eta * d^3
    """
    return np.pi * viscosity * (diameter ** 3)

def calculate_translational_displacement(force: np.ndarray, dt: float, gamma_t: float, T: float) -> np.ndarray:
    """
    Calculate displacement dr for one time step using Overdamped Langevin dynamics.
    dr = (F / gamma_t) * dt + sqrt(2 * kB * T * dt / gamma_t) * xi
    
    Args:
        force: (3,) Force vector [N]
        dt: Time step [s]
        gamma_t: Translational drag coefficient [kg/s]
        T: Temperature [K]
        
    Returns:
        dr: (3,) Displacement vector [m]
    """
    # Deterministic drift
    drift = (force / gamma_t) * dt
    
    # Stochastic diffusion
    if T > 0:
        # D_t = k_B * T / gamma_t
        # sigma = sqrt(2 * D_t * dt) = sqrt(2 * k_B * T * dt / gamma_t)
        sigma = np.sqrt(2.0 * Constants.kB * T * dt / gamma_t)
        stochastic = np.random.normal(scale=sigma, size=3)
    else:
        stochastic = np.zeros(3)
        
    return drift + stochastic

def calculate_rotational_update(orientation: np.ndarray, torque: np.ndarray, dt: float, gamma_r: float, T: float) -> np.ndarray:
    """
    Calculate new orientation n(t+dt) using rigid body rotation.
    n(t+dt) = n(t) + (omega x n(t)) * dt
    omega = (torque / gamma_r) + xi_rot
    
    Args:
        orientation: (3,) Unit vector defining particle orientation (and magnetization)
        torque: (3,) Torque vector [N*m]
        dt: Time step [s]
        gamma_r: Rotational drag coefficient [N*m*s]
        T: Temperature [K]
        
    Returns:
        new_orientation: (3,) Normalized new orientation vector
    """
    # Deterministic angular velocity
    omega_det = torque / gamma_r
    
    # Stochastic angular velocity
    if T > 0:
        # D_r = k_B * T / gamma_r
        # sigma_omega = sqrt(2 * D_r / dt)  <-- Wait, usually written as dTheta terms
        # dTheta = sqrt(2 * D_r * dt) * xi
        # omega_stoch = dTheta / dt = sqrt(2 * D_r / dt) * xi
        # Let's compute the random rotation vector dTheta directly
        sigma_dtheta = np.sqrt(2.0 * Constants.kB * T * dt / gamma_r)
        dtheta_stoch = np.random.normal(scale=sigma_dtheta, size=3)
    else:
        dtheta_stoch = np.zeros(3)
        
    # Total rotation vector (angle * axis) for this step
    # dTheta_total = omega_det * dt + dtheta_stoch
    rot_vec = omega_det * dt + dtheta_stoch
    
    # Apply rotation only if magnitude is non-zero
    angle = np.linalg.norm(rot_vec)
    if angle < 1e-15:
        return orientation
            
    axis = rot_vec / angle
    
    # Rodrigues' rotation formula
    # v_rot = v cos(theta) + (k x v) sin(theta) + k (k . v) (1 - cos(theta))
    # where k is unit axis, v is orientation
    
    cos_a = np.cos(angle)
    sin_a = np.sin(angle)
    k = axis
    v = orientation
    
    v_new = v * cos_a + np.cross(k, v) * sin_a + k * np.dot(k, v) * (1.0 - cos_a)
    
    # Normalize to prevent drift
    norm = np.linalg.norm(v_new)
    if norm > 0:
        v_new /= norm
        
    return v_new

def calculate_steric_forces(positions: np.ndarray, diameters: np.ndarray, stiffness: float) -> np.ndarray:
    """
    Calculate steric repulsion forces between particles to prevent overlap.
    Uses a simple Hookean spring model for overlapping spheres.
    F_rep = stiffness * (d_avg - r) * r_unit  if r < d_avg
    
    Args:
        positions: (N, 3) particle positions
        diameters: (N,) particle diameters
        stiffness: Numerical stiffness of the repulsion
        
    Returns:
        F_steric: (N, 3) repulsive force vectors
    """
    N = len(positions)
    F_steric = np.zeros_like(positions)
    
    for i in range(N):
        for j in range(i + 1, N):
            r_vec = positions[i] - positions[j]
            r_mag = np.linalg.norm(r_vec)
            
            # Distance at which contact occurs
            d_contact = (diameters[i] + diameters[j]) / 2.0
            
            if r_mag < d_contact and r_mag > 0:
                # Compression amount
                overlap = d_contact - r_mag
                r_unit = r_vec / r_mag
                
                # Repulsive force (acting on i, opposite on j)
                force_mag = stiffness * overlap
                force_vec = force_mag * r_unit
                
                F_steric[i] += force_vec
                F_steric[j] -= force_vec
                
    return F_steric

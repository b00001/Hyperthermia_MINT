import numpy as np

def calculate_dipole_field(positions: np.ndarray, moments: np.ndarray) -> np.ndarray:
    """
    Calculate the magnetic dipole field at each particle position due to all other particles.
    
    Args:
        positions: (N, 3) array of particle coordinates [m]
        moments: (N, 3) array of magnetic moment vectors [A m^2]
        
    Returns:
        H_dip: (N, 3) array of interaction fields [A/m]
        
    Note: This is an O(N^2) implementation for basic demonstration.
    For large N, Fast Multipole Method or FFT-based methods are preferred.
    """
    N = len(positions)
    H_dip = np.zeros((N, 3))
    
    # Pre-constants
    scale = 1.0 / (4 * np.pi) 
    
    for i in range(N):
        for j in range(N):
            if i == j:
                continue
            
            r_vec = positions[i] - positions[j]
            r_mag = np.linalg.norm(r_vec)
            
            if r_mag == 0: # Should not happen if particles don't overlap
                continue
                
            n_hat = r_vec / r_mag
            m_j = moments[j]
            
            # H_dip_j_on_i = (1 / 4pi) * (3(m_j . n)n - m_j) / r^3
            dot_prod = np.dot(m_j, n_hat)
            term = 3 * dot_prod * n_hat - m_j
            
            H_dip[i] += scale * term / (r_mag**3)
            
    return H_dip

def calculate_dipole_force(positions: np.ndarray, moments: np.ndarray) -> np.ndarray:
    """
    Calculate the magnetic force on each particle due to all others.
    F_i = Sum_j( F_ji )
    F_ji = (3*mu0 / 4*pi*r^5) * [ (m_i.r)m_j + (m_j.r)m_i + (m_i.m_j)r - 5(m_i.r)(m_j.r)r/r^2 ]
    where r = r_i - r_j
    
    Args:
        positions: (N, 3) 
        moments: (N, 3)
        
    Returns:
        Force: (N, 3) [N]
    """
    N = len(positions)
    F_total = np.zeros((N, 3))
    
    # mu0 / 4pi = 1e-7
    scale = 1e-7 * 3.0
    
    for i in range(N):
        for j in range(N):
            if i == j:
                continue
            
            r_vec = positions[i] - positions[j]
            r_mag = np.linalg.norm(r_vec)
            
            if r_mag == 0:
                continue
                
            r_unit = r_vec / r_mag
            m_i = moments[i]
            m_j = moments[j]
            
            # Dot products
            mi_r = np.dot(m_i, r_vec)
            mj_r = np.dot(m_j, r_vec)
            mi_mj = np.dot(m_i, m_j)
            
            # Force term components (vectorized form of the gradient)
            # F = (3 mu0 / 4 pi r^5) * [ (m_i . r) m_j + (m_j . r) m_i + (m_i . m_j) r - 5 (m_i . r)(m_j . r) r / r^2 ]
            # Note on formula: r is vector r_i - r_j
            
            term1 = mi_r * m_j
            term2 = mj_r * m_i
            term3 = mi_mj * r_vec
            term4 = -5.0 * mi_r * mj_r * r_vec / (r_mag**2)
            
            force_ij = scale * (term1 + term2 + term3 + term4) / (r_mag**5)
            
            F_total[i] += force_ij
            
    return F_total

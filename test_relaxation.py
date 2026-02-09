from relaxation import neel_relaxation_time, brown_relaxation_time
import numpy as np

# Parameters from material_input.txt
K = 1e4  # Anisotropy constant [J/m^3]
d = 4e-9  # Particle diameter [m]
V = (np.pi / 6) * d**3  # Volume [m^3]
Ms = 4.46e5  # Saturation magnetization [A/m]
T = 300  # Temperature [K]
eta = 0.00089  # Viscosity [Pa*s]

# Calculate relaxation times
tau_N = neel_relaxation_time(1e-9, K, V, T)
tau_B = brown_relaxation_time(eta, V, T)

print(f"Particle diameter: {d*1e9:.1f} nm")
print(f"Particle volume: {V*1e27:.3f} nm^3")
print(f"\nNeel relaxation time: {tau_N:.6e} s")
print(f"Brown relaxation time: {tau_B:.6e} s")
print(f"\nRatio tau_N/tau_B: {tau_N/tau_B:.6e}")
print(f"\nRegime: {'Neel-dominated' if tau_N < tau_B else 'Brown-dominated'}")

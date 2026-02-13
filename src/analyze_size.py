"""
Analysis script for particle size dependence.
Generates plots:
1. Relaxation time constants vs particle size (τ_N, τ_B, τ_eff)
2. Heating rate (SAR) vs particle size
"""

import numpy as np
import matplotlib.pyplot as plt
from .relaxation import neel_relaxation_time, brown_relaxation_time, effective_relaxation_time
from .config import parse_config_file, get_param, SimulationConfig
from hdr.constants import Constants
from .material import Material
from .particle import Particle
from .field import AlternatingField
from .simulation import Simulation
from .hyperthermia import calculate_SAR

def analyze_relaxation_vs_size():
    """Generate relaxation time vs particle size plot."""
    # Load configuration
    config_map = parse_config_file("input.txt")
    mat_map = parse_config_file("material_input.txt")
    
    # Parameters
    T = get_param(config_map, 'temperature', 300.0)
    eta = get_param(config_map, 'viscosity', 0.00089)
    K = get_param(mat_map, 'K', 1e4)
    shell_thickness = get_param(config_map, 'shell_thickness', 2e-9)  # 2 nm default
    tau0 = get_param(mat_map, 'tau0', 1e-9)
    # Size range
    d_min = get_param(config_map, 'size_min', 2e-9)
    d_max = get_param(config_map, 'size_max', 20e-9)
    n_points = int(get_param(config_map, 'size_points', 50))
    
    diameters = np.linspace(d_min, d_max, n_points)
    radii_nm = (diameters / 2) * 1e9  # Convert to nm for plotting
    
    tau_N_arr = []
    tau_B_arr = []
    tau_eff_arr = []
    
    print("Calculating relaxation times vs particle size...")
    for d in diameters:
        # Core volume (for Néel)
        V_core = (4.0 / 3.0) * np.pi * (d/2)**3

        # Hydrodynamic volume (for Brownian)
        V_hydro = (1.0 + shell_thickness / (d/2))**3 * V_core

        tau_N = neel_relaxation_time(1e-9, K, V_core, T)
        tau_B = brown_relaxation_time(eta, V_hydro, T)
        tau_eff = effective_relaxation_time(tau_N, tau_B)

        
        tau_N_arr.append(tau_N)
        tau_B_arr.append(tau_B)
        tau_eff_arr.append(tau_eff)
    
    # Plot
    plt.figure(figsize=(8, 6))
    plt.semilogy(radii_nm, tau_N_arr, 'b-', linewidth=2, label=r'$\tau_N$ (Néel)')
    plt.semilogy(radii_nm, tau_B_arr, 'r-', linewidth=2, label=r'$\tau_B$ (Brown)')
    plt.semilogy(radii_nm, tau_eff_arr, 'k-', linewidth=2, label=r'$\tau$ (Effective)')
    
    plt.xlabel('Particle radius, R (nm)', fontsize=12)
    plt.ylabel('Relaxation time constant, τ (s)', fontsize=12)
    plt.title(f'Time constants vs. particle size\nT={T}K, K={K:.1e} J/m³', fontsize=10)
    plt.ylim(1e-12, 1)
    plt.grid(True, which='both', alpha=0.3)
    plt.legend(fontsize=11)
    plt.tight_layout()
    
    plt.savefig('output/relaxation_vs_size.png', dpi=150)
    print("Saved: output/relaxation_vs_size.png")
    plt.close()

def analyze_heating_vs_size():
    """Generate heating rate (SAR) vs particle size plot."""
    # Load configuration
    config_map = parse_config_file("input.txt")
    mat_map = parse_config_file("material_input.txt")
    
    # Parameters
    T = get_param(config_map, 'temperature', 300.0)
    eta = get_param(config_map, 'viscosity', 0.00089)
    freq = get_param(config_map, 'field_frequency', 300e3)
    amp_mT = get_param(config_map, 'field_amplitude', 25.13)
    amp = (amp_mT / 1000.0) / Constants.mu0
    dt = get_param(config_map, 'dt', 1e-10)
    
    # Material
    mat = Material(
        Ms=get_param(mat_map, 'Ms', 4.46e5),
        K=get_param(mat_map, 'K', 1e4),
        alpha=get_param(mat_map, 'alpha', 0.1),
        gamma=get_param(mat_map, 'gamma', 1.76e11)
    )
    if 'density' in mat_map:
        mat.density = mat_map['density']
    
    # Size range
    d_min = get_param(config_map, 'size_min', 2e-9)
    d_max = get_param(config_map, 'size_max', 10e-9)
    n_points = int(get_param(config_map, 'SAR_size_points', 8))  # Use SAR_size_points
    
    diameters = np.linspace(d_min, d_max, n_points)
    radii_nm = (diameters / 2) * 1e9
    
    SAR_arr = []
    
    print(f"\nCalculating SAR vs particle size ({n_points} points)...")
    print("This may take several minutes...")
    
    field = AlternatingField(amplitude=amp, frequency=freq)
    
    for i, d in enumerate(diameters):
        print(f"  {i+1}/{n_points}: d={d*1e9:.1f} nm", end='')
        
        # Create particle
        particle = Particle(diameter=d, material=mat)
        
        # Quick simulation (1 cycle only)
        tmax = 1.0 / freq
        sim_config = SimulationConfig(
            temperature=T,
            viscosity=eta,
            dt=dt,
            tmax=tmax
        )
        
        sim = Simulation(sim_config, [particle], field, mode='auto')
        hysteresis = sim.run()
        
        # Calculate SAR
        area = hysteresis.calculate_area()
        sar = calculate_SAR(area, freq, density=get_param(mat_map, 'density', 5200))
        SAR_arr.append(sar)
        
        print(f" → SAR={sar:.2e} W/kg")
    
    # Plot
    plt.figure(figsize=(8, 6))
    plt.plot(radii_nm, SAR_arr, 'b-', linewidth=2, marker='o', markersize=4)
    
    plt.xlabel('Particle radius, R (nm)', fontsize=12)
    plt.ylabel('SAR (W/kg)', fontsize=12)
    plt.title(f'Heating rate vs. particle size\nB={amp_mT:.1f} mT, f={freq/1e3:.0f} kHz, T={T}K', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plt.savefig('output/SAR_vs_size.png', dpi=150)
    print("\nSaved: output/SAR_vs_size.png")
    plt.close()

def run():
    import os
    os.makedirs('output', exist_ok=True)
    
    # Load configuration to check what to analyze
    config_map = parse_config_file("input.txt")
    do_relaxation = get_param(config_map, 'analyze_relaxation', True)
    do_SAR = get_param(config_map, 'analyze_SAR', True)
    
    print("="*60)
    print("Particle Size Analysis")
    print("="*60)
    print(f"Relaxation analysis: {do_relaxation}")
    print(f"SAR analysis: {do_SAR}")
    print("="*60)
    
    # Plot 1: Relaxation times (fast)
    if do_relaxation:
        analyze_relaxation_vs_size()
    else:
        print("Skipping relaxation analysis (analyze_relaxation=False)")
    
    # Plot 2: Heating rate (slow, requires simulations)
    if do_SAR:
        analyze_heating_vs_size()
    else:
        print("Skipping SAR analysis (analyze_SAR=False)")
    
    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60)

if __name__ == "__main__":
    run()

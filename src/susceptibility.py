import os
import sys
import numpy as np
from hdr.constants import Constants
from .config import parse_config_file, get_param
from .relaxation import neel_relaxation_time, brown_relaxation_time, effective_relaxation_time
import matplotlib.pyplot as plt


def calculate_susceptibility_spectra(f_sweep, T, viscosity, tau0, shell, Ms, K, d, polydisperse=False, sigma=0.1):
    """
    Calculate complex susceptibility spectra for monodisperse or polydisperse particles.
    
    Returns:
        chi_prime, chi_double_prime, chi0 (static susceptibility for normalization)
    """
    kB = Constants.kB
    mu0 = Constants.mu0

    if not polydisperse:
        # Monodisperse Case
        V = (np.pi * d**3) / 6.0
        V_hydro = (np.pi * (d + 2*shell)**3) / 6.0
        
        x0 = (mu0 * Ms**2 * V) / (3 * kB * T)
        
        tau_N = neel_relaxation_time(tau0, K, V, T)
        tau_B = brown_relaxation_time(viscosity, V_hydro, T)
        tau_eff = effective_relaxation_time(tau_N, tau_B)
        
        omega = 2 * np.pi * f_sweep
        denom = 1 + (omega * tau_eff)**2
        chi_prime = x0 / denom
        chi_double_prime = (x0 * omega * tau_eff) / denom
            
        return chi_prime, chi_double_prime, x0
        
    else:
        # Polydisperse Case (Log-normal distribution)
        N_sizes = 200
        d_median = d

        d_min = d_median * np.exp(-5 * sigma)
        d_max = d_median * np.exp(5 * sigma)
        d_array = np.linspace(d_min, d_max, N_sizes)
        
        # Log-normal PDF
        weights = (1.0 / (d_array * sigma * np.sqrt(2 * np.pi))) * \
                  np.exp(-np.log(d_array / d_median)**2 / (2 * sigma**2))
        weights /= np.trapz(weights, d_array)
        
        # Precompute per-size parameters
        tau_eff_array = np.zeros(N_sizes)
        x0_array = np.zeros(N_sizes)
        
        for j, dj in enumerate(d_array):
            Vj = (np.pi / 6.0) * dj**3
            VHj = (np.pi / 6.0) * (dj + 2*shell)**3
            x0_array[j] = (mu0 * Ms**2 * Vj) / (3 * kB * T)
            tau_Nj = neel_relaxation_time(tau0, K, Vj, T)
            tau_Bj = brown_relaxation_time(viscosity, VHj, T)
            tau_eff_array[j] = effective_relaxation_time(tau_Nj, tau_Bj)
        
        chi_prime_poly = np.zeros_like(f_sweep)
        chi_double_poly = np.zeros_like(f_sweep)
        
        for i, f in enumerate(f_sweep):
            omega = 2 * np.pi * f
            denom = 1 + (omega * tau_eff_array)**2
            cp_contrib = weights * (x0_array / denom)
            cdp_contrib = weights * ((x0_array * omega * tau_eff_array) / denom)
            chi_prime_poly[i] = np.trapz(cp_contrib, d_array)
            chi_double_poly[i] = np.trapz(cdp_contrib, d_array)
            
        x0_total = np.trapz(weights * x0_array, d_array)
        return chi_prime_poly, chi_double_poly, x0_total


def calculate_power_dissipation(chi_double_prime, H0, f_sweep):
    """
    Volumetric power dissipation (Rosensweig Eq. 6).
    P = mu0 * pi * chi'' * H0^2 * f   [W/m^3]
    """
    mu0 = Constants.mu0
    return mu0 * np.pi * chi_double_prime * H0**2 * f_sweep

def calculate_power_dissipation_tua(x0, tau_eff, H0, f_sweep):
    """
    Volumetric power dissipation (Tua Eq. 6).
    P = mu0 * pi * chi'' * H0^2 * f   [W/m^3]
    """
    mu0 = Constants.mu0
    return (mu0 * np.pi * x0 * H0**2 * f_sweep * (2 * np.pi * f_sweep) * tau_eff) / (1 + (2 * np.pi * f_sweep * tau_eff)**2)


def calculate_SAR(P, density):
    """
    Specific Absorption Rate.
    SAR = P / density   [W/kg]
    
    Args:
        P: Power dissipation [W/m^3]
        density: Material density [kg/m^3]
    Returns:
        SAR [W/kg]
    """
    return P / density


def calculate_SAR_vs_diameter(d_array, f, T, viscosity, tau0, shell, Ms, K, H0, density):
    """
    Calculate SAR as a function of particle diameter at a fixed frequency.
    
    Args:
        d_array: Array of diameters [m]
        f: Fixed frequency [Hz]
        T, viscosity, tau0, shell, Ms, K: Physical parameters
        H0: Field amplitude [A/m]
        density: Material density [kg/m^3]
    Returns:
        SAR_array [W/kg]
    """
    mu0 = Constants.mu0
    kB = Constants.kB
    omega = 2 * np.pi * f
    SAR_array = np.zeros_like(d_array)
    
    for i, d in enumerate(d_array):
        V = (np.pi * d**3) / 6.0
        V_hydro = (np.pi * (d + 2*shell)**3) / 6.0
        
        x0 = (mu0 * Ms**2 * V) / (3 * kB * T)
        
        tau_N = neel_relaxation_time(tau0, K, V, T)
        tau_B = brown_relaxation_time(viscosity, V_hydro, T)
        tau_eff = effective_relaxation_time(tau_N, tau_B)
        
        denom = 1 + (omega * tau_eff)**2
        chi_dp = (x0 * omega * tau_eff) / denom
        
        P = mu0 * np.pi * chi_dp * H0**2 * f
        P = calculate_power_dissipation_tua(x0, tau_eff, H0, f)
        SAR_array[i] = P / density
    
    return SAR_array


def run():

    print("-" * 50)
    print("Susceptibility Analysis Tool")
    print("-" * 50)

    config_file = "input.txt"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    print(f"Loading configuration from: {config_file}")

    # ---------------------------------------------------------
    # 1. Load Configurations
    # ---------------------------------------------------------
    config_map = parse_config_file(config_file)
    
    mat_filename = get_param(config_map, 'material', required=True)
    if not mat_filename.endswith('.txt'):
        mat_filename += ".txt"
    print(f"Loading material from: {mat_filename}")
    mat_map = parse_config_file(mat_filename)

    # ---------------------------------------------------------
    # 2. Extract Parameters
    # ---------------------------------------------------------
    # From input.txt
    T         = get_param(config_map, 'temperature', 300.0)
    viscosity = get_param(config_map, 'viscosity', 1.0e-3)
    shell     = get_param(config_map, 'shell_thickness', 2e-9)
    d         = get_param(config_map, 'particle_diameter', 8.9e-9)
    
    B0_mT     = get_param(config_map, 'field_amplitude', 60.0)
    B0        = B0_mT * 1e-3   # mT -> T
    H0        = B0 / Constants.mu0  # B -> H [A/m]
    
    # Frequency sweep
    f_min     = get_param(config_map, 'freq_min', 0.0)
    f_max     = get_param(config_map, 'freq_max', 3e6)
    f_points  = int(get_param(config_map, 'freq_points', 5000))
    scale     = get_param(config_map, 'freq_scale', 'linear')
    
    # Polydispersity
    is_polydisperse = get_param(config_map, 'polydisperse', False)
    sigma           = get_param(config_map, 'val_sigma', 0.1)
    
    # SAR vs diameter sweep
    size_min    = get_param(config_map, 'size_min', 1e-9)
    size_max    = get_param(config_map, 'size_max', 30e-9)
    size_points = int(get_param(config_map, 'SAR_size_points', 300))
    f_fixed     = get_param(config_map, 'field_frequency', 400000)  # Hz for SAR vs d plot
    
    # Output directory
    output_dir = get_param(config_map, 'output_dir', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # From material file
    Ms      = get_param(mat_map, 'Ms', required=True)
    K       = get_param(mat_map, 'K', required=True)
    tau0    = get_param(mat_map, 'tau0', 1e-9)
    density = get_param(mat_map, 'density', 5180.0)

    print(f"Temperature:  {T} K")
    print(f"Viscosity:    {viscosity} Pa*s")
    print(f"Particle d:   {d*1e9:.2f} nm")
    print(f"Shell:        {shell*1e9:.2f} nm")
    print(f"B0:           {B0*1e3:.1f} mT  (H0 = {H0:.2e} A/m)")
    print(f"Ms:           {Ms:.2e} A/m")
    print(f"K:            {K:.2e} J/m^3")
    print(f"tau0:         {tau0:.2e} s")
    print(f"Density:      {density} kg/m^3")
    print(f"Polydisperse: {is_polydisperse}")
    if is_polydisperse:
        print(f"Sigma:        {sigma}")
    print(f"Output dir:   {output_dir}")

    # ---------------------------------------------------------
    # 3. Generate frequency array
    # ---------------------------------------------------------
    if scale == 'log':
        f_sweep = np.logspace(np.log10(max(f_min, 1.0)), np.log10(f_max), f_points)
    else:
        f_sweep = np.linspace(f_min, f_max, f_points)
        
    # ---------------------------------------------------------
    # 4. Susceptibility spectra (both mono & poly)
    # ---------------------------------------------------------
    print("\nComputing monodisperse (sigma = 0) spectra...")
    chi_p_mono, chi_dp_mono, x0_mono = calculate_susceptibility_spectra(
        f_sweep, T, viscosity, tau0, shell, Ms, K, d, polydisperse=False
    )
    
    print("Computing polydisperse (sigma = {:.2f}) spectra...".format(sigma))
    chi_p_poly, chi_dp_poly, x0_poly = calculate_susceptibility_spectra(
        f_sweep, T, viscosity, tau0, shell, Ms, K, d, polydisperse=True, sigma=sigma
    )
    
    # Normalize
    chi_p_mono_norm  = chi_p_mono  / x0_mono
    chi_dp_mono_norm = chi_dp_mono / x0_mono
    chi_p_poly_norm  = chi_p_poly  / x0_poly
    chi_dp_poly_norm = chi_dp_poly / x0_poly

    # ---------------------------------------------------------
    # 5. Power dissipation & SAR vs frequency
    # ---------------------------------------------------------
    P_mono = calculate_power_dissipation(chi_dp_mono, H0, f_sweep)
    P_poly = calculate_power_dissipation(chi_dp_poly, H0, f_sweep)
    
    SAR_mono = calculate_SAR(P_mono, density)
    SAR_poly = calculate_SAR(P_poly, density)

    # ---------------------------------------------------------
    # 6. SAR vs diameter (at fixed frequency)
    # ---------------------------------------------------------
    print(f"Computing SAR vs diameter at f = {f_fixed:.2e} Hz...")
    d_array = np.linspace(size_min, size_max, size_points)
    SAR_vs_d = calculate_SAR_vs_diameter(
        d_array, f_fixed, T, viscosity, tau0, shell, Ms, K, H0, density
    )

    # ==========================================================
    #  PLOTS
    # ==========================================================
    
    # --- Plot 1: Susceptibility Spectrum (Rosensweig Fig. 1) ---
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    ax1.plot(f_sweep, chi_p_mono_norm,  'b-',  linewidth=2, label=r"Real ($\sigma = 0$)")
    ax1.plot(f_sweep, chi_dp_mono_norm, 'b--', linewidth=2, label=r"Imaginary ($\sigma = 0$)")
    ax1.plot(f_sweep, chi_p_poly_norm,  'r-',  linewidth=2, label=r"Real ($\sigma = 0.1$)")
    ax1.plot(f_sweep, chi_dp_poly_norm, 'r--', linewidth=2, label=r"Imaginary ($\sigma = 0.1$)")
    ax1.set_xlabel("Frequency, f (Hz)", fontsize=12)
    ax1.set_ylabel(r"$\chi / \chi_0$", fontsize=14)
    ax1.set_title(f"Fig. 1  Susceptibility (d = {d*1e9:.1f} nm, "
                  f"$B_0$ = {B0*1e3:.0f} mT, T = {T:.0f} K)", fontsize=12)
    ax1.set_xlim(0, f_max)
    ax1.set_ylim(0, 1.05)
    ax1.legend(fontsize=10, loc='best')
    ax1.grid(True, linestyle='--', alpha=0.5)
    fig1.tight_layout()
    fig1.savefig(os.path.join(output_dir, "susceptibility_spectrum.png"), dpi=150)
    print(f"\nPlot saved to {output_dir}/susceptibility_spectrum.png")
    
    # --- Plot 2: Power Dissipation vs Frequency ---
    fig2, ax2 = plt.subplots(figsize=(8, 6))
    ax2.plot(f_sweep, P_mono * 1e-6, 'b-',  linewidth=2, label=r"Monodisperse ($\sigma = 0$)")
    ax2.plot(f_sweep, P_poly * 1e-6, 'r-',  linewidth=2, label=r"Polydisperse ($\sigma = 0.1$)")
    ax2.set_xlabel("Frequency, f (Hz)", fontsize=12)
    ax2.set_ylabel(r"Power Dissipation, P (MW/m$^3$)", fontsize=12)
    ax2.set_title(f"Power Dissipation ($B_0$ = {B0*1e3:.0f} mT, "
                  f"d = {d*1e9:.1f} nm, T = {T:.0f} K)", fontsize=12)
    ax2.set_xlim(0, f_max)
    ax2.legend(fontsize=10, loc='best')
    ax2.grid(True, linestyle='--', alpha=0.5)
    fig2.tight_layout()
    fig2.savefig(os.path.join(output_dir, "power_spectrum.png"), dpi=150)
    print(f"Plot saved to {output_dir}/power_spectrum.png")

    # --- Plot 3: SAR vs Frequency ---
    fig3, ax3 = plt.subplots(figsize=(8, 6))
    ax3.plot(f_sweep, SAR_mono, 'b-',  linewidth=2, label=r"Monodisperse ($\sigma = 0$)")
    ax3.plot(f_sweep, SAR_poly, 'r-',  linewidth=2, label=r"Polydisperse ($\sigma = 0.1$)")
    ax3.set_xlabel("Frequency, f (Hz)", fontsize=12)
    ax3.set_ylabel("SAR (W/kg)", fontsize=12)
    ax3.set_title(f"SAR vs Frequency ($B_0$ = {B0*1e3:.0f} mT, "
                  f"d = {d*1e9:.1f} nm, T = {T:.0f} K)", fontsize=12)
    ax3.set_xlim(0, f_max)
    ax3.legend(fontsize=10, loc='best')
    ax3.grid(True, linestyle='--', alpha=0.5)
    fig3.tight_layout()
    fig3.savefig(os.path.join(output_dir, "SAR_vs_frequency.png"), dpi=150)
    print(f"Plot saved to {output_dir}/SAR_vs_frequency.png")

    # --- Plot 4: SAR vs Diameter ---
    fig4, ax4 = plt.subplots(figsize=(8, 6))
    ax4.plot(d_array * 1e9, SAR_vs_d, 'b-', linewidth=2)
    ax4.set_xlabel("Particle Diameter (nm)", fontsize=12)
    ax4.set_ylabel("SAR (W/kg)", fontsize=12)
    ax4.set_title(f"SAR vs Diameter ($B_0$ = {B0*1e3:.0f} mT, "
                  f"f = {f_fixed*1e-3:.0f} kHz, T = {T:.0f} K)", fontsize=12)
    ax4.grid(True, linestyle='--', alpha=0.5)
    fig4.tight_layout()
    fig4.savefig(os.path.join(output_dir, "SAR_vs_diameter.png"), dpi=150)
    print(f"Plot saved to {output_dir}/SAR_vs_diameter.png")

    # ---------------------------------------------------------
    # 7. CSV Output
    # ---------------------------------------------------------
    # Spectra CSV
    data_spectra = np.column_stack((
        f_sweep,
        chi_p_mono, chi_dp_mono, chi_p_mono_norm, chi_dp_mono_norm,
        chi_p_poly, chi_dp_poly, chi_p_poly_norm, chi_dp_poly_norm,
        P_mono, P_poly, SAR_mono, SAR_poly
    ))
    header_spectra = ("Frequency[Hz], "
              "Chi_Prime_Mono, Chi_DoublePrime_Mono, Chi_Prime_Mono_Norm, Chi_DoublePrime_Mono_Norm, "
              "Chi_Prime_Poly, Chi_DoublePrime_Poly, Chi_Prime_Poly_Norm, Chi_DoublePrime_Poly_Norm, "
              "P_Mono[W/m3], P_Poly[W/m3], SAR_Mono[W/kg], SAR_Poly[W/kg]")
    np.savetxt(os.path.join(output_dir, "susceptibility_spectra.csv"), data_spectra, 
               header=header_spectra, delimiter=",")
    print(f"Data saved to {output_dir}/susceptibility_spectra.csv")
    
    # SAR vs diameter CSV
    data_sar_d = np.column_stack((d_array * 1e9, SAR_vs_d))
    np.savetxt(os.path.join(output_dir, "SAR_vs_diameter.csv"), data_sar_d,
               header="Diameter[nm], SAR[W/kg]", delimiter=",")
    print(f"Data saved to {output_dir}/SAR_vs_diameter.csv")

    # ---------------------------------------------------------
    # 8. Summary
    # ---------------------------------------------------------
    idx_peak_mono = np.argmax(chi_dp_mono_norm)
    print(f"\nMonodisperse chi'' peak at f = {f_sweep[idx_peak_mono]:.2e} Hz")
    print(f"  chi0 = {x0_mono:.4e}")
    
    idx_cross = np.argmin(np.abs(chi_p_poly_norm - chi_dp_poly_norm))
    print(f"Polydisperse crossover at f ~ {f_sweep[idx_cross]:.2e} Hz")
    print(f"  chi0 = {x0_poly:.4e}")
    
    print(f"\nMax SAR (mono, vs f):  {np.max(SAR_mono):.2e} W/kg")
    print(f"Max SAR (poly, vs f):  {np.max(SAR_poly):.2e} W/kg")
    
    idx_peak_d = np.argmax(SAR_vs_d)
    print(f"Peak SAR vs diameter:  {SAR_vs_d[idx_peak_d]:.2e} W/kg at d = {d_array[idx_peak_d]*1e9:.2f} nm")
    
    print("-" * 50)


if __name__ == "__main__":
    run()

from .config import SimulationConfig, parse_config_file, get_param
from hdr.constants import Constants
from .material import Material
from .particle import Particle
from .field import AlternatingField
from .simulation import Simulation
from .hyperthermia import calculate_SAR
from .visualization import plot_hysteresis, plot_time_series, animate_system
import os

import numpy as np

def run():
    print("Initializing Magnetic Hyperthermia Simulation from config files...")
    
    import sys
    config_file = "input.txt"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    # 1. Load Configurations
    config_map = parse_config_file(config_file)
    mat_map = parse_config_file(get_param(config_map, 'material', required=True) + ".txt")
    
    # Defaults if missing (safe fallback)
    freq = get_param(config_map, 'field_frequency', 300e3)
    # Field amplitude is now in mT (milliTesla) in input file
    # Convert to A/m: H [A/m] = B [T] / mu0
    amp_mT = get_param(config_map, 'field_amplitude', 25.13)  # Default 25.13 mT
    amp = (amp_mT / 1000.0) / Constants.mu0  # Convert mT -> T -> A/m
    cycles = get_param(config_map, 'cycles', 1)
    dt = get_param(config_map, 'dt', 1e-10)
    max_steps = int(get_param(config_map, 'max_steps', 0))  # 0 = auto
    animation_fps = get_param(config_map, 'animation_fps', 20)
    
    # Calculate tmax and override if max_steps is specified
    tmax = cycles / freq if freq > 0 else 1e-7
    if max_steps > 0:
        tmax = max_steps * dt
        print(f"Using max_steps={max_steps} (overriding cycles={cycles})")
    
    sim_config = SimulationConfig(
        temperature=get_param(config_map, 'temperature', 300.0),
        viscosity=get_param(config_map, 'viscosity', 0.00089),
        dt=dt,
        tmax=tmax
    )
    
    # 2. Define Material and Particles
    # Construct material from map
    mat = Material(
        Ms=get_param(mat_map, 'Ms', 4.46e5),
        K=get_param(mat_map, 'K', 1e4),
        alpha=get_param(mat_map, 'alpha', 0.1),
        gamma=get_param(mat_map, 'gamma', 1.76e11),
        tau0=get_param(mat_map, 'tau0', 1e-9),
        density=get_param(mat_map, 'density', 5180.0)
    )
    p_diam = get_param(config_map, 'particle_diameter', 20e-9)
    p_count = int(get_param(config_map, 'particle_count', 10))
    
    # Create an ensemble
    particles = [Particle(diameter=p_diam, material=mat) for _ in range(p_count)]
    
    # 3. Define Field
    field = AlternatingField(amplitude=amp, frequency=freq)
    
    # 4. Create Simulation
    sim = Simulation(sim_config, particles, field)
    
    print(f"Running simulation for {len(particles)} particles over {cycles} cycles...")
    print(f"Field: {amp*Constants.mu0*1000:.2f} mT @ {freq/1000} kHz")
    
    # 5. Run
    hysteresis = sim.run()
    
    # 6. Analyze
    times, H, M = hysteresis.get_arrays()
    area = hysteresis.calculate_area()
    # Need density for SAR... provided in mat_map
    dens = get_param(mat_map, 'density', 5200)
    sar = calculate_SAR(area, freq, density=dens)
    
    print("\n--- Results ---")
    print(f"Hysteresis Loop Area: {area:.4e} J/m^3")
    print(f"Calculated SAR: {sar:.2f} W/kg")
    
    if area > 0:
        print("SUCCESS: Hysteresis detected.")
    else:
        print("WARNING: Loop area is zero. Check simulation parameters (e.g., field amplitude vs anisotropy).")
        
    # 7. Visualize (Optional based on input.txt)
    save_output = get_param(config_map, 'save_output', True)
    
    if save_output:
        output_dir = get_param(config_map, 'output_dir', "output")
        os.makedirs(output_dir, exist_ok=True)
        print(f"\nSaving results to '{output_dir}' directory...")
        
        plot_hysteresis(hysteresis, save_path=os.path.join(output_dir, "hysteresis_loop.png"))
        plot_time_series(hysteresis, save_path=os.path.join(output_dir, "time_series.png"))
        
        print("Generating animation (this may take a moment)...")
        # Using .gif as it is more portable without ffmpeg installed, though .mp4 is better if ffmpeg exists
        # Animation interval in ms = 1000 / fps
        anim_interval = int(1000 / animation_fps)
        animate_system(sim.pos_history, sim.history, times, field=field, interval=anim_interval, save_path=os.path.join(output_dir, "simulation.gif"))
        print("Done.")
    else:
        print("\nOutput saving disabled in input.txt. Displaying plots instead...")
        plot_hysteresis(hysteresis)
        plot_time_series(hysteresis)
        anim_interval = int(1000 / animation_fps)
        animate_system(sim.pos_history, sim.history, times, field=field, interval=anim_interval)

if __name__ == "__main__":
    run()

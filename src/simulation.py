import numpy as np
from typing import List, Optional

from .config import SimulationConfig
from hdr.constants import Constants
from .material import Material
from .particle import Particle
from .field import Field, AlternatingField
from .dynamics import (
    calculate_translational_gamma, 
    calculate_rotational_gamma, 
    calculate_translational_displacement, 
    calculate_rotational_update,
    calculate_steric_forces
)
from .magnetization import calculate_effective_field, solve_llg_step
from .relaxation import neel_relaxation_time, brown_relaxation_time
from .dipole import calculate_dipole_field, calculate_dipole_force
from .hysteresis_loop import HysteresisLoop

class Simulation:
    def __init__(self, config: SimulationConfig, particles: List[Particle], field: Field, mode='auto'):
        """
        Initialize simulation.
        
        Args:
            config: SimulationConfig object
            particles: List of Particle objects
            field: Field object (external magnetic field)
            mode: 'auto', 'neel', or 'brownian'
                - 'auto': Auto-detect based on relaxation times
                - 'neel': Force Neel relaxation (stochastic LLG)
                - 'brownian': Force Brownian relaxation (rigid body rotation)
        """
        self.config = config
        self.particles = particles
        self.field = field
        self.time = 0.0
        self.hysteresis = HysteresisLoop()
        self.history = [] # List of (N, 3) arrays to store magnetization states
        self.pos_history = [] # List of (N, 3) arrays to store position states
        
        # Initialize positions
        n_particles = len(particles)
        self.positions = np.zeros((n_particles, 3)) 
        
        # Simple linear arrangement along X-axis centered at origin
        spacing = 3.0 * particles[0].diameter if n_particles > 0 else 1e-7
        
        start_x = - (n_particles - 1) * spacing / 2.0
        for i in range(n_particles):
            self.positions[i] = np.array([start_x + i * spacing, 0.0, 0.0])
        
        # Determine simulation mode
        self.mode = self._determine_mode(mode)
        print(f"Simulation Mode: {self.mode.upper()}")

    def _determine_mode(self, mode_input: str) -> str:
        """Determine which dynamics to use based on relaxation times."""
        if mode_input in ['neel', 'brownian']:
            return mode_input
            
        # Auto-detect based on first particle
        if len(self.particles) == 0:
            return 'brownian'
            
        p = self.particles[0]
        tau_N = neel_relaxation_time(1e-9, p.material.K, p.volume, self.config.temperature)
        tau_B = brown_relaxation_time(self.config.viscosity, p.volume, self.config.temperature)
        
        print(f"Auto-detect: tau_N = {tau_N:.3e} s, tau_B = {tau_B:.3e} s")
        print(f"Ratio tau_N/tau_B = {tau_N/tau_B:.3e}")
        
        return 'neel' if tau_N < tau_B else 'brownian'

    def run(self):
        """Run the simulation loop."""
        n_steps = int(self.config.tmax / self.config.dt)
        n_particles = len(self.particles)
        
        # Precompute drag coefficients (used in both modes for translation)
        gammas_t = np.array([calculate_translational_gamma(self.config.viscosity, p.diameter) for p in self.particles])
        gammas_r = np.array([calculate_rotational_gamma(self.config.viscosity, p.diameter) for p in self.particles])
        
        # Current magnetization directions state (N, 3)
        m_dirs = np.array([p.magnetization_direction for p in self.particles])
        moments_mag = np.array([p.get_magnetic_moment_magnitude() for p in self.particles])
        diameters = np.array([p.diameter for p in self.particles])
        
        # Anisotropy axes (assuming z-axis for all particles for now)
        aniso_axes = np.array([[0.0, 0.0, 1.0] for _ in self.particles])
        
        print(f"Starting simulation: {n_steps} steps, dt={self.config.dt}")
        
        # Main Time Loop
        for step in range(n_steps):
            t = self.time
            
            # 1. Get External Field
            H_ext_vec = self.field.get_field(t) # (3,)
            
            # 2. Dipole Interactions
            current_moments = m_dirs * moments_mag[:, np.newaxis]
            H_dip = calculate_dipole_field(self.positions, current_moments)
            dipole_forces = calculate_dipole_force(self.positions, current_moments)
            steric_forces = calculate_steric_forces(self.positions, diameters, self.config.steric_stiffness)
            
            total_forces = dipole_forces + steric_forces
            
            # 3. Update State for each particle
            new_positions = np.zeros_like(self.positions)
            new_m_dirs = np.zeros_like(m_dirs)
            
            avg_Mz = 0.0
            
            for i in range(n_particles):
                p = self.particles[i]
                
                # --- Translation (Common to both modes) ---
                disp = calculate_translational_displacement(
                    force=total_forces[i],
                    dt=self.config.dt,
                    gamma_t=gammas_t[i],
                    T=self.config.temperature
                )
                new_positions[i] = self.positions[i] + disp
                
                # --- Magnetization Dynamics (Mode-dependent) ---
                if self.mode == 'neel':
                    # Neel Mode: Solve stochastic LLG
                    H_eff = calculate_effective_field(
                        t=t,
                        m_vector=m_dirs[i],
                        H_ext=H_ext_vec,
                        H_dip=H_dip[i],
                        anisotropy_axis=aniso_axes[i],
                        K=p.material.K,
                        Ms=p.material.Ms,
                        alpha=p.material.alpha,
                        V=p.volume,
                        T=self.config.temperature,
                        dt=self.config.dt,
                        gamma=p.material.gamma
                    )
                    
                    new_m_dirs[i] = solve_llg_step(
                        m_old=m_dirs[i],
                        H_eff=H_eff,
                        gamma=p.material.gamma,
                        alpha=p.material.alpha,
                        dt=self.config.dt
                    )
                    
                else:
                    # Brownian Mode: Rigid body rotation
                    H_local = H_ext_vec + H_dip[i]
                    torque = Constants.mu0 * np.cross(current_moments[i], H_local)
                    
                    new_m_dirs[i] = calculate_rotational_update(
                        orientation=m_dirs[i],
                        torque=torque,
                        dt=self.config.dt,
                        gamma_r=gammas_r[i],
                        T=self.config.temperature
                    )
                
                # Hysteresis tracking
                avg_Mz += new_m_dirs[i][2] * p.material.Ms
            
            # Update state arrays
            self.positions = new_positions
            m_dirs = new_m_dirs
            
            # Store history
            self.history.append(m_dirs.copy())
            self.pos_history.append(self.positions.copy())
            
            # Update particle objects (sync)
            for i, p in enumerate(self.particles):
                p.magnetization_direction = m_dirs[i]
            
            # Record Hysteresis Data
            H_val = H_ext_vec[2] 
            M_val = avg_Mz / n_particles
            self.hysteresis.add_point(t, H_val, M_val)
            
            self.time += self.config.dt
            
        return self.hysteresis

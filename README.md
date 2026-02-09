# Brownian Dynamics Magnetic Hyperthermia Simulation

## 1. Overview
This project simulates the dynamics of magnetic nanoparticles in a fluid under an alternating magnetic field. It specifically focuses on the **Brownian-dominated regime**, where the magnetic moment is rigidly locked to the particle, and relaxation occurs via physical rotation of the particle.

The simulation includes:
- **Translational Brownian Motion**: Particles diffuse in space.
- **Rotational Brownian Motion**: Particles rotate due to thermal fluctuations and magnetic torque.
- **Dipole-Dipole Interactions**: Magnetic forces and mutual induction between particles.
- **Viscous Drag**: Overdamped dynamics in a fluid environment.

## 2. Physics Model

### Conceptual Framework
- **Regime**: $ \tau_{Neel} \gg \tau_{Brown} $. The internal magnetization is locked to the particle's easy axis.
- **State Variables**: 
  - Position $\mathbf{r}_i$ 
  - Orientation/Magnetization Direction $\mathbf{n}_i$ (Unit vector)

### Equations of Motion (Langevin Dynamics)

**1. Translation (Force Balance)**
$$ \mathbf{r}(t+\Delta t) = \mathbf{r}(t) + \frac{\mathbf{F}_{dip}}{\gamma_t} \Delta t + \sqrt{2 D_t \Delta t} \mathbf{\xi}_t $$
- $\mathbf{F}_{dip}$: Magnetic dipole-dipole force.
- $\gamma_t = 3 \pi \eta d$: Translational drag (Stokes' Law).
- $D_t = k_B T / \gamma_t$: Translational diffusion coefficient.

**2. Rotation (Torque Balance)**
$$ \mathbf{n}(t+\Delta t) = \mathbf{n}(t) + (\boldsymbol{\omega} \times \mathbf{n}(t)) \Delta t $$
$$ \boldsymbol{\omega} = \frac{\boldsymbol{\tau}_{mag}}{\gamma_r} + \boldsymbol{\xi}_{rot} $$
- $\boldsymbol{\tau}_{mag} = \mu_0 (\mathbf{m} \times \mathbf{H}_{loc})$: Magnetic torque aligning the particle.
- $\mathbf{H}_{loc} = \mathbf{H}_{ext} + \mathbf{H}_{dip}$: Local effective field.
- $\gamma_r = \pi \eta d^3$: Rotational drag.
- Discretized random rotation has variance $\propto 2 k_B T \Delta t / \gamma_r$.

## 3. Project Structure

| File | Description |
|------|-------------|
| `main.py` | Entry point. Sets up and runs the simulation. |
| `input.txt` | Configuration for simulation parameters (T, viscosity, field). |
| `material_input.txt` | Configuration for material properties (Ms, K, diameter). |
| `simulation.py` | Contains the `Simulation` class and main time loop. |
| `dynamics.py` | Implements the Langevin physics functions (translation & rotation). |
| `particle.py` | `Particle` class holding state (position, magnetization). |
| `dipole.py` | Calculates dipole-dipole fields and forces ($O(N^2)$). |
| `field.py` | Defines the external alternating magnetic field. |
| `visualization.py` | Plotting and animation functions. |
| `config.py` | Configuration parsing and constants. |

## 4. How to Run

### Prerequisites
- Python 3.x
- NumPy, Matplotlib

### Execution
1. **Configure Parameters**:
   Edit `input.txt` to change field strength, frequency, or duration.
   Edit `material_input.txt` to change particle size or magnetic properties.

2. **Run Simulation**:
   ```bash
   python main.py
   ```
   Or with a specific config file:
   ```bash
   python main.py my_config.txt
   ```

3. **Output**:
   Results are saved in the `output/` directory (or as specified in config):
   - `simulation.gif`: 3D Animation of particle motion.
   - `hysteresis_loop.png`: M vs H loop.
   - `time_series.png`: Field and Magnetization vs Time.
   - Console output shows the Loop Area and calculated SAR (Specific Absorption Rate).

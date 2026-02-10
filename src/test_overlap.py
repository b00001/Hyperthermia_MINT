import numpy as np
import matplotlib.pyplot as plt
from .config import SimulationConfig
from .material import Material
from .particle import Particle
from .field import StaticField
from .simulation import Simulation

def test_overlap():
    # Setup: 2 particles very close to each other, attracted
    # Mode will be Brownian (easier to see overlap prevention)
    
    mat = Material(Ms=4e5, K=1e4, alpha=0.1, gamma=1.76e11)
    
    # Diameter = 20nm
    p1 = Particle(material=mat, diameter=20e-9)
    p2 = Particle(material=mat, diameter=20e-9)
    
    # They are already overlapping! Total diameter = 20nm, distance = 10nm.
    
    # Force them to point towards each other for attraction? 
    # Or just let steric force push them apart to d=20nm.
    p1.magnetization_direction = np.array([1.0, 0, 0])
    p2.magnetization_direction = np.array([1.0, 0, 0])
    
    config = SimulationConfig(
        dt=1e-12, 
        tmax=2e-9, 
        steric_stiffness=10.0 # High stiffness
    )
    
    # Static zero field
    field = StaticField(np.array([0, 0, 0]))
    
    sim = Simulation(config, [p1, p2], field, mode='brownian')
    
    # Override positions to force overlap for testing
    sim.positions[0] = np.array([-5e-9, 0, 0])
    sim.positions[1] = np.array([5e-9, 0, 0])
    
    distances = []
    times = []
    
    for _ in range(50):
        sim.run() # This runs until tmax
        dist = np.linalg.norm(sim.positions[0] - sim.positions[1])
        distances.append(dist)
        times.append(sim.time)
    
    plt.figure(figsize=(8, 5))
    plt.plot(np.array(times)*1e9, np.array(distances)*1e9, label='Distance between particles')
    plt.axhline(y=20, color='r', linestyle='--', label='Contact Diameter (20nm)')
    plt.xlabel('Time (ns)')
    plt.ylabel('Distance (nm)')
    plt.title('Steric Repulsion Verification (Starting Overlapped)')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    final_dist = np.linalg.norm(sim.positions[0] - sim.positions[1])
    print(f"Final distance: {final_dist*1e9:.2f} nm")
    print(f"Target distance: 20.00 nm")

if __name__ == "__main__":
    test_overlap()

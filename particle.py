import numpy as np
from material import Material

class Particle:
    """
    Represents a single spherical magnetic nanoparticle.
    """
    def __init__(self, diameter: float, material: Material, shell_thickness=0.0):
        """
        Args:
            diameter (float): Particle diameter [m]
            material (Material): Material properties
            shell_thickness (float): Shell thickness [m]
        """
        self.diameter = diameter
        self.radius = diameter / 2.0
        self.material = material
        self.volume = (4.0 / 3.0) * np.pi * (self.radius ** 3)
        self.mass = getattr(material, 'density', 5200) * self.volume # Optional density usage
        self.shell_thickness = shell_thickness
        self.volume_hydro = (1.0 + shell_thickness / self.radius)**3 * self.volume

        # Hydrodynamic diameter (optional, for reporting)
        self.d_hydro = 2.0 * (self.radius + shell_thickness)
        # Initial magnetic state (unit vector), default to z-axis
        self.magnetization_direction = np.array([0.0, 0.0, 1.0])
        

    def get_magnetic_moment_magnitude(self) -> float:
        """m = Ms * V [A*m^2]"""
        return self.material.Ms * self.volume
    
    def get_magnetic_moment_vector(self) -> np.ndarray:
        """m_vec = m * m_hat"""
        return self.get_magnetic_moment_magnitude() * self.magnetization_direction

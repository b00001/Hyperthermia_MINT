from dataclasses import dataclass

@dataclass
class Material:
    """
    Represents the material properties of a magnetic nanoparticle.
    
    Attributes:
        Ms (float): Saturation magnetization [A/m]
        K (float): Anisotropy constant [J/m^3]
        alpha (float): Damping parameter [dimensionless]
        gamma (float): Gyromagnetic ratio [rad/(s*T)]
    """
    Ms: float
    K: float    
    alpha: float = 0.1
    gamma: float = 1.76e11  # Approx for electron in rad/(s*T)

    @staticmethod
    def magnetite():
        """Returns a Material instance with properties of Magnetite (Fe3O4) approx."""
        return Material(
            Ms=4.46e5,  # ~446 kA/m
            K=1.0e4,    # ~10-20 kJ/m^3
            alpha=0.1,
            gamma=1.76e11
        )

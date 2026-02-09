import numpy as np
from abc import ABC, abstractmethod

class Field(ABC):
    """Abstract base class for external magnetic fields."""
    
    @abstractmethod
    def get_field(self, t: float) -> np.ndarray:
        """
        Calculate magnetic field vector at time t.
        
        Args:
            t (float): Time in seconds
            
        Returns:
            np.ndarray: Field vector H [A/m] of shape (3,)
        """
        pass

class AlternatingField(Field):
    """
    Alternating Magnetic Field (AMF) applied along a specific axis.
    H(t) = amplitude * cos(2 * pi * frequency * t) * direction
    """
    def __init__(self, amplitude: float, frequency: float, direction: np.ndarray = np.array([0, 0, 1])):
        self.amplitude = amplitude      # [A/m]
        self.frequency = frequency      # [Hz]
        self.direction = direction / np.linalg.norm(direction)
        
    def get_field(self, t: float) -> np.ndarray:
        return self.amplitude * np.cos(2 * np.pi * self.frequency * t) * self.direction

class StaticField(Field):
    """Constant magnetic field."""
    def __init__(self, vector: np.ndarray):
        self.vector = np.array(vector)
        
    def get_field(self, t: float) -> np.ndarray:
        return self.vector

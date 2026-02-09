import numpy as np
from scipy.spatial import ConvexHull, QhullError

class HysteresisLoop:
    """
    Class to store and analyze hysteresis loops (M vs H).
    """
    def __init__(self):
        self.H_history = []
        self.M_history = []
        self.times = []
        
    def add_point(self, t: float, H_val: float, M_val: float):
        self.times.append(t)
        self.H_history.append(H_val)
        self.M_history.append(M_val)
        
    def get_arrays(self):
        return np.array(self.times), np.array(self.H_history), np.array(self.M_history)
    
    def calculate_area(self) -> float:
        """
        Calculate the area of the hysteresis loop A = integral(M dH) or integral(H dM).
        Using trapezoidal rule or simple polygon area (shoelace formula) over one cycle.
        """
        h_arr = np.array(self.H_history)
        m_arr = np.array(self.M_history)
        
        if len(h_arr) < 3:
            return 0.0
            
        # Using trapezoidal integration approx over the data points
        # Area = Integral M dH
        area = np.trapz(m_arr, h_arr)
        return abs(area) 

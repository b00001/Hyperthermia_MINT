import numpy as np

def calculate_SAR(loop_area: float, frequency: float, density: float = 5200) -> float:
    """
    Calculate Specific Absorption Rate (SAR).
    SAR = (A * f) / rho
    
    Args:
        loop_area (float): Area of hysteresis loop [J/m^3] (Energy loss per cycle per volume)
        frequency (float): Field frequency [Hz]
        density (float): Material density [kg/m^3]
        
    Returns:
        SAR (float): [W/kg]
    """
    if density <= 0:
        return 0.0
    return (loop_area * frequency) / density

def calculate_power_loss(loop_area: float, frequency: float) -> float:
    """
    Calculate Power Loss density.
    P = A * f
    
    Args:
        loop_area: [J/m^3]
        frequency: [Hz]
    
    Returns:
        Power density [W/m^3]
    """
    return loop_area * frequency

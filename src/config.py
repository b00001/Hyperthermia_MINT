import os
import logging

logger = logging.getLogger(__name__)

def get_param(config, key, default=None, required=False):
    """
    Retrieve a parameter from config dict with warning on default fallback.
    
    Args:
        config: Dictionary of parsed config values.
        key: Parameter key to look up.
        default: Default value if key is missing.
        required: If True, raise ValueError when key is missing.
    
    Returns:
        The config value or default.
    """
    if key in config:
        return config[key]
    elif required:
        raise ValueError(f"Required parameter '{key}' missing in input file.")
    else:
        logger.warning("Parameter '%s' missing. Using default: %s", key, default)
        return default

def parse_config_file(filepath: str) -> dict:
    """
    Parses a key=value config file.
    Ignores comments starting with #.
    Attempts to convert values to float, int, or boolean.
    """
    config = {}
    if not os.path.exists(filepath):
        # Try looking one directory up if in src
        if os.path.exists(os.path.join("..", filepath)):
             filepath = os.path.join("..", filepath)
        else:
            print(f"Warning: Config file {filepath} not found.")
            return config
        
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Remove inline comments
            if '#' in line:
                line = line.split('#')[0].strip()
                
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Type inference
                if value.lower() == 'true':
                    val = True
                elif value.lower() == 'false':
                    val = False
                else:
                    try:
                        val = float(value)
                        # Check if it's actually an int
                        if val.is_integer():
                            val = int(val)
                    except ValueError:
                        val = value # Keep as string
                        
                config[key] = val
                
    return config

class SimulationConfig:
    """Default simulation parameters."""
    def __init__(
        self,
        temperature: float = 300.0,       # Temperature [K]
        viscosity: float = 0.00089,       # Viscosity of water at 25C [Pa*s]
        dt: float = 1e-12,               # Time step [s]
        tmax: float = 1e-7,               # Max simulation time [s]
        steric_stiffness: float = 1.0     # Stiffness for repulsive forces [N/m] 
    ):
        self.temperature = temperature
        self.viscosity = viscosity
        self.dt = dt
        self.tmax = tmax
        self.steric_stiffness = steric_stiffness

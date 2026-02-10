"""
Main entry point for Hyperthermia MINT Simulation.
Reads input.txt to determine execution channel.
"""
import sys
import os
from src.config import parse_config_file

def main():
    # 1. Read input configuration
    config = parse_config_file("input.txt")
    channel = config.get('channel', 'simulation')  # Default to simulation if not specified
    
    print(f"Project Runner: Executing channel '{channel}'")
    
    if channel == 'simulation':
        from src.simulation_runner import main as run_simulation
        run_simulation()
        
    elif channel == 'analysis_size':
        from src.analyze_size import run as run_analysis
        run_analysis()
        
    elif channel == 'custom_analysis':
        # Reserved for future custom loops
        try:
            from src import custom_analysis
            custom_analysis.run()
        except ImportError:
            print("Error: 'custom_analysis' module not implemented yet.")
            
    else:
        print(f"Error: Unknown channel '{channel}'. Available: simulation, analysis_size, custom_analysis")
        sys.exit(1)

if __name__ == "__main__":
    main()

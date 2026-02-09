import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation
from typing import List, Optional

from hysteresis_loop import HysteresisLoop
from config import Constants

def plot_hysteresis(hysteresis: HysteresisLoop, title: str = "Hysteresis Loop", save_path: Optional[str] = None):
    """
    Plot Magnetization vs External Field.
    """
    _, H, M = hysteresis.get_arrays()
    
    plt.figure(figsize=(8, 6))
    plt.plot(H, M, 'b-', label='M(H)')
    plt.xlabel('External Field B [T]')
    plt.ylabel('Magnetization M [A/m]')
    plt.title(title)
    plt.grid(True)
    plt.legend()
    
    if save_path:
        plt.savefig(save_path)
        plt.close() # Close to free memory if saving
    else:
        plt.show()

def plot_time_series(hysteresis: HysteresisLoop, save_path: Optional[str] = None):
    """
    Plot H(t) and M(t) over time.
    """
    times, H, M = hysteresis.get_arrays()
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    color = 'tab:red'
    ax1.set_xlabel('Time [s]')
    ax1.set_ylabel('Field B [T]', color=color)
    ax1.plot(times, H, color=color, label='H(t)')
    ax1.tick_params(axis='y', labelcolor=color)
    
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    
    color = 'tab:blue'
    ax2.set_ylabel('Magnetization M [A/m]', color=color)
    ax2.plot(times, M, color=color, label='M(t)')
    ax2.tick_params(axis='y', labelcolor=color)
    
    plt.title("Time Evolution of Field and Magnetization")
    
    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

def animate_system(
    pos_history: List[np.ndarray], 
    m_history: List[np.ndarray], 
    times: np.ndarray, 
    field=None,
    interval: int = 50, 
    save_path: Optional[str] = None
):
    """
    Create a 3D animation of particle moments and positions.
    
    Args:
        pos_history: List of (N, 3) arrays containing positions at each step.
        m_history: List of (N, 3) arrays containing magnetization directions at each step.
        times: Array of time points.
        field: Field object (to visualize external field vector). Optional.
        interval: Animation interval in ms.
        save_path: Path to save animation.
    """
    # Downsample for smoother/faster animation if needed
    # If history is too large, skip frames
    # Downsample
    n_frames = len(m_history)
    skip = max(1, n_frames // 200)
    
    m_frames = m_history[::skip]
    p_frames = pos_history[::skip] # positions also change now
    frame_times = times[::skip]
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Calculate bounds
    # Find global min/max for bounds to keep camera steady
    all_pos = np.vstack(p_frames)
    min_bound = np.min(all_pos, axis=0) - 2e-8 # padding
    max_bound = np.max(all_pos, axis=0) + 2e-8
    
    def set_axes(ax):
        ax.set_xlim(min_bound[0], max_bound[0])
        ax.set_ylim(min_bound[1], max_bound[1])
        ax.set_zlim(min_bound[2], max_bound[2])
        ax.set_xlabel('X [m]')
        ax.set_ylabel('Y [m]')
        ax.set_zlabel('Z [m]')

    arrow_length = 0.2e-7 

    def update(num):
        ax.clear()
        set_axes(ax)
        
        pos = p_frames[num]
        m = m_frames[num]
        t = frame_times[num]
        
        # 1. Plot Particles (Spheres)
        # Using scatter, size s is area in points^2. 
        # Tuning size visually for ~20nm particles. 
        ax.scatter(pos[:, 0], pos[:, 1], pos[:, 2], s=100, color='blue', alpha=0.6, label='Particle')
        
        # 2. Plot Magnetization (Arrows)
        ax.quiver(
            pos[:, 0], pos[:, 1], pos[:, 2],
            m[:, 0], m[:, 1], m[:, 2],
            length=arrow_length, normalize=True, color='red', label='Moment'
        )
        
        # 3. Plot AC Field (if provided)
        if field is not None:
            H_vec = field.get_field(t)
            # Normalize for visualization
            H_magnitude = np.linalg.norm(H_vec)
            if H_magnitude > 0:
                H_normalized = H_vec / H_magnitude
                # Plot field vector at a fixed position (corner of plot)
                field_origin = np.array([min_bound[0] + 0.1*(max_bound[0]-min_bound[0]),
                                        min_bound[1] + 0.1*(max_bound[1]-min_bound[1]),
                                        max_bound[2] - 0.2*(max_bound[2]-min_bound[2])])
                
                ax.quiver(
                    field_origin[0], field_origin[1], field_origin[2],
                    H_normalized[0], H_normalized[1], H_normalized[2],
                    length=arrow_length*1.5, normalize=False, 
                    color='green', linewidth=2, alpha=0.8, label='H field'
                )
                
                # Add field magnitude text
                ax.text(field_origin[0], field_origin[1], field_origin[2] - arrow_length*0.5,
                       f'B: {H_magnitude*Constants.mu0*1000:.1f} mT', fontsize=8, color='green')
        
        ax.set_title(f"Time: {t:.2e} s")
        ax.legend(loc='upper right')
        return ax,

    anim = animation.FuncAnimation(
        fig, update, frames=len(m_frames), interval=interval, blit=False
    )
    
    if save_path:
        # Require ffmpeg for mp4 usually, or pillow for gif
        if save_path.endswith('.mp4'):
             writer = animation.FFMpegWriter(fps=1000/interval)
             anim.save(save_path, writer=writer)
        elif save_path.endswith('.gif'):
             anim.save(save_path, writer='pillow', fps=1000/interval)
        else:
             print(f"Warning: Unknown animation extension for {save_path}, trying default save.")
             anim.save(save_path)
             
        plt.close()
    else:
        plt.show()

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.patches import Rectangle
import warnings
warnings.filterwarnings('ignore')

# Set modern style
plt.style.use('default')
sns.set_palette("husl")

# Define color palette
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#6C5CE7', '#A29BFE', '#FD79A8']

class Plot:

    def plot_resource_values(self, df, f_name):
        # Create figure with subplots
        fig = plt.figure(figsize=(16, 12))
        fig.patch.set_facecolor('white')

        # Define subplot layout (3 rows, 3 columns - with one empty space)
        gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3, left=0.08, right=0.95, top=0.90, bottom=0.08)

        # Helper function to style subplot
        def style_subplot(ax, title, ylabel, color):
            ax.set_facecolor('#f8f9fa')
            ax.spines['bottom'].set_color('#333333')
            ax.spines['left'].set_color('#333333')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.tick_params(colors='#333333', which='both')
            ax.set_xlabel('Elapsed Time (s)', color='#333333', fontsize=10)
            ax.set_ylabel(ylabel, color='#333333', fontsize=10)
            ax.set_title(title, color='#2c3e50', fontsize=12, fontweight='bold', pad=15)
            ax.grid(True, alpha=0.3, linestyle='--', color='#cccccc')

        # Add title in the top-left position (where process count was)
        ax_title = fig.add_subplot(gs[0, 0])
        ax_title.axis('off')  # Turn off axes
        ax_title.text(0.5, 0.5, 'MindsDB Resource Usage &\nMonitoring Dashboard', 
                    ha='center', va='center', fontsize=18, fontweight='bold', 
                    color='#2c3e50', transform=ax_title.transAxes)

        # Plot 1: CPU Usage
        ax1 = fig.add_subplot(gs[0, 1])
        ax1.plot(df['elapsed_time'], df['cpu'], marker='s', linewidth=3, markersize=6, color=colors[1])
        ax1.fill_between(df['elapsed_time'], df['cpu'], alpha=0.3, color=colors[1])
        style_subplot(ax1, 'CPU Usage', 'CPU %', colors[1])

        # Plot 2: Memory Usage (Real)
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.plot(df['elapsed_time'], df['mem_real'], marker='^', linewidth=3, markersize=6, color=colors[2])
        style_subplot(ax2, 'Real Memory', 'Memory (MB)', colors[2])

        # Plot 3: Virtual Memory
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.plot(df['elapsed_time'], df['mem_virtual'], marker='d', linewidth=3, markersize=6, color=colors[3])
        style_subplot(ax3, 'Virtual Memory', 'Memory (MB)', colors[3])

        # Plot 4: Read Count
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.plot(df['elapsed_time'], df['read_count'], marker='p', linewidth=3, markersize=6, color=colors[4])
        style_subplot(ax4, 'Read Operations', 'Read Count', colors[4])

        # Plot 5: Write Count
        ax5 = fig.add_subplot(gs[1, 2])
        ax5.plot(df['elapsed_time'], df['write_count'], marker='h', linewidth=3, markersize=6, color=colors[5])
        style_subplot(ax5, 'Write Operations', 'Write Count', colors[5])

        # Plot 6: Read Bytes
        ax6 = fig.add_subplot(gs[2, 0])
        read_bytes_mb = df['read_bytes'] / (1024**2)
        ax6.plot(df['elapsed_time'], read_bytes_mb, marker='*', linewidth=3, markersize=8, color=colors[6])
        ax6.fill_between(df['elapsed_time'], read_bytes_mb, alpha=0.3, color=colors[6])
        style_subplot(ax6, 'Data Read', 'Bytes (MB)', colors[6])

        # Plot 7: Write Bytes
        ax7 = fig.add_subplot(gs[2, 1])
        write_bytes_mb = df['write_bytes'] / (1024**2)
        ax7.plot(df['elapsed_time'], write_bytes_mb, marker='X', linewidth=3, markersize=6, color=colors[7])
        ax7.fill_between(df['elapsed_time'], write_bytes_mb, alpha=0.3, color=colors[7])
        style_subplot(ax7, 'Data Written', 'Bytes (MB)', colors[7])

        # Plot 8: Combined I/O Operations
        ax8 = fig.add_subplot(gs[2, 2])
        ax8.plot(df['elapsed_time'], df['read_count'], marker='o', linewidth=2, markersize=5, 
                color=colors[4], label='Read Ops', alpha=0.8)
        ax8.plot(df['elapsed_time'], df['write_count'], marker='s', linewidth=2, markersize=5, 
                color=colors[5], label='Write Ops', alpha=0.8)
        ax8.legend(facecolor='white', edgecolor='#333333', labelcolor='#333333', loc='upper left')
        style_subplot(ax8, 'I/O Operations Comparison', 'Operation Count', colors[4])

        # Add subtle gradient background effect
        for i, ax in enumerate([ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8]):
            rect = Rectangle((0, 0), 1, 1, transform=ax.transAxes, 
                            facecolor='none', edgecolor=colors[(i+1) % len(colors)], 
                            linewidth=2, alpha=0.5)
            ax.add_patch(rect)

        # Save the plot
        plt.savefig(f_name, dpi=300, bbox_inches='tight', 
                    facecolor='white', edgecolor='none')

        print(f"Dashboard saved as '{f_name}'")

    def generate_resource_usage_md(self, output_dir: str):
        try:
            df = pd.read_csv(f"{output_dir}/activity.csv")
            plot_f_name = f"{output_dir}/resource_usage.png"
            self.plot_resource_values(df, plot_f_name)
            mem_max = df["mem_real"].max()
            mem_avg = df["mem_real"].mean()
            cpu_percent_max = df["cpu"].max()
            cpu_percent_avg = df['cpu'].mean()

            return f"""#### Key Metrics
            
- **Max memory usage**: {mem_max:,.2f} MB\n
- **Average memory usage (MB)**: {mem_avg:,.2f} MB\n
- **Max CPU usage (%)**: {cpu_percent_max:,.2f}\n
- **Average CPU usage (%)**: {cpu_percent_avg:,.2f}\n

Resource usage graph:

![plot](resource_usage.png)
            """

        except Exception as e:
            print(e)
            return "Not available"
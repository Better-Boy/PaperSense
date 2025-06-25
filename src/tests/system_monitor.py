import threading
import psutil
import time
import statistics
from typing import Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.live import Live
from rich.layout import Layout

console = Console()

class SystemMonitor:
    """System resource monitoring"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.metrics = []
        
    def start_monitoring(self):
        """Start system monitoring in background thread"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1)
            
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                self.metrics.append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_info.rss / 1024 / 1024,
                    'memory_percent': self.process.memory_percent()
                })
                time.sleep(0.1)  # Sample every 100ms
            except Exception as e:
                console.print(f"[red]Monitoring error: {e}[/red]")
                break
                
    def get_peak_metrics(self) -> Dict[str, Any]:
        """Get peak resource usage metrics"""
        if not self.metrics:
            return {'peak_cpu': 0, 'peak_memory_mb': 0, 'avg_cpu': 0, 'avg_memory_mb': 0}
            
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        memory_values = [m['memory_mb'] for m in self.metrics]
        
        return {
            'peak_cpu': max(cpu_values),
            'peak_memory_mb': max(memory_values),
            'avg_cpu': statistics.mean(cpu_values),
            'avg_memory_mb': statistics.mean(memory_values)
        }
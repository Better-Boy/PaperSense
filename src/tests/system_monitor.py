import threading
import psutil
import time
import statistics
from typing import Dict, Any, List, Optional
from rich.console import Console

from src.tests.models import ResourceSnapshot
from src import config_loader
console = Console()


class ResourceMonitor:
    """Monitors system resources during function execution"""
    
    def __init__(self, process_pid: Optional[int] = None):
        self.sampling_interval = config_loader.benchmark_test.resource_sample_rate
        self.process = psutil.Process(process_pid)
        self.monitoring = False
        self.resource_snapshots: List[ResourceSnapshot] = []
        self.monitor_thread = None
        
    def _take_snapshot(self) -> Optional[ResourceSnapshot]:
        """Take a snapshot of current resource usage"""
        try:
            # Get CPU usage (non-blocking)
            cpu_percent = self.process.cpu_percent()
            
            # Get memory info
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            # Get other process info
            num_threads = self.process.num_threads()
            
            try:
                open_files = len(self.process.open_files())
            except (psutil.PermissionError, psutil.AccessDenied):
                open_files = -1
                
            try:
                network_connections = len(self.process.connections())
            except (psutil.PermissionError, psutil.AccessDenied):
                network_connections = -1
            
            # Get I/O info
            try:
                io_counters = self.process.io_counters()
                io_read_bytes = io_counters.read_bytes
                io_write_bytes = io_counters.write_bytes
            except (psutil.AccessDenied, AttributeError):
                io_read_bytes = io_write_bytes = 0
            
            # Get file descriptor count
            try:
                num_fds = self.process.num_fds()
            except (psutil.AccessDenied, AttributeError):
                num_fds = 0
            
            return ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_rss_mb=memory_info.rss / 1024 / 1024,
                memory_vms_mb=memory_info.vms / 1024 / 1024,
                num_threads=num_threads,
                open_files=open_files,
                network_connections=network_connections,
                io_read_bytes=io_read_bytes,
                io_write_bytes=io_write_bytes,
                num_fds=num_fds
            )
        except Exception as e:
            print(f"Error taking snapshot: {e}")
            return None
    
    def _monitor_resources(self):
        """Background thread function to continuously monitor resources"""
        while self.monitoring:
            snapshot = self._take_snapshot()
            if snapshot:
                self.resource_snapshots.append(snapshot)
            time.sleep(self.sampling_interval)
    
    def start_monitoring(self):
        """Start resource monitoring in a background thread"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_resources)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def get_single_snapshot(self) -> Optional[ResourceSnapshot]:
        """Get a single resource snapshot"""
        return self._take_snapshot()
    
    def clear_snapshots(self):
        """Clear all stored snapshots"""
        self.resource_snapshots.clear()

from dataclasses import dataclass
from typing import Dict


@dataclass
class ResourceSnapshot:
    """Represents a snapshot of system resources at a point in time"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_rss_mb: float
    memory_vms_mb: float
    num_threads: int
    open_files: int
    network_connections: int
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    num_fds: int = 0

@dataclass
class ExecutionResult:
    """Represents the result of a single execution"""
    operation_type: str
    batch_size: str
    data_size: int
    execution_time: float
    success: bool
    mindsdb_server_before_snapshot: ResourceSnapshot = None
    mindsdb_server_after_snapshot: ResourceSnapshot = None
    test_script_before_snapshot: ResourceSnapshot = None
    test_script_after_snapshot: ResourceSnapshot = None
    concurrent_user_cnt: int = 0
    total_latency: float = 0
    error_message: str = ""
    mindsdb_server_resource_delta: Dict[str, float] = None
    test_script_resource_delta: Dict[str, float] = None


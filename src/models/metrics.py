from dataclasses import dataclass


# Configuration Classes
# Not using pydantic as it's slower compared to dataclass due to validation, parsing
@dataclass
class PerformanceMetrics:
    """Performance metrics container"""

    total_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput_ops_per_sec: float
    latency_avg_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    error_count: int
    success_count: int


@dataclass
class ChunkMetrics:
    """Metrics for chunk processing"""

    chunk_id: str
    processing_time_ms: float
    size_bytes: int
    memory_delta_mb: float


@dataclass
class BatchMetrics:
    """Metrics for batch processing"""

    batch_id: int
    batch_size: int
    total_time_ms: float
    chunks_processed: int
    avg_chunk_time_ms: float
    memory_peak_mb: float
    errors: int


@dataclass
class FileMetrics:
    """Metrics for file processing"""

    file_id: str
    total_chunks: int
    processing_time_ms: float
    avg_chunks_per_second: float
    total_size_bytes: int
    memory_usage_mb: float

from pydantic import BaseModel, Field, field_validator
from typing import Literal
import yaml


class MindsDBInfraConfig(BaseModel):
    """Configuration for MindsDB infrastructure."""
    host: str = Field(default="127.0.0.1", description="MindsDB host address")
    port: int = Field(default=47334, description="MindsDB port number")
    mindsdb_pid: int = Field(description="MindsDB process ID")
    
    @field_validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v


class BenchmarkConfig(BaseModel):
    """Configuration for benchmark testing."""
    data_size: int = Field(description="Size of data for benchmarking", default=1000)
    test_data_path: str = Field(description="Path to test data file")
    queries_file_path: str = Field(description="Path to queries file")
    output_dir: str = Field(description="Directory for test output")
    iterations: int = Field(description="Number of iterations to run", default=1)
    
    @field_validator('data_size')
    def validate_data_size(cls, v):
        if v <= 0:
            raise ValueError('Data size must be positive')
        return v

class StressConfig(BaseModel):
    """Configuration for stress testing."""
    data_size: int = Field(description="Size of data for stress testing", default=1000)
    test_data_path: str = Field(description="Path to test data file")
    queries_file_path: str = Field(description="Path to queries file")
    output_dir: str = Field(description="Directory for test output")
    concurrent_users: int = Field(description="Number of concurrent users", default=30)
    spawn_rate: int = Field(description="Rate of spawning users", default=2)
    test_runtime: int = Field(description="Test runtime in seconds", default=30)
    
    @field_validator('data_size', 'concurrent_users', 'spawn_rate', 'test_runtime')
    def validate_positive_values(cls, v):
        if v <= 0:
            raise ValueError('Value must be positive')
        return v

class TestConfig(BaseModel):
    """Main configuration model for the entire test setup."""
    mindsdb_infra: MindsDBInfraConfig
    benchmark: BenchmarkConfig
    stress: StressConfig
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'TestConfig':
        """Load configuration from YAML file."""
        with open(yaml_path, 'r') as file:
            data = yaml.safe_load(file)
        return cls(**data)
    
    @classmethod
    def from_yaml_string(cls, yaml_string: str) -> 'TestConfig':
        """Load configuration from YAML string."""
        data = yaml.safe_load(yaml_string)
        return cls(**data)

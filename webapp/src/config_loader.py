"""Configuration loader for PaperSense application."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from .models.config import (
    PaperSenseConfig,
    MindsDBConfig,
    PostgresConfig,
    KnowledgeBaseConfig,
    AgentConfig
)


def load_config_from_yaml(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Optional path to config file. If None, uses default path.
        
    Returns:
        Dict containing raw configuration data.
        
    Raises:
        FileNotFoundError: If config file doesn't exist.
        yaml.YAMLError: If config file is invalid YAML.
    """
    if config_path is None:
        config_path = _get_config_path()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as config_file:
            data = yaml.safe_load(config_file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file: {e}")
    
    if not data:
        raise ValueError("Configuration file is empty or invalid")
    
    return data


def _get_config_path() -> Path:
    """Get the configuration file path from environment or default location."""
    config_path_str = os.getenv("PAPERSENSE_CONFIG_PATH")
    
    if config_path_str:
        return Path(config_path_str)
    
    return Path(__file__).parent.parent / 'config.yaml'


def create_config_with_env_overrides() -> PaperSenseConfig:
    """
    Create configuration with environment variable overrides.
    
    This function loads the base configuration from YAML and then applies
    environment variable overrides using Pydantic's settings management.
    
    Returns:
        Validated PaperSenseConfig instance.
    """
    # Load base configuration from YAML
    try:
        yaml_config = load_config_from_yaml()
    except (FileNotFoundError, yaml.YAMLError, ValueError):
        # If YAML config doesn't exist or is invalid, use defaults
        yaml_config = {}
    
    # Apply environment variable overrides
    env_overrides = _get_env_overrides()
    
    # Merge YAML config with environment overrides
    merged_config = _deep_merge_dicts(yaml_config, env_overrides)
    
    # Create and validate Pydantic model
    return PaperSenseConfig(**merged_config)


def _get_env_overrides() -> Dict[str, Any]:
    """Get environment variable overrides structured for Pydantic."""
    overrides = {}
    
    # MindsDB overrides
    if os.getenv("MINDSDB_HOST"):
        overrides.setdefault("MINDSDB_INFRA", {})["MINDSDB_HOST"] = os.getenv("MINDSDB_HOST")
    
    if os.getenv("MINDSDB_PORT"):
        overrides.setdefault("MINDSDB_INFRA", {})["MINDSDB_PORT"] = int(os.getenv("MINDSDB_PORT"))
    
    # PostgreSQL overrides
    postgres_env_mappings = {
        "POSTGRES_HOST": "HOST",
        "POSTGRES_PORT": "PORT",
        "POSTGRES_USER": "USER", 
        "POSTGRES_PASSWORD": "PASSWORD"
    }
    
    for env_var, config_key in postgres_env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            overrides.setdefault("POSTGRES", {})[config_key] = env_value
            # Convert port to int if it's the port field
            if config_key == "PORT":
                overrides["POSTGRES"][config_key] = int(env_value)
    
    return overrides


def _deep_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with override values taking precedence."""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


# Module-level configuration
try:
    config = create_config_with_env_overrides()
    
    # Expose individual configuration sections for backward compatibility
    mdb_infra = config.MINDSDB_INFRA
    kb = config.KNOWLEDGE_BASE
    psql = config.POSTGRES
    agent = config.AGENT
    
except Exception as e:
    print(f"Error loading configuration: {e}")
    raise


# Export configuration classes for external use
__all__ = [
    'mdb_infra',
    'kb',
    'psql', 
    'agent'
]
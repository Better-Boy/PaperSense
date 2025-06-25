"""Configuration loader for PaperSense application."""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .models.config import (
    PaperSenseConfig
)

# Configure logger for this module
logger = logging.getLogger(__name__)

def load_config_from_yaml(config_path: str) -> Dict[str, Any]:
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
    
    logger.info(f"Loading configuration from: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as config_file:
            data = yaml.safe_load(config_file)
        logger.debug(f"Successfully loaded YAML configuration with {len(data) if data else 0} top-level keys")
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in config file {config_path}: {e}")
        raise yaml.YAMLError(f"Invalid YAML in config file: {e}")
    except Exception as e:
        logger.error(f"Unexpected error reading config file {config_path}: {e}")
        raise
    
    if not data:
        logger.warning("Configuration file is empty or contains no data")
        raise ValueError("Configuration file is empty or invalid")
    
    return data


def create_config_with_env_overrides(config_path: str) -> PaperSenseConfig:
    """
    Create configuration with environment variable overrides.
    
    This function loads the base configuration from YAML and then applies
    environment variable overrides using Pydantic's settings management.
    
    Returns:
        Validated PaperSenseConfig instance.
    """
    logger.info("Creating configuration with environment variable overrides")
    
    # Load base configuration from YAML
    try:
        yaml_config = load_config_from_yaml(config_path)
        logger.info("Successfully loaded base configuration from YAML")
    except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
        logger.warning(f"Failed to load YAML config ({e}), using defaults")
        yaml_config = {}
    
    # Apply environment variable overrides
    env_overrides = _get_env_overrides()
    logger.debug(f"Found {len(env_overrides)} environment override sections")
    
    # Merge YAML config with environment overrides
    merged_config = _deep_merge_dicts(yaml_config, env_overrides)
    logger.debug("Successfully merged YAML config with environment overrides")
    
    try:
        config = PaperSenseConfig(**merged_config)
        logger.info("Successfully created and validated PaperSense configuration")
        return config
    except Exception as e:
        logger.error(f"Failed to create PaperSenseConfig: {e}")
        raise


def _get_env_overrides() -> Dict[str, Any]:
    """Get environment variable overrides structured for Pydantic."""
    logger.debug("Scanning for environment variable overrides")
    overrides = {}
    
    # MindsDB overrides
    mindsdb_host = os.getenv("MINDSDB_HOST")
    if mindsdb_host:
        overrides.setdefault("mindsdb_infra", {})["host"] = mindsdb_host
        logger.debug(f"Found MINDSDB_HOST override: {mindsdb_host}")
    
    mindsdb_port = os.getenv("MINDSDB_PORT")
    if mindsdb_port:
        try:
            port_int = int(mindsdb_port)
            overrides.setdefault("mindsdb_infra", {})["port"] = port_int
            logger.debug(f"Found MINDSDB_PORT override: {port_int}")
        except ValueError:
            logger.warning(f"Invalid MINDSDB_PORT value '{mindsdb_port}', must be an integer")

    # OpenAI API Key override
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        overrides.setdefault("knowledge_base", {})["openai_api_key"] = openai_key
        logger.debug("Found OPENAI_API_KEY override (value masked for security)")
    
    # PostgreSQL overrides
    postgres_env_mappings = {
        "POSTGRES_HOST": "host",
        "POSTGRES_PORT": "port",
        "POSTGRES_USER": "user", 
        "POSTGRES_PASSWORD": "password"
    }
    
    postgres_overrides_found = []
    for env_var, config_key in postgres_env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            overrides.setdefault("postgres", {})[config_key] = env_value
            if config_key == "port":
                try:
                    overrides["postgres"][config_key] = int(env_value)
                    postgres_overrides_found.append(f"{env_var}={env_value}")
                except ValueError:
                    logger.warning(f"Invalid POSTGRES_PORT value '{env_value}', must be an integer")
                    continue
            else:
                display_value = env_value if config_key != "password" else "***"
                postgres_overrides_found.append(f"{env_var}={display_value}")
    
    if postgres_overrides_found:
        logger.debug(f"Found PostgreSQL overrides: {', '.join(postgres_overrides_found)}")

    logger.debug(f"Total environment overrides found: {len(overrides)} sections")
    return overrides


def _deep_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with override values taking precedence."""
    logger.debug("Performing deep merge of configuration dictionaries")
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result

_config = None

def get_config() -> PaperSenseConfig:
    """Get the current configuration, loading it if necessary."""
    global _config
    if _config is None:
        default_config_path = Path(__file__).parent / 'default_config.yaml'
        _config = create_config_with_env_overrides(default_config_path)
    return _config

def set_config(config_path: Optional[Path] = None):
    """Set configuration from a specific path."""
    global _config
    _config = create_config_with_env_overrides(config_path)
    
    global mdb_infra, kb, psql, agent, app, kb_storage, benchmark_test, stress_test

    mdb_infra = _config.mindsdb_infra
    kb = _config.knowledge_base
    psql = _config.postgres
    agent = _config.agent
    app = _config.app
    kb_storage = kb.storage
    benchmark_test = _config.benchmark
    stress_test = _config.stress
    logger.info("Configuration updated successfully")


try:
    config = get_config()
    
    mdb_infra = config.mindsdb_infra
    kb = config.knowledge_base
    psql = config.postgres
    agent = config.agent
    app = config.app
    kb_storage = kb.storage
    benchmark_test = config.benchmark
    stress_test = config.stress
    logger.info("Configuration module initialized successfully")
    
except Exception as e:
    logger.critical(f"Critical error loading configuration: {e}")
    raise


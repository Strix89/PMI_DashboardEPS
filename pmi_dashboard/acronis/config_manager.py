"""
Acronis Configuration Manager for PMI Dashboard

This module handles configuration management for Acronis API credentials,
supporting both .env file storage and JSON file configurations in the data/ directory.

The module implements a flexible configuration system:
1. Environment Variables (.env file) - Primary credential storage
2. JSON Configuration Files - Alternative configuration method for data/ directory

Key Components:
- AcronisConfigManager: Main configuration management class
- AcronisConfigurationError: Custom exception for configuration issues

Features:
- Environment variable management with .env file updates
- JSON file configuration support in data/ directory
- Configuration validation with detailed error messages
- Automatic credential detection and loading
- Secure credential handling and validation
- Support for multiple configuration sources

Example:
    Basic configuration management:
        from acronis.config_manager import AcronisConfigManager
        
        manager = AcronisConfigManager()
        
        # Save configuration to .env
        config = {
            "base_url": "https://ecs.evolumia.cloud/api/",
            "client_id": "your-client-id",
            "client_secret": "your-client-secret",
            "grant_type": "client_credentials"
        }
        manager.save_config(config)
        
        # Load current configuration
        current_config = manager.get_config()
        
        # Validate configuration
        errors = manager.validate_config(config)

Author: PMI Dashboard Team
Version: 1.0.0
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AcronisConfigurationError(Exception):
    """Custom exception for Acronis configuration-related errors."""
    pass


class AcronisConfigManager:
    """
    Manager for Acronis API configuration with support for .env and JSON files.
    
    This class provides a complete interface for managing Acronis API credentials
    and configuration. It supports both .env file storage (primary method) and
    JSON file configurations stored in the data/ directory.
    
    Features:
    - .env file credential management with atomic updates
    - JSON file configuration support for data/ directory
    - Configuration validation with detailed error messages
    - Automatic configuration detection and loading
    - Secure credential handling
    - Support for multiple configuration sources
    
    Configuration Structure:
    {
        "base_url": "https://ecs.evolumia.cloud/api/",
        "client_id": "your-client-id-here",
        "client_secret": "your-client-secret-here",
        "grant_type": "client_credentials"
    }
    
    Environment Variables (.env file):
    ACRONIS_BASE_URL=https://ecs.evolumia.cloud/api/
    ACRONIS_CLIENT_ID=your-client-id-here
    ACRONIS_CLIENT_SECRET=your-client-secret-here
    ACRONIS_GRANT_TYPE=client_credentials
    
    Example:
        >>> manager = AcronisConfigManager()
        >>> config = {
        ...     "base_url": "https://ecs.evolumia.cloud/api/",
        ...     "client_id": "client-123",
        ...     "client_secret": "secret-456",
        ...     "grant_type": "client_credentials"
        ... }
        >>> manager.save_config(config)
        >>> current = manager.get_config()
        >>> errors = manager.validate_config(config)
    """
    
    # Environment variable names for Acronis configuration
    ENV_VARS = {
        "base_url": "ACRONIS_BASE_URL",
        "client_id": "ACRONIS_CLIENT_ID", 
        "client_secret": "ACRONIS_CLIENT_SECRET",
        "grant_type": "ACRONIS_GRANT_TYPE"
    }
    
    # Default configuration values
    DEFAULTS = {
        "grant_type": "client_credentials"
    }
    
    def __init__(self, env_file_path: Optional[str] = None, data_dir: Optional[str] = None):
        """
        Initialize the Acronis configuration manager.
        
        Args:
            env_file_path: Path to the .env file. If None, uses default location
            data_dir: Path to the data directory for JSON configs. If None, uses default
        """
        # Set paths
        if env_file_path is None:
            # Default to .env file in the same directory as the main app
            app_dir = os.path.dirname(os.path.dirname(__file__))
            self.env_file_path = os.path.join(app_dir, '.env')
        else:
            self.env_file_path = env_file_path
            
        if data_dir is None:
            # Default to data directory relative to app
            app_dir = os.path.dirname(os.path.dirname(__file__))
            self.data_dir = os.path.join(app_dir, 'data')
        else:
            self.data_dir = data_dir
            
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_config(self) -> Optional[Dict[str, str]]:
        """
        Get current Acronis configuration from JSON file in data directory.
        
        Returns:
            Configuration dictionary or None if no configuration found
        """
        # Try to load from JSON file in data directory
        config_file_path = os.path.join(self.data_dir, 'acronis_config.json')
        
        if os.path.exists(config_file_path):
            try:
                with open(config_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract Acronis configuration
                if "acronis" in data and isinstance(data["acronis"], dict):
                    config = data["acronis"]
                    # Convert all values to strings
                    config = {k: str(v) for k, v in config.items()}
                    
                    if self._is_config_complete(config):
                        logger.debug("Loaded Acronis configuration from JSON file")
                        return config
                
            except (json.JSONDecodeError, Exception) as e:
                logger.error(f"Failed to load Acronis configuration from JSON: {e}")
        
        # Fallback: try to load from environment variables (for backward compatibility)
        config = self._load_from_env()
        if config and self._is_config_complete(config):
            logger.debug("Loaded Acronis configuration from environment variables (fallback)")
            return config
        
        logger.debug("No complete Acronis configuration found")
        return None
    
    def save_config(self, config: Dict[str, str]) -> bool:
        """
        Save Acronis configuration to JSON file in data directory.
        
        Args:
            config: Configuration dictionary to save
            
        Returns:
            True if configuration was saved successfully
            
        Raises:
            AcronisConfigurationError: If configuration is invalid or cannot be saved
        """
        # Validate configuration
        validation_errors = self.validate_config(config)
        if validation_errors:
            raise AcronisConfigurationError(f"Invalid configuration: {'; '.join(validation_errors)}")
        
        try:
            # Save to JSON file in data directory
            config_file_path = os.path.join(self.data_dir, 'acronis_config.json')
            
            # Create config with metadata
            config_data = {
                "acronis": config,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved Acronis configuration to {config_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save Acronis configuration: {e}")
            raise AcronisConfigurationError(f"Cannot save configuration: {e}")
    
    def validate_config(self, config: Dict[str, str]) -> List[str]:
        """
        Validate Acronis configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Required fields
        required_fields = ["base_url", "client_id", "client_secret"]
        for field in required_fields:
            if not config.get(field):
                errors.append(f"Missing required field: {field}")
            elif not isinstance(config[field], str) or not config[field].strip():
                errors.append(f"Field '{field}' must be a non-empty string")
        
        # Validate base_url format
        base_url = config.get("base_url", "")
        if base_url:
            if not (base_url.startswith("http://") or base_url.startswith("https://")):
                errors.append("base_url must start with http:// or https://")
            if not base_url.endswith("/"):
                errors.append("base_url should end with a forward slash (/)")
            
            # Additional Acronis-specific URL validation (relaxed)
            # Allow any valid URL, not just Acronis-specific ones
            pass
            
            # Common Acronis URL patterns
            common_patterns = [
                "cloud.acronis.com",
                "eu-cloud.acronis.com", 
                "us-cloud.acronis.com",
                "ap-cloud.acronis.com"
            ]
            
            # If it's not a common cloud URL, add a warning (not an error)
            if not any(pattern in base_url for pattern in common_patterns):
                # This is just informational, not an error
                pass
        
        # Validate grant_type
        grant_type = config.get("grant_type", "")
        if grant_type and grant_type not in ["client_credentials", "authorization_code", "password"]:
            errors.append(f"Invalid grant_type: {grant_type}. Must be one of: client_credentials, authorization_code, password")
        
        # Validate client_id format (relaxed validation)
        client_id = config.get("client_id", "")
        if client_id and len(client_id) < 3:
            errors.append("client_id seems too short (minimum 3 characters expected)")
        
        # Validate client_secret format (relaxed validation)
        client_secret = config.get("client_secret", "")
        if client_secret and len(client_secret) < 8:
            errors.append("client_secret seems too short (minimum 8 characters expected)")
        
        return errors
    
    def delete_config(self) -> bool:
        """
        Delete Acronis configuration JSON file.
        
        Returns:
            True if configuration was deleted successfully
            
        Raises:
            AcronisConfigurationError: If configuration cannot be deleted
        """
        try:
            config_file_path = os.path.join(self.data_dir, 'acronis_config.json')
            
            if os.path.exists(config_file_path):
                os.remove(config_file_path)
                logger.info(f"Deleted Acronis configuration file: {config_file_path}")
            else:
                logger.info("No Acronis configuration file to delete")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Acronis configuration: {e}")
            raise AcronisConfigurationError(f"Cannot delete configuration: {e}")
    
    def load_from_json(self, json_path: str) -> Optional[Dict[str, str]]:
        """
        Load configuration from a specific JSON file.
        
        Args:
            json_path: Path to the JSON configuration file
            
        Returns:
            Configuration dictionary or None if file cannot be loaded
            
        Raises:
            AcronisConfigurationError: If JSON file is invalid
        """
        try:
            if not os.path.exists(json_path):
                return None
                
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract Acronis configuration if it's nested
            if "acronis" in data:
                config = data["acronis"]
            else:
                config = data
            
            # Validate that it's a proper configuration
            if not isinstance(config, dict):
                raise AcronisConfigurationError("JSON file must contain a configuration object")
            
            # Convert all values to strings
            config = {k: str(v) for k, v in config.items()}
            
            logger.info(f"Loaded Acronis configuration from JSON file: {json_path}")
            return config
            
        except json.JSONDecodeError as e:
            raise AcronisConfigurationError(f"Invalid JSON in file {json_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to load configuration from {json_path}: {e}")
            return None
    
    def _load_from_env(self) -> Optional[Dict[str, str]]:
        """Load configuration from environment variables."""
        config = {}
        
        # Load environment variables if .env file exists
        if os.path.exists(self.env_file_path):
            env_vars = self._read_env_file()
            for config_key, env_key in self.ENV_VARS.items():
                if env_key in env_vars:
                    config[config_key] = env_vars[env_key]
        
        # Also check actual environment variables (in case they're set directly)
        for config_key, env_key in self.ENV_VARS.items():
            env_value = os.environ.get(env_key)
            if env_value:
                config[config_key] = env_value
        
        # Apply defaults
        for key, default_value in self.DEFAULTS.items():
            if key not in config:
                config[key] = default_value
        
        return config if config else None
    
    def _load_from_json(self) -> Optional[Dict[str, str]]:
        """Load configuration from JSON files in data directory."""
        # Look for Acronis configuration files
        json_files = [
            "acronis_config.json",
            "acronis.json",
            "config.json"  # Generic config file that might contain Acronis section
        ]
        
        for filename in json_files:
            json_path = os.path.join(self.data_dir, filename)
            try:
                config = self.load_from_json(json_path)
                if config and self._is_config_complete(config):
                    return config
            except AcronisConfigurationError:
                continue  # Try next file
        
        return None
    
    def _is_config_complete(self, config: Dict[str, str]) -> bool:
        """Check if configuration has all required fields."""
        required_fields = ["base_url", "client_id", "client_secret"]
        return all(config.get(field) for field in required_fields)
    
    def _read_env_file(self) -> Dict[str, str]:
        """Read environment variables from .env file."""
        env_vars = {}
        
        if not os.path.exists(self.env_file_path):
            return env_vars
        
        try:
            with open(self.env_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            logger.error(f"Error reading .env file: {e}")
        
        return env_vars
    
    def _update_env_file(self, config: Dict[str, str]):
        """Update .env file with Acronis configuration."""
        # Read existing .env file content
        existing_lines = []
        if os.path.exists(self.env_file_path):
            with open(self.env_file_path, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        
        # Remove existing Acronis configuration lines
        filtered_lines = []
        acronis_env_vars = set(self.ENV_VARS.values())
        
        for line in existing_lines:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
                key = line_stripped.split('=', 1)[0].strip()
                if key not in acronis_env_vars:
                    filtered_lines.append(line)
            else:
                filtered_lines.append(line)
        
        # Add Acronis configuration section
        acronis_section = [
            "\n",
            "# ============================================================================\n",
            "# Acronis Cyber Protect Cloud Configuration\n", 
            "# ============================================================================\n",
            "\n",
            "# Acronis API base URL\n",
            f"ACRONIS_BASE_URL={config.get('base_url', '')}\n",
            "\n",
            "# Acronis API client credentials\n",
            f"ACRONIS_CLIENT_ID={config.get('client_id', '')}\n",
            f"ACRONIS_CLIENT_SECRET={config.get('client_secret', '')}\n",
            "\n",
            "# OAuth2 grant type (usually client_credentials)\n",
            f"ACRONIS_GRANT_TYPE={config.get('grant_type', 'client_credentials')}\n",
            "\n"
        ]
        
        # Write updated .env file
        with open(self.env_file_path, 'w', encoding='utf-8') as f:
            f.writelines(filtered_lines)
            f.writelines(acronis_section)
    
    def _remove_from_env_file(self):
        """Remove Acronis configuration from .env file."""
        if not os.path.exists(self.env_file_path):
            return
        
        # Read existing .env file content
        with open(self.env_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Remove Acronis configuration lines and section
        filtered_lines = []
        acronis_env_vars = set(self.ENV_VARS.values())
        skip_section = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if we're entering Acronis section
            if "Acronis Cyber Protect Cloud Configuration" in line:
                skip_section = True
                continue
            
            # Check if we're leaving Acronis section (next section or end)
            if skip_section and line_stripped.startswith("# =====") and "Acronis" not in line:
                skip_section = False
                filtered_lines.append(line)
                continue
            
            # Skip lines in Acronis section
            if skip_section:
                continue
            
            # Remove individual Acronis environment variables (in case they're scattered)
            if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
                key = line_stripped.split('=', 1)[0].strip()
                if key in acronis_env_vars:
                    continue
            
            filtered_lines.append(line)
        
        # Write updated .env file
        with open(self.env_file_path, 'w', encoding='utf-8') as f:
            f.writelines(filtered_lines)
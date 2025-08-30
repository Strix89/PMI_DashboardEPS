"""
Configuration management for PMI Dashboard
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass


class Config:
    """Application configuration class with validation and default handling."""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    HOST = os.environ.get('FLASK_HOST') or '127.0.0.1'
    PORT = int(os.environ.get('FLASK_PORT') or 5000)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes']
    
    # Application paths
    DATA_DIR = os.environ.get('DATA_DIR') or os.path.join(os.path.dirname(__file__), 'data')
    PROXMOX_CONFIG_FILE = os.environ.get('PROXMOX_CONFIG_FILE') or 'proxmox_config.json'
    
    # Proxmox default settings
    PROXMOX_DEFAULT_PORT = int(os.environ.get('PROXMOX_DEFAULT_PORT') or 8006)
    PROXMOX_SSL_VERIFY = os.environ.get('PROXMOX_SSL_VERIFY', 'False').lower() in ['true', '1', 'yes']
    PROXMOX_TIMEOUT = int(os.environ.get('PROXMOX_TIMEOUT') or 30)
    
    # Real-time update settings
    METRICS_REFRESH_INTERVAL = int(os.environ.get('METRICS_REFRESH_INTERVAL') or 10)
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    LOG_FILE = os.environ.get('LOG_FILE', '')
    
    # Security settings
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'False').lower() in ['true', '1', 'yes']
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT') or 60)
    MAX_UPLOAD_SIZE = int(os.environ.get('MAX_UPLOAD_SIZE') or 10)
    
    @classmethod
    def get_proxmox_config_path(cls) -> str:
        """Get the full path to the Proxmox configuration file."""
        if os.path.isabs(cls.PROXMOX_CONFIG_FILE):
            return cls.PROXMOX_CONFIG_FILE
        return os.path.join(cls.DATA_DIR, cls.PROXMOX_CONFIG_FILE)
    
    @classmethod
    def validate_configuration(cls) -> List[str]:
        """
        Validate configuration settings and return list of warnings/errors.
        
        Returns:
            List of validation messages (warnings and errors)
        """
        messages = []
        
        # Validate Flask settings
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            messages.append("WARNING: Using default SECRET_KEY. Change this in production!")
        
        if cls.PORT < 1 or cls.PORT > 65535:
            messages.append(f"ERROR: Invalid PORT value: {cls.PORT}")
        
        # Validate Proxmox settings
        if cls.PROXMOX_DEFAULT_PORT < 1 or cls.PROXMOX_DEFAULT_PORT > 65535:
            messages.append(f"ERROR: Invalid PROXMOX_DEFAULT_PORT value: {cls.PROXMOX_DEFAULT_PORT}")
        
        if cls.PROXMOX_TIMEOUT < 1 or cls.PROXMOX_TIMEOUT > 300:
            messages.append(f"WARNING: PROXMOX_TIMEOUT value seems unusual: {cls.PROXMOX_TIMEOUT}")
        
        # Validate metrics refresh interval
        if cls.METRICS_REFRESH_INTERVAL < 1 or cls.METRICS_REFRESH_INTERVAL > 300:
            messages.append(f"WARNING: METRICS_REFRESH_INTERVAL value seems unusual: {cls.METRICS_REFRESH_INTERVAL}")
        
        # Validate log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if cls.LOG_LEVEL not in valid_log_levels:
            messages.append(f"ERROR: Invalid LOG_LEVEL: {cls.LOG_LEVEL}. Must be one of: {', '.join(valid_log_levels)}")
        
        # Validate session timeout
        if cls.SESSION_TIMEOUT < 1 or cls.SESSION_TIMEOUT > 1440:  # Max 24 hours
            messages.append(f"WARNING: SESSION_TIMEOUT value seems unusual: {cls.SESSION_TIMEOUT}")
        
        # Validate max upload size
        if cls.MAX_UPLOAD_SIZE < 1 or cls.MAX_UPLOAD_SIZE > 1024:  # Max 1GB
            messages.append(f"WARNING: MAX_UPLOAD_SIZE value seems unusual: {cls.MAX_UPLOAD_SIZE}")
        
        return messages
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration."""
        # Ensure data directory exists
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        
        # Validate configuration
        validation_messages = Config.validate_configuration()
        for message in validation_messages:
            if message.startswith("ERROR"):
                logger.error(message)
                raise ConfigurationError(message)
            else:
                logger.warning(message)


class ProxmoxConfigManager:
    """Manager for Proxmox node configuration stored in JSON files."""
    
    def __init__(self, config_file_path: Optional[str] = None):
        """
        Initialize the Proxmox configuration manager.
        
        Args:
            config_file_path: Path to the configuration file. If None, uses Config.get_proxmox_config_path()
        """
        self.config_file_path = config_file_path or Config.get_proxmox_config_path()
        self._ensure_config_file_exists()
    
    def _ensure_config_file_exists(self):
        """Ensure the configuration file exists with proper structure."""
        if not os.path.exists(self.config_file_path) or os.path.getsize(self.config_file_path) == 0:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file_path), exist_ok=True)
            
            # Create empty configuration file
            default_config = {
                "nodes": [],
                "metadata": {
                    "version": "1.0",
                    "created_at": None,
                    "last_modified": None
                }
            }
            self._save_config(default_config)
            logger.info(f"Created new Proxmox configuration file: {self.config_file_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from JSON file.
        
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If file cannot be loaded or parsed
        """
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate basic structure
            if not isinstance(config, dict):
                raise ConfigurationError("Configuration file must contain a JSON object")
            
            if "nodes" not in config:
                config["nodes"] = []
            
            if "metadata" not in config:
                config["metadata"] = {
                    "version": "1.0",
                    "created_at": None,
                    "last_modified": None
                }
            
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except IOError as e:
            raise ConfigurationError(f"Cannot read configuration file: {e}")
    
    def _save_config(self, config: Dict[str, Any]):
        """
        Save configuration to JSON file.
        
        Args:
            config: Configuration dictionary to save
            
        Raises:
            ConfigurationError: If file cannot be saved
        """
        try:
            # Update metadata
            from datetime import datetime
            now = datetime.utcnow().isoformat() + 'Z'
            
            if config["metadata"]["created_at"] is None:
                config["metadata"]["created_at"] = now
            config["metadata"]["last_modified"] = now
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file_path), exist_ok=True)
            
            # Write configuration with proper formatting
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved Proxmox configuration to: {self.config_file_path}")
            
        except IOError as e:
            raise ConfigurationError(f"Cannot write configuration file: {e}")
    
    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """
        Get all configured Proxmox nodes.
        
        Returns:
            List of node configuration dictionaries
        """
        config = self._load_config()
        return config.get("nodes", [])
    
    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific node by its ID.
        
        Args:
            node_id: Unique identifier for the node
            
        Returns:
            Node configuration dictionary or None if not found
        """
        nodes = self.get_all_nodes()
        for node in nodes:
            if node.get("id") == node_id:
                return node
        return None
    
    def add_node(self, node_config: Dict[str, Any]) -> str:
        """
        Add a new Proxmox node configuration.
        
        Args:
            node_config: Node configuration dictionary
            
        Returns:
            The ID of the added node
            
        Raises:
            ConfigurationError: If node configuration is invalid
        """
        # Validate node configuration
        validation_errors = self._validate_node_config(node_config)
        if validation_errors:
            raise ConfigurationError(f"Invalid node configuration: {'; '.join(validation_errors)}")
        
        config = self._load_config()
        
        # Generate ID if not provided
        if "id" not in node_config:
            import uuid
            node_config["id"] = str(uuid.uuid4())
        
        # Check for duplicate IDs
        existing_ids = [node.get("id") for node in config["nodes"]]
        if node_config["id"] in existing_ids:
            raise ConfigurationError(f"Node with ID '{node_config['id']}' already exists")
        
        # Add timestamps
        from datetime import datetime
        now = datetime.utcnow().isoformat() + 'Z'
        node_config["created_at"] = now
        node_config["last_connected"] = None
        
        # Set defaults
        node_config.setdefault("enabled", True)
        node_config.setdefault("port", Config.PROXMOX_DEFAULT_PORT)
        node_config.setdefault("ssl_verify", Config.PROXMOX_SSL_VERIFY)
        
        config["nodes"].append(node_config)
        self._save_config(config)
        
        logger.info(f"Added new Proxmox node: {node_config.get('name', node_config['id'])}")
        return node_config["id"]
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing node configuration.
        
        Args:
            node_id: ID of the node to update
            updates: Dictionary of fields to update
            
        Returns:
            True if node was updated, False if not found
            
        Raises:
            ConfigurationError: If update data is invalid
        """
        config = self._load_config()
        
        for i, node in enumerate(config["nodes"]):
            if node.get("id") == node_id:
                # Create updated node config for validation
                updated_node = {**node, **updates}
                validation_errors = self._validate_node_config(updated_node)
                if validation_errors:
                    raise ConfigurationError(f"Invalid node update: {'; '.join(validation_errors)}")
                
                # Apply updates
                config["nodes"][i].update(updates)
                self._save_config(config)
                
                logger.info(f"Updated Proxmox node: {node_id}")
                return True
        
        return False
    
    def remove_node(self, node_id: str) -> bool:
        """
        Remove a node configuration.
        
        Args:
            node_id: ID of the node to remove
            
        Returns:
            True if node was removed, False if not found
        """
        config = self._load_config()
        
        for i, node in enumerate(config["nodes"]):
            if node.get("id") == node_id:
                removed_node = config["nodes"].pop(i)
                self._save_config(config)
                
                logger.info(f"Removed Proxmox node: {removed_node.get('name', node_id)}")
                return True
        
        return False
    
    def _validate_node_config(self, node_config: Dict[str, Any]) -> List[str]:
        """
        Validate a node configuration dictionary.
        
        Args:
            node_config: Node configuration to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Required fields
        required_fields = ["name", "host"]
        for field in required_fields:
            if not node_config.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate host
        host = node_config.get("host", "")
        if host and not (self._is_valid_hostname(host) or self._is_valid_ip(host)):
            errors.append(f"Invalid host format: {host}")
        
        # Validate port
        port = node_config.get("port", Config.PROXMOX_DEFAULT_PORT)
        try:
            port = int(port)
            if port < 1 or port > 65535:
                errors.append(f"Port must be between 1 and 65535: {port}")
        except (ValueError, TypeError):
            errors.append(f"Port must be a valid integer: {port}")
        
        # Validate boolean fields
        bool_fields = ["ssl_verify", "enabled"]
        for field in bool_fields:
            if field in node_config and not isinstance(node_config[field], bool):
                errors.append(f"Field '{field}' must be a boolean value")
        
        return errors
    
    def _is_valid_hostname(self, hostname: str) -> bool:
        """Check if a string is a valid hostname."""
        import re
        if len(hostname) > 253:
            return False
        
        # Allow for a single dot at the end (FQDN)
        if hostname.endswith('.'):
            hostname = hostname[:-1]
        
        allowed = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$')
        return all(allowed.match(part) for part in hostname.split('.'))
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if a string is a valid IP address."""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
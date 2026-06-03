import yaml
from typing import Any, Dict, Optional

class ConfigLoader:
    def __init__(self, config_file_path: str):
        self.config_file_path = config_file_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load the configuration from the YAML file."""
        try:
            with open(self.config_file_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {self.config_file_path} not found.")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML file: {e}")

    def get(self, path: str, default: Any = None) -> Any:
        """
        Retrieve a configuration value using a dot-separated path.
        Example path: 'application.name'
        """
        keys = path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def __call__(self, path: str) -> Any:
        return self.get(path)

    def __getattr__(self, name: str) -> 'ConfigNode':
        return ConfigNode(self, name)

class ConfigNode:
    def __init__(self, config_loader: ConfigLoader, path: str):
        self._config_loader = config_loader
        self._path = path

    def __getattr__(self, name: str) -> 'ConfigNode':
        return ConfigNode(self._config_loader, f"{self._path}.{name}")

    def __call__(self,any=None) -> Any:
        return self._config_loader.get(self._path)
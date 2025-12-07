#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        LUMINA PLUGIN SYSTEM                                   ║
║                                                                               ║
║  Extensible plugin architecture for Lumina.                                  ║
║  Allows third-party extensions and capabilities.                             ║
║                                                                               ║
║  Features:                                                                     ║
║  - Plugin discovery and loading                                               ║
║  - Standardized plugin API                                                    ║
║  - Hot-reload capabilities                                                    ║
║  - Plugin marketplace concept                                                 ║
║  - Version management                                                         ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import importlib
import importlib.util
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Type
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import threading

# ═══════════════════════════════════════════════════════════════════════════════
# PLUGIN BASE CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaPlugin(ABC):
    """Base class for all Lumina plugins."""
    
    # Plugin metadata (override in subclass)
    name: str = "BasePlugin"
    version: str = "1.0.0"
    description: str = "A Lumina plugin"
    author: str = "Unknown"
    requires: List[str] = []  # Required packages
    
    def __init__(self, lumina_context: Dict):
        """Initialize with Lumina context."""
        self.context = lumina_context
        self.enabled = True
        self._initialized = False
    
    @abstractmethod
    def on_load(self) -> bool:
        """Called when the plugin is loaded. Return True if successful."""
        pass
    
    @abstractmethod
    def on_unload(self) -> bool:
        """Called when the plugin is unloaded. Return True if successful."""
        pass
    
    def on_enable(self):
        """Called when the plugin is enabled."""
        self.enabled = True
    
    def on_disable(self):
        """Called when the plugin is disabled."""
        self.enabled = False
    
    def get_commands(self) -> Dict[str, Callable]:
        """Return a dict of commands this plugin provides."""
        return {}
    
    def get_actions(self) -> Dict[str, Callable]:
        """Return a dict of actions this plugin provides for Lumina's decision loop."""
        return {}
    
    def get_hooks(self) -> Dict[str, Callable]:
        """Return a dict of hooks this plugin wants to register."""
        return {}
    
    def get_info(self) -> Dict:
        """Get plugin information."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "initialized": self._initialized
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PLUGIN METADATA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PluginMetadata:
    """Metadata about a plugin."""
    id: str
    name: str
    version: str
    description: str
    author: str
    path: str
    enabled: bool
    loaded_at: Optional[str]
    requires: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "path": self.path,
            "enabled": self.enabled,
            "loaded_at": self.loaded_at,
            "requires": self.requires,
            "provides": self.provides
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PLUGIN REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class PluginRegistry:
    """Registry for managing plugins."""
    
    def __init__(self, plugins_path: Path):
        self.plugins_path = plugins_path
        self.plugins_path.mkdir(parents=True, exist_ok=True)
        
        self.registry_path = plugins_path / "registry.json"
        
        self.plugins: Dict[str, LuminaPlugin] = {}
        self.metadata: Dict[str, PluginMetadata] = {}
        self.hooks: Dict[str, List[Callable]] = {}
        
        self._load_registry()
    
    def _load_registry(self):
        """Load the plugin registry from disk."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                    for plugin_data in data.get("plugins", []):
                        meta = PluginMetadata(**plugin_data)
                        self.metadata[meta.id] = meta
            except Exception as e:
                print(f"Error loading plugin registry: {e}")
    
    def _save_registry(self):
        """Save the plugin registry to disk."""
        with open(self.registry_path, 'w') as f:
            json.dump({
                "plugins": [m.to_dict() for m in self.metadata.values()],
                "updated_at": datetime.now().isoformat()
            }, f, indent=2)
    
    def register(self, plugin: LuminaPlugin, path: str) -> PluginMetadata:
        """Register a plugin."""
        plugin_id = hashlib.md5(plugin.name.encode()).hexdigest()[:12]
        
        metadata = PluginMetadata(
            id=plugin_id,
            name=plugin.name,
            version=plugin.version,
            description=plugin.description,
            author=plugin.author,
            path=path,
            enabled=True,
            loaded_at=datetime.now().isoformat(),
            requires=plugin.requires
        )
        
        self.plugins[plugin_id] = plugin
        self.metadata[plugin_id] = metadata
        
        # Register hooks
        for hook_name, handler in plugin.get_hooks().items():
            if hook_name not in self.hooks:
                self.hooks[hook_name] = []
            self.hooks[hook_name].append(handler)
        
        self._save_registry()
        return metadata
    
    def unregister(self, plugin_id: str) -> bool:
        """Unregister a plugin."""
        if plugin_id in self.plugins:
            plugin = self.plugins[plugin_id]
            
            # Remove hooks
            for hook_name, handler in plugin.get_hooks().items():
                if hook_name in self.hooks:
                    self.hooks[hook_name] = [
                        h for h in self.hooks[hook_name] if h != handler
                    ]
            
            del self.plugins[plugin_id]
            del self.metadata[plugin_id]
            self._save_registry()
            return True
        return False
    
    def get(self, plugin_id: str) -> Optional[LuminaPlugin]:
        """Get a plugin by ID."""
        return self.plugins.get(plugin_id)
    
    def get_metadata(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get plugin metadata."""
        return self.metadata.get(plugin_id)
    
    def list_plugins(self) -> List[PluginMetadata]:
        """List all registered plugins."""
        return list(self.metadata.values())
    
    def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Call all handlers for a hook."""
        results = []
        for handler in self.hooks.get(hook_name, []):
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Hook {hook_name} error: {e}")
        return results
    
    def get_all_commands(self) -> Dict[str, Callable]:
        """Get all commands from all plugins."""
        commands = {}
        for plugin in self.plugins.values():
            if plugin.enabled:
                commands.update(plugin.get_commands())
        return commands
    
    def get_all_actions(self) -> Dict[str, Callable]:
        """Get all actions from all plugins."""
        actions = {}
        for plugin in self.plugins.values():
            if plugin.enabled:
                actions.update(plugin.get_actions())
        return actions


# ═══════════════════════════════════════════════════════════════════════════════
# PLUGIN LOADER
# ═══════════════════════════════════════════════════════════════════════════════

class PluginLoader:
    """Loads plugins from files."""
    
    def __init__(self, registry: PluginRegistry, lumina_context: Dict):
        self.registry = registry
        self.context = lumina_context
        self.loaded_modules: Dict[str, Any] = {}
    
    def discover(self) -> List[Path]:
        """Discover plugin files in the plugins directory."""
        plugins = []
        
        # Look for .py files
        for path in self.registry.plugins_path.glob("*.py"):
            if not path.name.startswith("_"):
                plugins.append(path)
        
        # Look for plugin directories with __init__.py
        for path in self.registry.plugins_path.iterdir():
            if path.is_dir() and (path / "__init__.py").exists():
                plugins.append(path / "__init__.py")
        
        return plugins
    
    def load_plugin(self, plugin_path: Path) -> Optional[LuminaPlugin]:
        """Load a plugin from a file."""
        try:
            # Create module spec
            module_name = f"lumina_plugin_{plugin_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            
            if spec is None or spec.loader is None:
                return None
            
            # Load module
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            self.loaded_modules[str(plugin_path)] = module
            
            # Find plugin class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, LuminaPlugin) and 
                    attr is not LuminaPlugin):
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                print(f"No plugin class found in {plugin_path}")
                return None
            
            # Instantiate plugin
            plugin = plugin_class(self.context)
            
            # Call on_load
            if plugin.on_load():
                plugin._initialized = True
                self.registry.register(plugin, str(plugin_path))
                return plugin
            else:
                print(f"Plugin {plugin.name} failed to load")
                return None
                
        except Exception as e:
            print(f"Error loading plugin {plugin_path}: {e}")
            return None
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin."""
        plugin = self.registry.get(plugin_id)
        if plugin:
            try:
                plugin.on_unload()
                return self.registry.unregister(plugin_id)
            except Exception as e:
                print(f"Error unloading plugin: {e}")
        return False
    
    def reload_plugin(self, plugin_id: str) -> Optional[LuminaPlugin]:
        """Reload a plugin."""
        metadata = self.registry.get_metadata(plugin_id)
        if not metadata:
            return None
        
        path = Path(metadata.path)
        
        # Unload
        self.unload_plugin(plugin_id)
        
        # Reload module
        if metadata.path in self.loaded_modules:
            del self.loaded_modules[metadata.path]
        
        # Load again
        return self.load_plugin(path)
    
    def load_all(self) -> List[LuminaPlugin]:
        """Load all discovered plugins."""
        plugins = []
        for path in self.discover():
            plugin = self.load_plugin(path)
            if plugin:
                plugins.append(plugin)
        return plugins


# ═══════════════════════════════════════════════════════════════════════════════
# PLUGIN WATCHER
# ═══════════════════════════════════════════════════════════════════════════════

class PluginWatcher:
    """Watches for plugin changes for hot-reload."""
    
    def __init__(self, loader: PluginLoader, interval: float = 5.0):
        self.loader = loader
        self.interval = interval
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.file_times: Dict[str, float] = {}
    
    def _get_file_time(self, path: Path) -> float:
        """Get modification time of a file."""
        try:
            return path.stat().st_mtime
        except:
            return 0
    
    def _check_changes(self):
        """Check for plugin file changes."""
        for path in self.loader.discover():
            path_str = str(path)
            current_time = self._get_file_time(path)
            
            if path_str in self.file_times:
                if current_time > self.file_times[path_str]:
                    print(f"Plugin changed: {path.name}")
                    # Find and reload the plugin
                    for meta in self.loader.registry.list_plugins():
                        if meta.path == path_str:
                            self.loader.reload_plugin(meta.id)
                            break
            
            self.file_times[path_str] = current_time
    
    def start(self):
        """Start watching for changes."""
        if self.running:
            return
        
        # Initialize file times
        for path in self.loader.discover():
            self.file_times[str(path)] = self._get_file_time(path)
        
        def watch_loop():
            while self.running:
                self._check_changes()
                time.sleep(self.interval)
        
        self.running = True
        self._thread = threading.Thread(target=watch_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop watching."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=self.interval * 2)


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA PLUGINS INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaPlugins:
    """Lumina's plugin system interface."""
    
    def __init__(self, workspace_path: Path, lumina_context: Dict = None):
        self.workspace_path = workspace_path
        self.plugins_path = workspace_path / "plugins"
        self.plugins_path.mkdir(parents=True, exist_ok=True)
        
        self.context = lumina_context or {}
        
        self.registry = PluginRegistry(self.plugins_path)
        self.loader = PluginLoader(self.registry, self.context)
        self.watcher = PluginWatcher(self.loader)
        
        # Create example plugin
        self._create_example_plugin()
        
        print(f"    🔌 Plugins: {len(self.registry.list_plugins())} loaded")
    
    def _create_example_plugin(self):
        """Create an example plugin if none exist."""
        example_path = self.plugins_path / "example_plugin.py"
        if not example_path.exists():
            example_code = '''"""Example Lumina Plugin"""

from lumina_plugins import LuminaPlugin

class ExamplePlugin(LuminaPlugin):
    name = "Example Plugin"
    version = "1.0.0"
    description = "An example plugin to demonstrate the plugin system"
    author = "Lumina Team"
    
    def on_load(self) -> bool:
        print(f"    🔌 {self.name} loaded!")
        return True
    
    def on_unload(self) -> bool:
        print(f"    🔌 {self.name} unloaded!")
        return True
    
    def get_commands(self):
        return {
            "example_hello": self.hello_command
        }
    
    def hello_command(self, name: str = "World"):
        """Say hello."""
        return f"Hello, {name}! This is from the Example Plugin."
'''
            example_path.write_text(example_code)
    
    def load_all(self) -> int:
        """Load all plugins."""
        plugins = self.loader.load_all()
        return len(plugins)
    
    def load(self, path: str) -> Optional[Dict]:
        """Load a specific plugin."""
        plugin = self.loader.load_plugin(Path(path))
        if plugin:
            return plugin.get_info()
        return None
    
    def unload(self, plugin_id: str) -> bool:
        """Unload a plugin."""
        return self.loader.unload_plugin(plugin_id)
    
    def reload(self, plugin_id: str) -> Optional[Dict]:
        """Reload a plugin."""
        plugin = self.loader.reload_plugin(plugin_id)
        if plugin:
            return plugin.get_info()
        return None
    
    def enable(self, plugin_id: str) -> bool:
        """Enable a plugin."""
        plugin = self.registry.get(plugin_id)
        if plugin:
            plugin.on_enable()
            return True
        return False
    
    def disable(self, plugin_id: str) -> bool:
        """Disable a plugin."""
        plugin = self.registry.get(plugin_id)
        if plugin:
            plugin.on_disable()
            return True
        return False
    
    def list(self) -> List[Dict]:
        """List all plugins."""
        return [m.to_dict() for m in self.registry.list_plugins()]
    
    def get_commands(self) -> Dict[str, Callable]:
        """Get all plugin commands."""
        return self.registry.get_all_commands()
    
    def get_actions(self) -> Dict[str, Callable]:
        """Get all plugin actions for Lumina's decision loop."""
        return self.registry.get_all_actions()
    
    def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Call a hook across all plugins."""
        return self.registry.call_hook(hook_name, *args, **kwargs)
    
    def start_watching(self):
        """Start watching for plugin changes."""
        self.watcher.start()
    
    def stop_watching(self):
        """Stop watching for plugin changes."""
        self.watcher.stop()
    
    def get_stats(self) -> Dict:
        """Get plugin system statistics."""
        plugins = self.registry.list_plugins()
        return {
            "total_plugins": len(plugins),
            "enabled": sum(1 for p in plugins if p.enabled),
            "commands": len(self.get_commands()),
            "actions": len(self.get_actions()),
            "hooks": list(self.registry.hooks.keys())
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_plugins(workspace_path: Path, lumina_context: Dict = None) -> LuminaPlugins:
    """Initialize Lumina's plugin system."""
    return LuminaPlugins(workspace_path, lumina_context)


PLUGINS_AVAILABLE = True


if __name__ == "__main__":
    # Test the plugin system
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    plugins = initialize_plugins(workspace)
    
    print("\n" + "=" * 50)
    print("Plugin System Test")
    print("=" * 50)
    
    # Load all plugins
    print("\nLoading plugins...")
    count = plugins.load_all()
    print(f"Loaded {count} plugins")
    
    # List plugins
    print("\nInstalled plugins:")
    for plugin in plugins.list():
        print(f"  - {plugin['name']} v{plugin['version']} ({plugin['id']})")
    
    # Get commands
    print("\nAvailable commands:")
    for cmd in plugins.get_commands():
        print(f"  - {cmd}")
    
    print("\n" + "=" * 50)
    print("Stats:", plugins.get_stats())


"""Test plugin system initialization - mock heavy dependencies"""
import sys
import json
import traceback
import types

# Mock redis module before any imports
redis_mock = types.ModuleType('redis')
redis_mock.Redis = type('Redis', (), {'__init__': lambda *a, **k: None})
sys.modules['redis'] = redis_mock

# Mock sqlalchemy modules
for mod_name in [
    'sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.ext',
    'sqlalchemy.ext.asyncio', 'sqlalchemy.ext.declarative',
    'sqlalchemy.pool', 'sqlalchemy.sql', 'sqlalchemy.types',
    'sqlalchemy.engine', 'sqlalchemy.event', 'sqlalchemy.dialects',
    'sqlalchemy.dialects.sqlite',
    'pydantic', 'passlib', 'passlib.context', 'bcrypt',
    'aiofiles',
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

sys.path.insert(0, '.')

# Directly import core module
import importlib.util
spec = importlib.util.spec_from_file_location('core', 'shared/services/plugins/plugin_manager/core.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
plugin_manager = mod.plugin_manager

results = []

try:
    # 1. Discover
    slugs = plugin_manager.discover_plugins()
    results.append(f"1. Discovered {len(slugs)} plugins: {slugs}")

    # 2. Load
    plugin_manager.load_all_plugins()
    results.append(f"2. Loaded {len(plugin_manager.plugins)} plugins")

    # 3. List each plugin
    for slug, p in plugin_manager.plugins.items():
        results.append(f"   - {slug}: {p.name} (installed={p.installed}, active={p.active})")

    # 4. Test state save
    plugin_manager._save_plugin_state()
    results.append(f"3. State file exists: {plugin_manager.state_file.exists()}")

    # 5. Test activate all
    for slug in list(plugin_manager.plugins.keys()):
        plugin_manager.activate_plugin(slug)
    active = plugin_manager.get_active_plugins()
    results.append(f"4. Active plugins after activation: {len(active)}")

    # 6. Save activated state
    plugin_manager._save_plugin_state()

    # 7. Read state file
    with open('storage/plugin_state.json', 'r') as f:
        state = json.load(f)
        results.append(f"5. State file has {len(state)} entries")
        for slug, s in state.items():
            results.append(f"   - {slug}: installed={s.get('installed')}, active={s.get('active')}")

    # 8. Test state load cycle - reset and reload
    plugin_manager2 = mod.PluginManager()
    plugin_manager2.plugins_dir = plugin_manager.plugins_dir
    plugin_manager2.state_file = plugin_manager.state_file
    plugin_manager2.load_all_plugins()
    restored = plugin_manager2._load_plugin_state()
    active2 = plugin_manager2.get_active_plugins()
    results.append(f"6. After state restore: {len(active2)} active, state_restored={restored}")

    results.append("\n=== ALL TESTS PASSED ===")

except Exception as e:
    results.append(f"ERROR: {e}")
    results.append(traceback.format_exc())

# Write results to file
with open('test_plugin_result.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

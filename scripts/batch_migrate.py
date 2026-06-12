"""Batch migrate remaining admin pages: apiClient -> adminService"""
import re

MIGRATIONS = {
    'AdminSettings.tsx': [
        # Import
        ("import {SYSTEM} from '@/lib/api/api-paths';\nimport {apiClient} from '@/lib/api/base-client';",
         "import {adminService} from '@/lib/api/admin-service';"),
        # settings list: apiClient.get(SYSTEM.SETTINGS) -> adminService.system.getSettings()
        ("apiClient.get(SYSTEM.SETTINGS)", "adminService.system.getSettings()"),
    ],
    'AdminSystem.tsx': [
        ("import {SYSTEM} from '@/lib/api/api-paths';\nimport {apiClient} from '@/lib/api/base-client';",
         "import {adminService} from '@/lib/api/admin-service';"),
        ("apiClient.get(SYSTEM.INFO)", "adminService.system.getSettings()"),
        ("apiClient.get(SYSTEM.HEALTH)", "adminService.system.getSettings()"),
    ],
    'AdminBackup.tsx': [
        ("import {SYSTEM} from '@/lib/api/api-paths';\nimport {apiClient} from '@/lib/api/base-client';",
         "import {adminService} from '@/lib/api/admin-service';"),
        ("apiClient.post(SYSTEM.BACKUP_CREATE(type))", "adminService.backup.create()"),
    ],
    'AdminPlugins.tsx': [
        ("import {apiClient} from '@/lib/api/base-client';",
         "import {adminService} from '@/lib/api/admin-service';"),
        ("apiClient.put(`/plugins/${slug}/settings`)", "adminService.plugins.updateSettings(slug, {})"),
    ],
    'AdminThemeMarketplace.tsx': [
        ("import {apiClient} from '@/lib/api/base-client';",
         "import {adminService} from '@/lib/api/admin-service';"),
        ("apiClient.get('/themes/installed')", "adminService.themes.list()"),
        ("apiClient.post('/themes/install', {slug})", "adminService.plugins.activate(slug)"),
    ],
}

for fname, rules in MIGRATIONS.items():
    path = f'frontend-astro/src/components/pages/admin/{fname}'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    changed = 0
    for old, new in rules:
        if old in c:
            c = c.replace(old, new)
            changed += 1
        else:
            # Try fuzzy: extract key part
            key = old.split('(')[0] if '(' in old else old[:30]
            # Just print warning
            pass
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print(f'{fname}: {changed} replacements')

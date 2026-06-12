"""Migrate AdminWidgetsManagement"""
path = 'frontend-astro/src/components/pages/admin/AdminWidgetsManagement.tsx'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace(
    "import {apiClient} from '@/lib/api/base-client';",
    "import {apiClient} from '@/lib/api/base-client';\nimport {adminService} from '@/lib/api/admin-service';"
)

# Line 56: list widgets  
c = c.replace(
    "apiClient.get('/cms/widgets/',",
    "adminService.widgets.list().then(r => r).catch(() => ({})).then(() => adminService.widgets.list()) || adminService.widgets.list()"
)

# Line 63: widget types
c = c.replace(
    "apiClient.get('/cms/widgets/types')",
    "adminService.widgets.listTypes()"
)

# Line 68: widget areas
c = c.replace(
    "apiClient.get('/cms/widgets/areas')",
    "adminService.widgets.listAreas()"
)

# Line 78: create
c = c.replace(
    "apiClient.post('/cms/widgets/', data)",
    "adminService.widgets.create(data)"
)

# Line 91: update
c = c.replace(
    "apiClient.put(`/cms/widgets/${id}`, data)",
    "adminService.widgets.update(id, data)"
)

# Line 103: toggle
c = c.replace(
    "apiClient.patch(`/cms/widgets/${id}/toggle`, {is_active})",
    "adminService.widgets.toggle(id, is_active)"
)

# Line 111: delete
c = c.replace(
    "apiClient.delete(`/cms/widgets/${id}`)",
    "adminService.widgets.delete(id)"
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')

with open('frontend-astro/src/components/pages/admin/PageBuilder.tsx', encoding='utf-8') as f:
    c = f.read()

replacements = [
    ("if (!res.success) throw new Error(res.error || '创建失败');",
     "if (!res.success) throw new Error(res.error || res.detail || (res.data and res.data.detail) or '创建失败');"),
    ("if (!res.success) throw new Error(res.error || '保存失败');",
     "if (!res.success) throw new Error(res.error || res.detail or '保存失败');"),
    ("if (!res.success) throw new Error(res.error || '发布失败');",
     "if (!res.success) throw new Error(res.error || res.detail or '发布失败');"),
    ("if (!res.success) throw new Error(res.error || '删除失败');",
     "if (!res.success) throw new Error(res.error || res.detail or '删除失败');"),
]

changes = 0
for old, new in replacements:
    if old in c:
        c = c.replace(old, new)
        changes += 1

with open('frontend-astro/src/components/pages/admin/PageBuilder.tsx', 'w', encoding='utf-8') as f:
    f.write(c)
print(f'Made {changes} replacements')

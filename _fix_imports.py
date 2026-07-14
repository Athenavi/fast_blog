"""Fix shared→src reverse dependencies: update imports while preserving UTF-8."""
import os

REPLACEMENTS = [
    ('from src.unified_logger import', 'from shared.logging import'),
    ('from src.setting import', 'from shared.config.settings import'),
]

count = 0
for dirpath, _, fnames in os.walk('shared'):
    for f in fnames:
        if not f.endswith('.py'):
            continue
        fp = os.path.join(dirpath, f)
        with open(fp, 'r', encoding='utf-8') as fh:
            content = fh.read()
        orig = content
        for old, new in REPLACEMENTS:
            content = content.replace(old, new)
        if content != orig:
            with open(fp, 'w', encoding='utf-8') as fh:
                fh.write(content)
            count += 1

print(f'Updated {count} files')

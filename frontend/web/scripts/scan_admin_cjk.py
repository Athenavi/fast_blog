from pathlib import Path
import re

root = Path(r"X:\project\fast_blog\frontend\web\src")
paths = list((root / "pages").rglob("*.vue")) + list((root / "components" / "admin").rglob("*.vue")) + [
    root / "components" / "Placeholder.vue"]
for path in paths:
    lines = path.read_text(encoding="utf-8").splitlines()
    hits = [(i + 1, line.strip()) for i, line in enumerate(lines) if re.search(r"[\u4e00-\u9fff]", line)]
    if hits:
        print(f"\n{path.relative_to(root)}")
        for line, text in hits:
            print(f"{line}: {text}")

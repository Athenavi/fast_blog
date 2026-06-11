import os, subprocess, sys

root = r"C:\Users\athenavi\AppData\Roaming\reasonix\global-workspace\fast_blog\src\api\v2"
packages = {
    "SEO": "seo",
    "Advanced Features": "advanced_features",
    "Performance": "performance"
}

for label, pkg in packages.items():
    print(f"=== {label} ===")
    p = os.path.join(root, pkg)
    for f in sorted(os.listdir(p)):
        if f.endswith(".py") and f != "__init__.py":
            fp = os.path.join(p, f)
            with open(fp, encoding="utf-8") as fh:
                lines = len(fh.readlines())
            print(f"  {f}: {lines} lines")
    print()

print("=== _helpers.py ===")
hp = os.path.join(root, "_helpers.py")
with open(hp, encoding="utf-8") as fh:
    lines = len(fh.readlines())
print(f"  _helpers.py: {lines} lines")

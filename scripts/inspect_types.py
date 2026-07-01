import json
from collections import defaultdict
from pathlib import Path

cfg = json.loads(Path("config.json").read_text(encoding="utf-8"))
by_type = defaultdict(list)
for s in cfg["sources"]:
    by_type[s["type"]].append(s)

for t, srcs in sorted(by_type.items()):
    keys = set()
    for s in srcs:
        keys.update(s.keys())
    print(f"{t} ({len(srcs)}): {sorted(keys - {'name', 'type'})}")
    print(f"   e.g. {srcs[0]['name']}")

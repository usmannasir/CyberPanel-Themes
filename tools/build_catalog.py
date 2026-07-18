#!/usr/bin/env python3
"""Build catalog.json: per-theme compatibility with the CyberPanel 2.4 UI.

  native  — defines the current design tokens (fully restyles the panel)
  partial — defines pre-2.4 variables the panel's theme bridge maps onto
            tokens (palette applies; old selector rules are inert)
  legacy  — only styles selectors/variables from the old UI (little or no
            visible effect on 2.4)

Run from the repo root: python3 tools/build_catalog.py
"""
import json, os, re, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'
BRIDGEABLE = (
    'background-color-first', 'background-color-second', 'background-color-third',
    'sidebar-background', 'sidebar-hover-background', 'hover-background-color',
    'content-text-color', 'link-color-first', 'text-color-first',
    'sidebar-color', 'sidebar-hover-text-color', 'hover-text-color',
    'resources-background', 'resources-text-color',
)

catalog = {}
for d in sorted(os.listdir(ROOT)):
    path = os.path.join(ROOT, d, 'design.css')
    if d.startswith(('.', 'tools')) or not os.path.exists(path):
        continue
    css = open(path, encoding='utf-8', errors='replace').read()
    decl = set(m.group(1).lower() for m in re.finditer(r'--([a-z0-9-]+)\s*:', css, re.I))
    if 'bg-primary' in decl:
        compat = 'native'
    elif any(v in decl for v in BRIDGEABLE):
        compat = 'partial'
    else:
        compat = 'legacy'
    catalog[d] = compat

out = os.path.join(ROOT, 'catalog.json')
json.dump(catalog, open(out, 'w'), indent=1, sort_keys=True)
print(json.dumps(catalog, indent=1, sort_keys=True))

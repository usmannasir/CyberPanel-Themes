#!/usr/bin/env python3
"""Generate design-v255.css for each theme folder from design.css."""
from __future__ import annotations
import re, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HEADER = """/* CyberPanel v2.5.5-dev theme pack — paste into Design > Main Dashboard CSS
   Requires cyberpanel-ui.css (v2.4.8+ shell). Legacy design.css targets the old sidebar DOM only.
   Toggle dark/light with the header moon/sun button (localStorage: cyberPanelTheme).
*/

"""
LIGHT_SELECTORS = (':root:not([data-theme="dark"])', '[data-theme="light"]')
DARK_SELECTORS = ('html[data-theme="dark"]', '[data-theme="dark"]')
ROOT_SHELL_RE = re.compile(r"^\s*--(?:bg-|text-|accent-|border-|shadow-|ai-banner|active-shadow|text-inverse)", re.MULTILINE)

def strip_comments(css):
    out, i, n = [], 0, len(css)
    while i < n:
        if css[i:i+2] == '/*':
            end = css.find('*/', i + 2)
            i = n if end == -1 else end + 2
            continue
        out.append(css[i])
        i += 1
    return ''.join(out)

def extract_rule_blocks(css):
    css = strip_comments(css)
    blocks, i, length = [], 0, len(css)
    while i < length:
        if css[i:i+2] == '/*':
            end = css.find('*/', i+2)
            i = len(css) if end == -1 else end + 2
            continue
        brace = css.find('{', i)
        if brace == -1: break
        selector = css[i:brace].strip()
        if not selector or selector.startswith('@'):
            i = brace + 1; depth = 1
            while i < length and depth:
                if css[i] == '{': depth += 1
                elif css[i] == '}': depth -= 1
                i += 1
            continue
        i = brace + 1; depth = 1; start = i
        while i < length and depth:
            if css[i] == '{': depth += 1
            elif css[i] == '}': depth -= 1
            i += 1
        blocks.append((selector, css[start:i-1]))
    return blocks

def normalize_selector(sel):
    return re.sub(r'\s+', ' ', sel.strip())

def var_lines(body):
    lines = []
    for line in body.splitlines():
        s = line.strip()
        if s.startswith('--') and ':' in s:
            lines.append('  ' + s.rstrip(';') + ';')
    return lines

def is_theme_alias_root(selector, body):
    if normalize_selector(selector) != ':root': return False
    for line in var_lines(body):
        name = line.strip().split(':', 1)[0]
        if name.startswith('--') and not re.match(r'--(?:bg-|text-|accent-)', name):
            if re.match(r'--[a-z0-9]+-', name): return True
    return bool(ROOT_SHELL_RE.search(body))

def build_pack(theme_name, css):
    blocks = extract_rule_blocks(css)
    alias_roots, light_lines, dark_lines, root_shell_lines = [], [], [], []
    for selector, body in blocks:
        norm = normalize_selector(selector)
        vars_only = var_lines(body)
        if not vars_only: continue
        if is_theme_alias_root(norm, body):
            alias_roots.append(':root {\n' + '\n'.join(vars_only) + '\n}\n'); continue
        if norm == ':root' and ROOT_SHELL_RE.search(body):
            root_shell_lines = vars_only; continue
        if any(s in norm for s in LIGHT_SELECTORS):
            if any(v.strip().startswith('--bg-') or v.strip().startswith('--accent-') for v in vars_only):
                light_lines = vars_only
            continue
        if any(s in norm for s in DARK_SELECTORS):
            if any(v.strip().startswith('--bg-') or v.strip().startswith('--accent-') for v in vars_only):
                dark_lines = vars_only
    if not light_lines and not dark_lines and not root_shell_lines and not alias_roots:
        return None
    out = [HEADER, '/* Theme: %s */\n\n' % theme_name]
    out.extend(alias_roots)
    if alias_roots: out.append('\n')
    if root_shell_lines and not light_lines:
        out.append(':root {\n' + '\n'.join(root_shell_lines) + '\n}\n\n')
        light_lines = root_shell_lines
    if light_lines:
        out.append(':root:not([data-theme="dark"]),\n[data-theme="light"] {\n' + '\n'.join(light_lines) + '\n}\n\n')
    if dark_lines:
        out.append('html[data-theme="dark"],\n[data-theme="dark"] {\n' + '\n'.join(dark_lines) + '\n}\n')
    elif light_lines:
        out.append('html[data-theme="dark"],\n[data-theme="dark"] {\n' + '\n'.join(light_lines) + '\n}\n')
    return ''.join(out)

def main():
    root = REPO_ROOT if len(sys.argv) < 2 else Path(sys.argv[1])
    generated, skipped = 0, []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.name.startswith('.'): continue
        design = path / 'design.css'
        if not design.is_file(): continue
        pack = build_pack(path.name, design.read_text(encoding='utf-8', errors='replace'))
        if pack is None:
            skipped.append(path.name); continue
        (path / 'design-v255.css').write_text(pack, encoding='utf-8')
        generated += 1
        print('OK ', path.name)
    if skipped:
        print('SKIP:', ', '.join(skipped))
    print('Generated', generated, 'file(s)')
    return 0

if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""WCAG 2.2 contrast audit/fix for CyberPanel themes — dual-mode aware.

Every theme is audited in BOTH panel modes:
  light: the theme's :root palette over the stock light tokens
  dark:  :root overlaid by the theme's [data-theme="dark"] block, over the
         stock dark tokens (what the moon-icon toggle renders)

Understands var(--x[, fallback]) indirection between theme variables (a
value that can't be resolved to a color is reported, never skipped).

Pairs: text 4.5:1 (WCAG 1.4.3), accent-as-link 4.5:1, focus ring 3:1
(1.4.11), active menu item vs sidebar 3:1 (1.4.11), sidebar text pairs.

Usage: python3 tools/contrast_audit.py [--fix] [--complete] [root]
  --complete  pin all mode-sensitive tokens in :root AND mirror the full
              effective palette into an explicit [data-theme="dark"] block
              (themes may then replace that block with a designed variant)
  --fix       minimally adjust failing colors (hue-preserving), per mode
"""
import os, re, sys, colorsys

FIX = '--fix' in sys.argv
COMPLETE = '--complete' in sys.argv
ROOT = next((a for a in sys.argv[1:] if not a.startswith('-')), '.')

DEFAULTS_LIGHT = {
    'bg-primary': '#f4f5fa', 'bg-secondary': '#ffffff', 'bg-sidebar': '#f6f7fc',
    'bg-hover': '#eceefb', 'bg-muted': '#f6f7f9', 'bg-code': '#f3f4f6',
    'text-primary': '#2f3640', 'text-secondary': '#66707e', 'text-heading': '#1e293b',
    'accent-color': '#5856d6', 'accent-hover': '#4644c0', 'text-on-accent': '#ffffff',
    'focus-ring': '#5856d6', 'border-color': '#e9ebf4',
    'table-head-bg': '#5b5fcf', 'table-head-text': '#ffffff',
    'sidebar-text': '#66707e', 'sidebar-text-muted': '#66707e',
    'sidebar-section-bg': '#5856d6', 'sidebar-section-text': '#ffffff',
    'sidebar-item-hover-bg': '#eceefb', 'sidebar-item-hover-text': '#5856d6',
    'sidebar-item-active-text': '#ffffff',
}
DEFAULTS_DARK = {
    'bg-primary': '#15161b', 'bg-secondary': '#1d1f26', 'bg-sidebar': '#191a20',
    'bg-hover': '#272a33', 'bg-muted': '#1d1f26', 'bg-code': '#23252d',
    'text-primary': '#e4e4e7', 'text-secondary': '#9aa1ad', 'text-heading': '#f3f4f6',
    'accent-color': '#7c7ff3', 'accent-hover': '#8b8ef5', 'text-on-accent': '#15161b',
    'focus-ring': '#a5a3f0', 'border-color': '#2c2f39',
    'table-head-bg': '#3b3f9e', 'table-head-text': '#f3f4f6',
    'sidebar-text': '#9aa1ad', 'sidebar-text-muted': '#9aa1ad',
    'sidebar-section-bg': '#7c7ff3', 'sidebar-section-text': '#ffffff',
    'sidebar-item-hover-bg': '#272a33', 'sidebar-item-hover-text': '#7c7ff3',
    'sidebar-item-active-text': '#ffffff',
}
# token -> token it falls back to in the panel CSS when undefined
FALLBACK_TOKEN = {
    'sidebar-text': 'text-secondary', 'sidebar-text-muted': 'text-secondary',
    'sidebar-item-hover-bg': 'bg-hover', 'sidebar-item-hover-text': 'accent-color',
    'sidebar-section-bg': 'accent-color', 'sidebar-item-active-bg': 'accent-color',
}
# legacy (pre-2.4) var -> token the panel bridge maps it to
BRIDGE = {
    'background-color-second': 'bg-primary', 'background-color-third': 'bg-secondary',
    'sidebar-background': 'bg-sidebar', 'background-color-first': 'bg-sidebar',
    'hover-background-color': 'bg-hover', 'sidebar-hover-background': 'bg-hover',
    'content-text-color': 'text-primary', 'link-color-first': 'text-primary',
    'text-color-first': 'text-heading',
}
PAIRS = [
    ('text-primary', 'bg-primary', 4.5), ('text-primary', 'bg-secondary', 4.5),
    ('text-primary', 'bg-hover', 4.5), ('text-primary', 'bg-muted', 4.5),
    ('text-primary', 'bg-code', 4.5),
    ('text-secondary', 'bg-primary', 4.5), ('text-secondary', 'bg-secondary', 4.5),
    ('text-heading', 'bg-primary', 4.5), ('text-heading', 'bg-secondary', 4.5),
    ('text-on-accent', 'accent-color', 4.5), ('text-on-accent', 'accent-hover', 4.5),
    ('accent-color', 'bg-primary', 4.5), ('accent-color', 'bg-secondary', 4.5),
    ('table-head-text', 'table-head-bg', 4.5),
    ('focus-ring', 'bg-primary', 3.0), ('focus-ring', 'bg-secondary', 3.0),
    ('focus-ring', 'bg-sidebar', 3.0),
    ('sidebar-text', 'bg-sidebar', 4.5),
    ('sidebar-section-text', 'sidebar-section-bg', 4.5),
    ('sidebar-item-hover-text', 'sidebar-item-hover-bg', 4.5),
    # active menu item must be visible against the sidebar, and legible
    ('sidebar-item-active-bg', 'bg-sidebar', 3.0),
    ('sidebar-item-active-text', 'sidebar-item-active-bg', 4.5),
]
NAMED = {'white': '#ffffff', 'black': '#000000', 'transparent': None}
MODE_SENSITIVE = list(DEFAULTS_LIGHT)  # tokens the toggle would flip if unset


def parse_color(v, under='#ffffff'):
    if v is None:
        return None
    v = re.sub(r'\s*!important\s*$', '', str(v).strip().lower())
    if v in NAMED:
        v = NAMED[v]
        if v is None:
            return None
    m = re.match(r'#([0-9a-f]{3})$', v)
    if m:
        return tuple(int(c * 2, 16) for c in m.group(1))
    m = re.match(r'#([0-9a-f]{6})', v)
    if m:
        h = m.group(1)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.match(r'rgba?\(([^)]+)\)', v)
    if m:
        parts = [p.strip() for p in re.split(r'[,/ ]+', m.group(1)) if p.strip()]
        try:
            rgb = tuple(int(float(p)) for p in parts[:3])
        except ValueError:
            return None
        if len(parts) == 4:
            a = float(parts[3].rstrip('%')) / (100 if parts[3].endswith('%') else 1)
            ub = parse_color(under) or (255, 255, 255)
            rgb = tuple(round(a * c + (1 - a) * u) for c, u in zip(rgb, ub))
        return rgb
    m = re.search(r'#([0-9a-f]{6}|[0-9a-f]{3})', v)  # first stop of a gradient
    if m:
        return parse_color('#' + m.group(1))
    return None


def lum(rgb):
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def hex_of(rgb):
    return '#%02x%02x%02x' % rgb


def hls_rgb(h, l, s):
    return tuple(round(c * 255) for c in colorsys.hls_to_rgb(h, l, s))


def shade(rgb, delta):
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    return hls_rgb(h, min(1.0, max(0.0, l + delta)), s)


def adjust(fg, bgs, need):
    """Hue-preserving lightness walk; tries both directions."""
    h, l0, s = colorsys.rgb_to_hls(*(c / 255 for c in fg))
    avg = sum(lum(b) for b in bgs) / len(bgs)
    for step in ((0.02, -0.02) if avg < 0.5 else (-0.02, 0.02)):
        l = l0
        for _ in range(60):
            rgb = hls_rgb(h, l, s)
            if all(ratio(rgb, b) >= need for b in bgs):
                return rgb
            nl = min(1.0, max(0.0, l + step))
            if nl == l:
                break
            l = nl
    return None


DARK_BLOCK_RE = re.compile(r'\[data-theme=["\']dark["\']\]\s*\{', re.I)


def split_blocks(css):
    """(root_decls, dark_decls): variable declarations outside vs inside
    [data-theme="dark"] blocks. Later declarations win within each scope."""
    dark_spans = []
    for m in DARK_BLOCK_RE.finditer(css):
        depth, i = 1, m.end()
        while i < len(css) and depth:
            if css[i] == '{':
                depth += 1
            elif css[i] == '}':
                depth -= 1
            i += 1
        dark_spans.append((m.start(), i))
    root, dark = {}, {}
    for m in re.finditer(r'--([a-z0-9-]+)\s*:\s*([^;}]+)[;}]', css, re.I):
        in_dark = any(a <= m.start() < b for a, b in dark_spans)
        (dark if in_dark else root)[m.group(1).lower()] = m.group(2).strip()
    return root, dark


def deref(value, decl, depth=0):
    """Resolve var(--x[, fallback]) chains against decl."""
    if value is None or depth > 8:
        return value
    value = re.sub(r'\s*!important\s*$', '', str(value).strip())
    m = re.match(r'var\(\s*--([a-z0-9-]+)\s*(?:,\s*([^)]+))?\)\s*$', str(value).strip(), re.I)
    if not m:
        return value
    name, fb = m.group(1).lower(), m.group(2)
    if name in decl:
        return deref(decl[name], decl, depth + 1)
    return deref(fb, decl, depth + 1) if fb else None


def make_resolver(decl, defaults, legacy):
    def resolve(token, seen=None):
        seen = seen or set()
        if token in seen:
            return None, None
        seen.add(token)
        if legacy:
            for v, t in BRIDGE.items():
                if t == token and v in decl:
                    return deref(decl[v], decl), v
        elif token in decl:
            return deref(decl[token], decl), token
        if token in FALLBACK_TOKEN:
            return resolve(FALLBACK_TOKEN[token], seen)
        return defaults.get(token), None
    return resolve


def complete_theme(decl):
    """Pin all mode-sensitive tokens from the theme's own palette (root scope)."""
    if 'bg-primary' not in decl:
        return {}
    eff = {k: deref(v, decl) for k, v in decl.items()}
    bgp = parse_color(eff.get('bg-primary'))
    if not bgp:
        return {}
    step = 0.06 if lum(bgp) < 0.5 else -0.06
    out = {}

    def pin(tok, val):
        if tok not in decl and val:
            out[tok] = val if isinstance(val, str) else hex_of(val)

    pin('bg-secondary', eff.get('bg-primary'))
    pin('bg-sidebar', eff.get('bg-primary'))
    pin('bg-hover', shade(bgp, step))
    pin('bg-muted', eff.get('bg-primary'))
    pin('bg-code', shade(bgp, step * 1.4))
    pin('text-secondary', eff.get('text-primary'))
    pin('text-heading', eff.get('text-primary'))
    acc = parse_color(eff.get('accent-color'))
    if acc:
        pin('accent-hover', shade(acc, 0.08 if lum(bgp) < 0.5 else -0.08))
        if 'text-on-accent' not in decl:
            pin('text-on-accent', '#ffffff' if ratio((255, 255, 255), acc) >= ratio((16, 16, 16), acc) else '#101010')
        pin('table-head-bg', eff.get('accent-color'))
        pin('table-head-text', eff.get('text-on-accent') or out.get('text-on-accent'))
        pin('focus-ring', eff.get('accent-color'))
    pin('border-color', hex_of(shade(bgp, step * 2)))
    return out


def audit_mode(decl, defaults, legacy):
    resolve = make_resolver(decl, defaults, legacy)
    fails, unresolved = [], []
    for fg_t, bg_t, need in PAIRS:
        fg_v, fg_src = resolve(fg_t)
        bg_v, _ = resolve(bg_t)
        fg = parse_color(fg_v, under=bg_v if isinstance(bg_v, str) else '#ffffff')
        bg = parse_color(bg_v)
        if fg_v is not None and fg is None:
            unresolved.append((fg_t, fg_v))
            continue
        if bg_v is not None and bg is None:
            unresolved.append((bg_t, bg_v))
            continue
        if not fg or not bg:
            continue
        r = ratio(fg, bg)
        if r < need:
            if fg_t.startswith('sidebar-'):
                fg_src = None   # fix by declaring the sidebar token itself
            fails.append((fg_t, bg_t, r, need, fg_src))
    return fails, unresolved


nfiles_changed, total_fail = 0, 0
themes = sorted(d for d in os.listdir(ROOT)
                if os.path.isdir(os.path.join(ROOT, d)) and not d.startswith(('.', 'tools', 'legacy-')))
for theme in themes:
    path = os.path.join(ROOT, theme, 'design.css')
    if not os.path.exists(path):
        continue
    css = open(path, encoding='utf-8', errors='replace', newline='').read()
    nl = '\r\n' if '\r\n' in css else '\n'
    root_d, dark_d = split_blocks(css)
    legacy = 'bg-primary' not in root_d

    if COMPLETE and not legacy:
        orig = css
        add = complete_theme(root_d)
        if add:
            block = (nl * 2 + '/* Mode-invariance: pin tokens the dark/light toggle would flip. */' + nl
                     + ':root {' + nl + ''.join('    --%s: %s;%s' % (k, v, nl) for k, v in sorted(add.items())) + '}' + nl)
            css += block
            root_d.update(add)
        # mirror the full effective palette into an explicit dark block so the
        # dark toggle is theme-controlled; themes may hand-tune this block.
        missing_dark = {t: deref(root_d[t], root_d) for t in MODE_SENSITIVE
                        if t in root_d and t not in dark_d and deref(root_d[t], root_d)}
        if missing_dark:
            block = (nl * 2 + '/* Dark-toggle palette: explicit so the moon icon renders a' + nl
                     + '   theme-controlled (and audited) look. Tune freely. */' + nl
                     + '[data-theme="dark"] {' + nl
                     + ''.join('    --%s: %s;%s' % (k, v, nl) for k, v in sorted(missing_dark.items())) + '}' + nl)
            css += block
            dark_d.update(missing_dark)
        if css != orig:
            open(path, 'w', encoding='utf-8', newline='').write(css)
            nfiles_changed += 1

    def run_audit():
        res = {}
        for mode, defaults in (('light', DEFAULTS_LIGHT), ('dark', DEFAULTS_DARK)):
            decl = dict(root_d)
            if mode == 'dark':
                decl.update(dark_d)
            fails, unresolved = audit_mode(decl, defaults, legacy)
            res[mode] = (fails, unresolved, decl)
        return res

    results = run_audit()

    if FIX:
        newcss = css
        for mode, (fails, _, decl) in results.items():
            defaults = DEFAULTS_DARK if mode == 'dark' else DEFAULTS_LIGHT
            resolve = make_resolver(decl, defaults, legacy)
            fixes, by_src = {}, {}
            for fg_t, bg_t, r, need, src in fails:
                by_src.setdefault((src or fg_t, need), set()).add(bg_t)
            for (src, need), bg_tokens in sorted(by_src.items()):
                bgs = [parse_color(resolve(bt)[0]) for bt in bg_tokens]
                bgs = [b for b in bgs if b]
                cur = parse_color(deref(decl.get(src), decl) or resolve(src)[0] or defaults.get(src))
                if not cur or not bgs:
                    continue
                new = adjust(cur, bgs, need)
                if new:
                    fixes[src] = hex_of(new)
                else:
                    # the foreground can't satisfy every partner (e.g. it must
                    # stay legible on other surfaces) — move each failing
                    # background toward the foreground's needs instead
                    for bt in bg_tokens:
                        bcur = parse_color(resolve(bt)[0])
                        if not bcur:
                            continue
                        nb = adjust(bcur, [cur], need)
                        if nb:
                            fixes[bt] = hex_of(nb)
            if fixes:
                scope = '[data-theme="dark"]' if mode == 'dark' else ':root'
                block = (nl * 2 + '/* WCAG contrast fixes (%s mode). */' % mode + nl
                         + scope + ' {' + nl + ''.join('    --%s: %s;%s' % (k, v, nl) for k, v in sorted(fixes.items())) + '}' + nl)
                newcss += block
        if newcss != css:
            open(path, 'w', encoding='utf-8', newline='').write(newcss)
            nfiles_changed += 1
            css = newcss
            root_d, dark_d = split_blocks(css)
            results = run_audit()

    kind = 'legacy' if legacy else ('v2+dark' if dark_d else 'v2')
    msgs = []
    # true-mode polarity: content surfaces must be light in light mode and
    # dark in dark mode (the sidebar may keep a contrary identity)
    if not legacy:
        for mode in ('light', 'dark'):
            decl = results[mode][2]
            resolve = make_resolver(decl, DEFAULTS_DARK if mode == 'dark' else DEFAULTS_LIGHT, legacy)
            for tok in ('bg-primary', 'bg-secondary', 'bg-sidebar'):
                c = parse_color(resolve(tok)[0])
                if not c:
                    continue
                l = lum(c)
                if mode == 'light' and l < 0.45:
                    msgs.append('    [light] POLARITY %s too dark (lum %.2f)' % (tok, l))
                if mode == 'dark' and l > 0.25:
                    msgs.append('    [dark] POLARITY %s too light (lum %.2f)' % (tok, l))
    for mode in ('light', 'dark'):
        fails, unresolved = results[mode][0], results[mode][1]
        total_fail += len(fails)
        for fg, bg, r, need, src in fails:
            msgs.append('    [%s] %s on %s: %.2f (need %s)%s' % (mode, fg, bg, r, need,
                        ('  [--%s]' % src) if src else ''))
        for tok, val in unresolved:
            msgs.append('    [%s] UNRESOLVED %s = %r' % (mode, tok, val))
    print('%-38s [%-7s] %s' % (theme, kind, 'OK' if not msgs else '%d issue(s)' % len(msgs)))
    for m in msgs:
        print(m)

print('\nTotal failing pairs (both modes): %d%s' % (total_fail, ' | files changed: %d' % nfiles_changed if (FIX or COMPLETE) else ''))

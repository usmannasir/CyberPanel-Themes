#!/usr/bin/env python3
"""Consolidate each theme into one clean :root + one [data-theme=dark] block.

- Folds all accumulated :root/dark correction blocks into single blocks.
- Dark themes: dark block mirrors :root (the toggle is a stable no-op).
- Light themes: derives a designed dark companion — surfaces tinted with the
  theme's accent hue, text ladder light, accent lightened for dark bgs.
- Solves every audit pair (both modes) in-memory before writing, so files
  stay clean (no appended correction blocks).

Run from repo root: python3 tools/consolidate.py
"""
import os, re, sys, colorsys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contrast_audit import (DEFAULTS_LIGHT, DEFAULTS_DARK, FALLBACK_TOKEN, PAIRS,
                            MODE_SENSITIVE, parse_color, lum, ratio, hex_of,
                            hls_rgb, shade, adjust, split_blocks, deref,
                            DARK_BLOCK_RE)

GENERATED_COMMENT = re.compile(
    r'/\*[^*]*(?:WCAG(?: 2\.2)? contrast fixes|Mode-invariance|Dark-toggle palette)[^*]*'
    r'(?:\*(?!/)[^*]*)*\*/\s*', re.I)


def strip_blocks(css):
    """Remove all :root{} and [data-theme=dark]{} blocks + generated comments."""
    spans = []
    for pat in (re.compile(r':root\s*\{', re.I), DARK_BLOCK_RE):
        for m in pat.finditer(css):
            depth, i = 1, m.end()
            while i < len(css) and depth:
                if css[i] == '{':
                    depth += 1
                elif css[i] == '}':
                    depth -= 1
                i += 1
            spans.append((m.start(), i))
    for a, b in sorted(spans, reverse=True):
        css = css[:a] + css[b:]
    css = GENERATED_COMMENT.sub('', css)
    return re.sub(r'\n{3,}', '\n\n', css).rstrip()


def effective(decl):
    out = {}
    for k, v in decl.items():
        r = deref(v, decl)
        if r:
            out[k] = re.sub(r'\s*!important\s*$', '', str(r).strip())
    return out


def solve(palette, defaults):
    """Adjust palette in place until every pair passes (or give up loudly)."""
    for _ in range(6):
        changed = False
        for fg_t, bg_t, need in PAIRS:
            fg_v = palette.get(fg_t) or palette.get(FALLBACK_TOKEN.get(fg_t, ''), None) or defaults.get(fg_t)
            bg_v = palette.get(bg_t) or palette.get(FALLBACK_TOKEN.get(bg_t, ''), None) or defaults.get(bg_t)
            fg, bg = parse_color(fg_v, under=bg_v), parse_color(bg_v)
            if not fg or not bg:
                continue
            if ratio(fg, bg) >= need:
                continue
            new = adjust(fg, [bg], need)
            if new:
                palette[fg_t] = hex_of(new)
                changed = True
            else:
                nb = adjust(bg, [fg], need)
                if nb:
                    palette[bg_t] = hex_of(nb)
                    changed = True
        if not changed:
            break
    return palette


def derive_light(dark_pal):
    """Designed light companion for an originally-dark theme: light content
    surfaces tinted with the theme hue; the dark sidebar is KEPT (it is the
    theme's identity and sidebar text already passes against it)."""
    acc = parse_color(dark_pal.get('accent-color')) or (88, 86, 214)
    h, _, sat = colorsys.rgb_to_hls(*(c / 255 for c in acc))
    tint = min(sat, 0.10)

    def surf(l):
        return hex_of(hls_rgb(h, l, tint))

    d = {
        'bg-primary': surf(0.965), 'bg-secondary': '#ffffff', 'bg-hover': surf(0.92),
        'bg-muted': surf(0.955), 'bg-code': surf(0.935), 'border-color': surf(0.86),
        'text-primary': hex_of(hls_rgb(h, 0.16, min(tint, 0.25))),
        'text-secondary': hex_of(hls_rgb(h, 0.36, min(tint, 0.20))),
        'text-heading': hex_of(hls_rgb(h, 0.10, min(tint, 0.25))),
    }
    la = adjust(acc, [parse_color('#ffffff'), parse_color(d['bg-primary'])], 4.5) or acc
    d['accent-color'] = hex_of(la)
    d['accent-hover'] = hex_of(shade(la, -0.08))
    d['text-on-accent'] = '#ffffff' if ratio((255, 255, 255), la) >= ratio((16, 16, 16), la) else '#101010'
    d['focus-ring'] = d['accent-color']
    d['table-head-bg'] = d['accent-color']
    d['table-head-text'] = d['text-on-accent']
    # keep the theme's dark sidebar + its text tokens (identity)
    for t in ('bg-sidebar', 'sidebar-text', 'sidebar-text-muted', 'sidebar-section-bg',
              'sidebar-section-text', 'sidebar-item-hover-bg', 'sidebar-item-hover-text',
              'sidebar-item-active-bg', 'sidebar-item-active-text'):
        if t in dark_pal:
            d[t] = dark_pal[t]
    return d


def derive_dark(light):
    """Designed dark companion: dark surfaces tinted with the theme's hue."""
    acc = parse_color(light.get('accent-color')) or (88, 86, 214)
    h, _, s = colorsys.rgb_to_hls(*(c / 255 for c in acc))
    tint = min(s, 0.18)

    def surf(l):
        return hex_of(hls_rgb(h, l, tint))

    d = {
        'bg-primary': surf(0.09), 'bg-secondary': surf(0.12), 'bg-sidebar': surf(0.075),
        'bg-hover': surf(0.17), 'bg-muted': surf(0.12), 'bg-code': surf(0.15),
        'border-color': surf(0.24),
        'text-primary': hex_of(hls_rgb(h, 0.90, min(tint, 0.08))),
        'text-secondary': hex_of(hls_rgb(h, 0.70, min(tint, 0.08))),
        'text-heading': hex_of(hls_rgb(h, 0.95, min(tint, 0.06))),
    }
    la = adjust(acc, [parse_color(d['bg-secondary'])], 4.5) or acc
    d['accent-color'] = hex_of(la)
    d['accent-hover'] = hex_of(shade(la, 0.08))
    d['text-on-accent'] = '#ffffff' if ratio((255, 255, 255), la) >= ratio((16, 16, 16), la) else '#101010'
    d['focus-ring'] = hex_of(adjust(la, [parse_color(d['bg-primary']),
                                         parse_color(d['bg-secondary']),
                                         parse_color(d['bg-sidebar'])], 3.0) or la)
    d['table-head-bg'] = d['accent-color']
    d['table-head-text'] = d['text-on-accent']
    d['sidebar-text'] = d['text-secondary']
    d['sidebar-text-muted'] = d['text-secondary']
    d['sidebar-section-bg'] = d['accent-color']
    d['sidebar-section-text'] = d['text-on-accent']
    d['sidebar-item-hover-bg'] = d['bg-hover']
    d['sidebar-item-hover-text'] = d['text-primary']
    if 'sidebar-item-active-bg' in light:
        d['sidebar-item-active-bg'] = d['accent-color']
        d['sidebar-item-active-text'] = d['text-on-accent']
    return d


TOKENS_ORDER = MODE_SENSITIVE + ['sidebar-item-active-bg', 'sidebar-item-active-text',
                                 'skeleton-base', 'skeleton-shine', 'border-soft']

root_dir = '.'
themes = sorted(d for d in os.listdir(root_dir)
                if os.path.isdir(d) and not d.startswith(('.', 'tools', 'legacy-')))
for theme in themes:
    path = os.path.join(theme, 'design.css')
    if not os.path.exists(path):
        continue
    css = open(path, encoding='utf-8', errors='replace', newline='').read()
    nl = '\r\n' if '\r\n' in css else '\n'
    root_d, dark_d = split_blocks(css)
    if 'bg-primary' not in root_d:
        continue
    eff_root = effective(root_d)
    eff_dark = dict(eff_root)
    eff_dark.update(effective({**root_d, **dark_d}))

    light_pal = {k: v for k, v in eff_root.items() if k in TOKENS_ORDER or not k.startswith(
        ('bg-', 'text-', 'accent-', 'sidebar-', 'table-', 'focus-', 'border-', 'skeleton-'))}
    is_dark_theme = lum(parse_color(eff_root['bg-primary']) or (255, 255, 255)) < 0.5
    if is_dark_theme:
        # true-mode polarity: the original dark design becomes the DARK block;
        # light mode gets a designed light companion that keeps the identity
        dark_pal = {k: v for k, v in eff_dark.items() if k in TOKENS_ORDER}
        light_pal = derive_light(dark_pal)
    else:
        dark_pal = derive_dark({k: v for k, v in eff_root.items() if k in TOKENS_ORDER})

    solve(light_pal, DEFAULTS_LIGHT)
    solve(dark_pal, DEFAULTS_DARK)

    custom = {k: v for k, v in root_d.items() if k not in TOKENS_ORDER}
    body = strip_blocks(css)

    def block(scope, pal, note):
        keys = [k for k in TOKENS_ORDER if k in pal] + sorted(k for k in pal if k not in TOKENS_ORDER)
        out = nl + '/* ' + note + ' */' + nl + scope + ' {' + nl
        out += ''.join('    --%s: %s;%s' % (k, pal[k], nl) for k in keys)
        return out + '}' + nl

    newcss = body + nl
    if custom:
        newcss += nl + ':root {' + nl + ''.join(
            '    --%s: %s;%s' % (k, re.sub(r'\s*!important\s*$', '', v), nl) for k, v in custom.items()) + '}' + nl
    newcss += block(':root', {k: v for k, v in light_pal.items() if k in TOKENS_ORDER},
                    'Theme palette (light / default mode) — WCAG 2.2 audited')
    newcss += block('[data-theme="dark"]', dark_pal,
                    'Dark-toggle palette — theme-controlled, WCAG 2.2 audited')
    open(path, 'w', encoding='utf-8', newline='').write(newcss)
    print('consolidated', theme, '(designed light companion)' if is_dark_theme else '(designed dark companion)')

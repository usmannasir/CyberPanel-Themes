# CyberPanel Themes

Themes you can apply to CyberPanel and make it look good :D

*NOTE: If you are running CyberPanel 2.1.1 and below use the `legacy` branch.* <br>
*NOTE 2: This doesn't override the login and file manager CSS like the `legacy` branch. Since it is not supported to do so yet.*

## How to Install

1. Go to the folder of your chosen theme
2. Click design.css
3. Copy everything in the file.
4. Go to CyberPanel > Design
5. Paste the contents of design.css to the text area.
6. Save.

## How to Remove

Remove everything from the `Design` text area.

## Troubleshooting

Try clearing cache on your web browser.

### CyberPanel by [usmannasir](https://github.com/usmannasir)

## CyberPanel v2.5.5-dev (v2.4.8+ shell)

The panel shell changed in v2.4.8: flat sidebar (`#sidebar`), `cyberpanel-ui.css`, and `data-theme` light/dark toggle.

| File | Use |
|------|-----|
| `design.css` | Legacy CyberPanel (< 2.4.8) only. Targets `#page-sidebar` / `#sidebar-menu`. |
| `design-v255.css` | **Use this on v2.5.5-dev.** Paste into **Design > Main Dashboard CSS**. |

### Install on v2.5.5-dev

1. Open the theme folder.
2. Copy all of `design-v255.css`.
3. CyberPanel > **Design** > paste into the text area > **Save**.
4. Hard refresh (`Ctrl+Shift+R`) and use the header **moon/sun** button to switch themes.

### Repository layout

Themes live in `newstargeted.com/cyberPanel-repos/cyberpanel-themes` (fork of [master3395/CyberPanel-Themes](https://github.com/master3395/CyberPanel-Themes)).


### VJ themes (synced from upstream)

| Folder | CyberPanel version |
|--------|-------------------|
| `VJ-Theme-*-v2` | **2.4.8+ / 2.5.5-dev** (unified login + dashboard + dark toggle) |
| `legacy-VJ-Theme-*` | **Before 2.4.8** (old `#page-sidebar` DOM only) |

Upstream source: [usmannasir/CyberPanel-Themes](https://github.com/usmannasir/CyberPanel-Themes). This fork adds `design-v255.css` for every theme that supports the new shell.

### Regenerate `design-v255.css`

After editing `design.css`, run:

```bash
python3 scripts/generate-design-v255.py
```

Legacy-only themes without shell variables (for example `l-dark-theme`) keep a hand-maintained `design-v255.css` approximation.

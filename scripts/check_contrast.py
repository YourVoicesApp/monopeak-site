#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Is the text on this dark page actually readable?

A dark theme is where contrast quietly fails. On a light page a colour that is
a little too pale still reads; on #0D0E12 a grey that looks fine to the eye
that chose it can fall under the line for anyone else — and nothing in the
markup says so. So the palette is measured rather than admired: every colour
the page sets on text is run against the ground it sits on, by the WCAG 2
formula, and the ratio is printed whether it passes or not.

The thresholds are the standard ones: 4.5:1 for body text, 3:1 for text at
24px or above (and for a mark that only separates two links).

  python3 scripts/check_contrast.py        # the exit status is the verdict
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, 'site', 'assets', 'site.css')

# what                                  foreground   on        least
PAIRS = [
    ('body text',                        '--ink',    '--ground', 4.5),
    ('the sentence under the heading',   '--ink2',   '--ground', 4.5),
    ('the line that names the company',  '--muted',  '--ground', 4.5),
    ('a link',                           '--gold',   '--ground', 4.5),
    ('a card’s text',               '--ink2',   '--card',   4.5),
    ('a card’s address line',       '--gold',   '--card',   4.5),
    ('the language under a card',        '--muted',  '--card',   4.5),
    ('the heading of a section',         '--muted',  '--ground', 4.5),
    ('the heading on the page',          '--ink',    '--ground', 3.0),
    ('the copyright line',               '--muted',  '--ground', 4.5),
    ('the dot between two links',        '--muted',  '--ground', 3.0),
]


def say(v, line):
    print('  %-6s %s' % (v, line))


def tokens():
    s = open(CSS, encoding='utf-8').read()
    root = s[s.index(':root {'):s.index('}', s.index(':root {'))]
    return dict(re.findall(r'(--[a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})', root))


def lum(hexv):
    r, g, b = (int(hexv[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def stray():
    """A colour written outside the palette is a colour this file never measures.

    The table above pairs tokens, so it is only worth anything if every colour
    on the page comes from one. The first run of this guard passed a line it
    had no business passing for exactly that reason: it asserted the separator
    between two links was `--muted` while the stylesheet set it to `--line`,
    and a guard that measures a colour the page does not use is green for the
    wrong reason. `rgba()` in a shadow is allowed; a shadow is not text."""
    s = open(CSS, encoding='utf-8').read()
    body = s[s.index('}', s.index(':root {')):]
    out = []
    for n, line in enumerate(body.splitlines(), s[:s.index('}', s.index(':root {'))].count('\n') + 1):
        if 'box-shadow' in line:
            continue
        for m in re.finditer(r'#[0-9A-Fa-f]{3,8}\b', line):
            out.append('line %d: %s' % (n, line.strip()))
            break
    return out


def main():
    t = tokens()
    if len(t) < 8:
        say('FAIL', 'only %d colours were read out of the stylesheet, so nothing was compared' % len(t))
        return 1
    bad = 0
    for what, fg, bg, least in PAIRS:
        f = t.get(fg, fg)
        b = t.get(bg, bg)
        if not (f.startswith('#') and b.startswith('#')):
            say('FAIL', '%s: %s or %s is not a colour this file declares' % (what, fg, bg))
            bad = 1
            continue
        r = ratio(f, b)
        line = '%s: %s on %s is %.1f:1 (needs %.1f)' % (what, f, b, r, least)
        if r + 0.05 < least:
            say('FAIL', line)
            bad = 1
        else:
            say('PASS', line)
    loose = stray()
    if loose:
        say('FAIL', 'a colour is written outside the palette, so it is never measured:')
        for l in loose:
            say('', '  %s' % l)
        bad = 1
    else:
        say('PASS', 'every colour on the page comes from the palette, so the table above covers them all')
    print()
    print('every colour on this page clears the line' if not bad
          else 'A COLOUR ON THIS PAGE IS TOO FAINT TO READ')
    return bad


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Is the first screen actually on the first screen?

A sentence in the HTML is not a sentence a visitor sees. The app round of this
same week cost two days to that difference twice: a widget in the tree is not a
control on the glass, and an unconditional 9px spacer beside something that
draws nothing took 6.2px off a bar that had 2.8px of margin. A page is the same
kind of object, so the claim «one clean first screen» is read off a renderer at
a stated width rather than argued about.

What it asserts, per page and per width:

  * every part of the first screen is inside the viewport — the mark, the title,
    the idea, the sentence about whose word it is, the state of the build, and
    both buttons. Not «present in the document»: `bottom <= viewport height`.
  * nothing overflows sideways: `scrollWidth <= innerWidth + 1`.
  * the two buttons sit on the glass with a real height, so neither is a
    zero-size element a finder would still report as found.

How, and why it is safe: the pages are copied to a temporary folder and the
probe is injected into the COPY. `site/` is never written to — the promise that
this site carries no JavaScript is one of the things being protected, so the
guard may not be the thing that breaks it. The copy is under the system temp
directory and is removed on the way out.

  python3 scripts/measure_first_screen.py            # the verdict is the exit status
  python3 scripts/measure_first_screen.py --keep     # leave the copy to look at
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')

# The widths: a common laptop, a small laptop, and a phone. The phone is the one
# that matters — it is where a hero built at 1440 falls apart.
WIDTHS = [(1366, 768), (1280, 800), (390, 844)]

# page : the parts its first screen must hold
PAGES = {
    'index.html': {
        'mark': '.hero-mark',
        'title': 'h1',
        'languages': '.cards',
        'where the projects are': '.links',
    },
    'sv/index.html': {
        'mark': 'header.top .mark img',
        'title': 'h1',
        'idea': '.hero-idea',
        'word': '.hero-word',
        # The page's practical job is to hand a reader on to Z, so the first
        # project card is part of the first screen, not something below it.
        'the first project': '.projs .proj',
    },
}
for _l in ('en', 'de', 'ar'):
    PAGES[_l + '/index.html'] = PAGES['sv/index.html']

PROBE = """
<script>
(function () {
  var want = %s;
  // Which menu to open, if any. The two <details> carry the same `name`, so a
  // browser that knows exclusive accordions will only ever hold one open —
  // which is also what a person gets, so they are measured one at a time.
  var pick = location.search.match(/menu=(\\d+)/);
  var menus = document.querySelectorAll('details.menu');
  if (pick && menus[+pick[1]]) { menus[+pick[1]].open = true; }
  var out = {vw: window.innerWidth, vh: window.innerHeight,
             sw: document.documentElement.scrollWidth, items: {}, panels: [], menus: menus.length};
  for (var k in want) {
    var e = document.querySelector(want[k]);
    if (!e) { out.items[k] = null; continue; }
    var r = e.getBoundingClientRect();
    out.items[k] = {top: Math.round(r.top), bottom: Math.round(r.bottom),
                    left: Math.round(r.left), right: Math.round(r.right),
                    w: Math.round(r.width), h: Math.round(r.height)};
  }
  var open = document.querySelectorAll('details.menu[open] .menu-panel');
  for (var i = 0; i < open.length; i++) {
    var p = open[i].getBoundingClientRect();
    out.panels.push({top: Math.round(p.top), bottom: Math.round(p.bottom),
                     left: Math.round(p.left), right: Math.round(p.right),
                     w: Math.round(p.width), h: Math.round(p.height)});
  }
  var pre = document.createElement('pre');
  pre.id = 'z-measure';
  pre.textContent = '@@' + JSON.stringify(out) + '@@';
  document.body.appendChild(pre);
})();
</script>
</body>"""


def chrome():
    for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'):
        path = shutil.which(name)
        if path:
            return path
    return None


def measure(binary, page, w, h, menu=None):
    url = 'file://' + page + ('?menu=%d' % menu if menu is not None else '')
    cmd = [binary, '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
           '--force-device-scale-factor=1', '--virtual-time-budget=4000',
           '--window-size=%d,%d' % (w, h), '--dump-dom', url]
    run = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=120)
    found = re.search(r'@@(\{.*?\})@@', run.stdout.decode('utf-8', 'replace'), re.S)
    if not found:
        return None
    return json.loads(found.group(1))


def main():
    binary = chrome()
    if binary is None:
        print('  FAIL   no browser on this machine, so the first screen was not measured')
        return 1

    work = tempfile.mkdtemp(prefix='zprivacy-first-screen-')
    keep = '--keep' in sys.argv
    bad = 0
    try:
        copy = os.path.join(work, 'site')
        shutil.copytree(SITE, copy)
        for page, want in PAGES.items():
            path = os.path.join(copy, page)
            with open(path, encoding='utf-8') as fh:
                html = fh.read()
            assert html.count('</body>') == 1, page
            assert '<script' not in html, '%s already carries a script' % page
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(html.replace('</body>', PROBE % json.dumps(want)))

        for page, want in PAGES.items():
            for w, h in WIDTHS:
                got = measure(binary, os.path.join(copy, page), w, h)
                if got is None:
                    print('  FAIL   %s at %dx%d: the browser said nothing' % (page, w, h))
                    bad += 1
                    continue
                vh, vw = got['vh'], got['vw']
                for name in sorted(want):
                    box = got['items'].get(name)
                    if box is None:
                        print('  FAIL   %s at %dx%d: no %s on the page at all' % (page, w, h, name))
                        bad += 1
                    elif box['h'] <= 0 or box['w'] <= 0:
                        print('  FAIL   %s at %dx%d: %s is %dx%d, so it is found but not drawn'
                              % (page, w, h, name, box['w'], box['h']))
                        bad += 1
                    elif box['bottom'] > vh:
                        print('  FAIL   %s at %dx%d: %s ends at y=%d, below the first screen (%d)'
                              % (page, w, h, name, box['bottom'], vh))
                        bad += 1
                    elif box['left'] < 0 or box['right'] > vw:
                        print('  FAIL   %s at %dx%d: %s runs from x=%d to x=%d, off a %d-wide screen'
                              % (page, w, h, name, box['left'], box['right'], vw))
                        bad += 1
                if got['sw'] > vw + 1:
                    print('  FAIL   %s at %dx%d: the page is %dpx wide and the screen is %d'
                          % (page, w, h, got['sw'], vw))
                    bad += 1

                # The menus, one at a time, because the two <details> are an
                # exclusive pair. Two things are asked of an open one: that the
                # panel is wholly on the glass, and that **nothing below it
                # moved** — a menu that pushes the page down pushes a button
                # under the ruler, which is the owner's own objection to the
                # four buttons that used to stand here.
                for which in range(got.get('menus', 0)):
                    opened = measure(binary, os.path.join(copy, page), w, h, menu=which)
                    if opened is None or not opened['panels']:
                        print('  FAIL   %s at %dx%d: menu %d opens nothing'
                              % (page, w, h, which))
                        bad += 1
                        continue
                    for box in opened['panels']:
                        if box['left'] < 0 or box['right'] > vw:
                            print('  FAIL   %s at %dx%d: menu %d runs from x=%d to x=%d, off a '
                                  '%d-wide screen' % (page, w, h, which, box['left'], box['right'], vw))
                            bad += 1
                        elif box['bottom'] > vh:
                            print('  FAIL   %s at %dx%d: menu %d ends at y=%d, below the glass (%d)'
                                  % (page, w, h, which, box['bottom'], vh))
                            bad += 1
                        elif box['h'] <= 0 or box['w'] <= 0:
                            print('  FAIL   %s at %dx%d: menu %d opens to nothing (%dx%d)'
                                  % (page, w, h, which, box['w'], box['h']))
                            bad += 1
                    moved = [n for n in want
                             if got['items'].get(n) and opened['items'].get(n)
                             and got['items'][n]['top'] != opened['items'][n]['top']]
                    if moved:
                        n = moved[0]
                        print('  FAIL   %s at %dx%d: opening menu %d moved %s from y=%d to y=%d'
                              % (page, w, h, which, n, got['items'][n]['top'],
                                 opened['items'][n]['top']))
                        bad += 1

                if not bad:
                    last = max(b['bottom'] for b in got['items'].values() if b)
                    print('  PASS   %-16s %4dx%-4d first screen ends at y=%d of %d%s'
                          % (page, w, h, last, vh,
                             ', %d menus open on the glass without moving it' % got['menus']
                             if got.get('menus') else ''))
    finally:
        if keep:
            print('\n  the copy with the probe in it: %s' % work)
        else:
            shutil.rmtree(work, ignore_errors=True)

    print()
    print('the first screen holds at every width' if not bad
          else 'THE FIRST SCREEN DOES NOT HOLD (%d)' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

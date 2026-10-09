#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The list of pages given to Google, walked and compared with the pages that exist.

The lead's instruction for the Google round: «حارس يمشي على القائمة ويقارنها
بالملفات المبنية أفضل من عين» — a guard that walks the list and compares it
with the built files beats an eye.

An eye is exactly what fails here. A sitemap is nine lines that all look alike,
it is read by a machine and never by a person, and nothing on the site goes red
when one of them is wrong: a page left out is simply never indexed, and a page
listed that does not exist is a 404 reported back to the owner in Search
Console weeks later. So the comparison runs **both ways**:

  1. every `<loc>` resolves to a page in the tree that will be uploaded;
  2. every page in that tree appears in the list, exactly once;
  3. every `<loc>` is the address that page itself calls canonical, so the
     sitemap and the page cannot drift apart;
  4. every `<url>` carries a `lastmod` that is a real date and not in the
     future;
  5. the `xhtml:link` alternates inside a `<url>`, where there are any, say the
     same thing as that page's own `<link rel="alternate">` block.

Point 3 is the one that makes this cheap to keep: `check_site.sh` already
derives each page's canonical from its path, so one of the two is always
anchored to the filesystem.

  python3 scripts/check_sitemap.py        # the exit status is the verdict
"""
import datetime
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
HOST = 'https://mono-peak.com'
SM = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
XH = '{http://www.w3.org/1999/xhtml}'


def say(verdict, line):
    print('  %-6s %s' % (verdict, line))


def pages():
    """Every page that will be served, with the address its path gives it."""
    out = {}
    for dirpath, _dirs, files in os.walk(SITE):
        if 'index.html' in files:
            rel = os.path.relpath(dirpath, SITE).replace(os.sep, '/')
            rel = '' if rel == '.' else rel + '/'
            out[HOST + '/' + rel] = os.path.join(dirpath, 'index.html')
    return out


def head_alternates(path):
    """What the page itself says its language versions are: hreflang -> absolute."""
    with open(path, encoding='utf-8') as fh:
        html = fh.read()
    found = {}
    for tag in re.findall(r'<link[^>]+rel="alternate"[^>]*>', html):
        lang = re.search(r'hreflang="([^"]+)"', tag)
        href = re.search(r'href="([^"]+)"', tag)
        if lang and href:
            found[lang.group(1)] = HOST + href.group(1) if href.group(1).startswith('/') else href.group(1)
    return found


def verdict(bad):
    print()
    print('the sitemap and the tree are the same pages' if not bad
          else 'THE SITEMAP AND THE TREE DISAGREE')
    return bad


def main():
    smpath = os.path.join(SITE, 'sitemap.xml')
    if not os.path.exists(smpath):
        say('FAIL', 'there is no site/sitemap.xml, so no page is offered to a crawler')
        return verdict(1)
    try:
        root = ET.parse(smpath).getroot()
    except ET.ParseError as exc:
        say('FAIL', 'sitemap.xml is not well-formed XML, so a crawler reads none of it: %s' % exc)
        return verdict(1)
    if root.tag != SM + 'urlset':
        say('FAIL', 'sitemap.xml has <%s> at its root, not <urlset> in the sitemap namespace' % root.tag)
        return verdict(1)

    tree = pages()
    bad = 0
    listed = []
    today = datetime.date.today()

    for url in root.findall(SM + 'url'):
        loc = url.findtext(SM + 'loc', default='').strip()
        listed.append(loc)
        if loc not in tree:
            say('FAIL', 'the list offers %s, and no page in the tree has that address' % (loc or '<empty loc>'))
            bad = 1
            continue

        # The page's own word for its address, so the two can never drift.
        with open(tree[loc], encoding='utf-8') as fh:
            html = fh.read()
        canon = re.search(r'<link[^>]+rel="canonical"[^>]*href="([^"]+)"', html)
        if not canon:
            say('FAIL', '%s is in the list and names no canonical address of its own' % loc)
            bad = 1
        elif canon.group(1) != loc:
            say('FAIL', 'the list calls it %s and the page itself says %s' % (loc, canon.group(1)))
            bad = 1

        mod = url.findtext(SM + 'lastmod', default='').strip()
        try:
            when = datetime.date(*[int(x) for x in mod.split('-')])
        except (TypeError, ValueError):
            say('FAIL', '%s carries «%s» where a date belongs' % (loc, mod))
            bad = 1
        else:
            if when > today:
                say('FAIL', '%s says it was last changed on %s, which has not happened yet' % (loc, mod))
                bad = 1

        # Alternates, where the entry carries them, must repeat the page.
        inline = {}
        for link in url.findall(XH + 'link'):
            if link.get('rel') == 'alternate' and link.get('hreflang'):
                inline[link.get('hreflang')] = link.get('href')
        if inline:
            mine = head_alternates(tree[loc])
            if inline != mine:
                say('FAIL', '%s: the list and the page disagree about its language versions' % loc)
                say('', '  list: %s' % sorted(inline.items()))
                say('', '  page: %s' % sorted(mine.items()))
                bad = 1

    twice = sorted({u for u in listed if listed.count(u) > 1})
    if twice:
        say('FAIL', 'the list offers the same address more than once: %s' % ', '.join(twice))
        bad = 1

    missing = sorted(set(tree) - set(listed))
    if missing:
        say('FAIL', 'a page will be uploaded that the list never mentions, so nobody will find it:')
        for m in missing:
            say('', '  %s' % m)
        bad = 1

    if not bad:
        say('PASS', 'the list offers all %d pages of the tree and nothing else, each at the address it claims for itself'
            % len(tree))
    return verdict(bad)


if __name__ == '__main__':
    sys.exit(main())

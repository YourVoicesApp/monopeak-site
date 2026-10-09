#!/usr/bin/env bash
# The guard before publishing mono-peak.com. Exit is the verdict.
# It lives outside site/ because site/ is what gets uploaded, and a guard is
# not part of what a visitor is served.
#
# Most of this is the z-privacy.com guard with the domain changed; the blocks
# that are only here are the webmail's paths, the company's mark, and the fact
# that the two project links must be reachable by a stranger.
set -uo pipefail
cd "$(dirname "$0")/../site" || exit 2
FAIL=0
say() { printf '  %-6s %s\n' "$1" "$2"; }

HOST='https://mono-peak.com'
# The picture is the company's own, as the webmail has served it since before
# this site existed. Pinned by fingerprint rather than by name, because a guard
# that compares names passes on the day someone draws a new one.
MARK_SHA='fe014e08ecc33a274d575399592a9360cc13aea703a2e8c917dd9a8253e7cff2'

LEFT=$(grep -rlE '\{\{[A-Z0-9_]+\}\}' --include='*.html' . 2>/dev/null || true)
if [ -n "$LEFT" ]; then
  say FAIL "build values still unfilled: $LEFT"; FAIL=1
else
  say PASS "every build value is filled"
fi

# Only what a browser FETCHES on its own counts: src=, a stylesheet link,
# url() and @import in CSS. A plain <a href> to another site is a hyperlink a
# person chooses. This is the guard behind the page's own sentence that no
# request leaves this domain.
OUT=$(grep -rnoE '(src|href)="https?://[^"]+"' --include='*.html' . 2>/dev/null \
      | grep -vE '<a |rel="alternate"|rel="canonical"' | grep -E 'src=|rel="stylesheet"' || true)
OUT="$OUT$(grep -rnoE '(url\(|@import)[^;]*https?://[^)"'"'"' ;]+' --include='*.css' . 2>/dev/null || true)"
if [ -n "$(printf '%s' "$OUT" | tr -d '[:space:]')" ]; then
  say FAIL "a request would leave this site:"; printf '%s\n' "$OUT" | sed 's/^/           /'
  FAIL=1
else
  say PASS "no third-party request: the fonts and styles are served from here"
fi

# Code, not the word — the lesson a sister guard paid for when a page honestly
# said «no analytics account» and a search for «analytics» went red. The page
# promises no script, no cookie and nothing counted; this is what holds it.
COUNTERS='<script|javascript:|document\.cookie|localStorage|on(click|load|error|submit|focus|change|input|mouseover|keyup|keydown)=|google-analytics|googletagmanager|gtag\(|analytics\.js|plausible\.io|matomo|fathom\.|hotjar|segment\.(io|com)|mixpanel'
if grep -rqiE "$COUNTERS" --include='*.html' . 2>/dev/null; then
  say FAIL "a script, a handler, a cookie or a counter is on a page:"
  grep -rniE "$COUNTERS" --include='*.html' . | sed 's/^/           /' | head -8
  FAIL=1
else
  say PASS "no JavaScript, no handler, no cookie, no counter"
fi

# The webmail keeps /mail/, /mailbox/ and /pilot/ on this same domain. This
# site replaces the redirect at the root and may not reach into them: one link
# from here and a crawler walks into a mailbox login.
INTO=$(grep -rnoE 'href="/(mail|mailbox|pilot)(/[^"]*)?"' --include='*.html' . 2>/dev/null || true)
if [ -n "$(printf '%s' "$INTO" | tr -d '[:space:]')" ]; then
  say FAIL "a link from this site reaches into the webmail's paths:"
  printf '%s\n' "$INTO" | sed 's/^/           /'
  FAIL=1
else
  say PASS "nothing here links into /mail/, /mailbox/ or /pilot/"
fi

# The mark, by fingerprint.
if [ ! -f assets/logo-mark-512.png ]; then
  say FAIL "the company's mark is not here"; FAIL=1
elif [ "$(sha256sum assets/logo-mark-512.png | cut -d' ' -f1)" != "$MARK_SHA" ]; then
  say FAIL "assets/logo-mark-512.png is not the mark this site was built with"; FAIL=1
else
  say PASS "the mark is the company's own picture, byte for byte"
fi

ICONS=0
for f in assets/logo-mark-32.png assets/logo-mark-64.png assets/logo-mark-180.png assets/logo-mark-192.png; do
  [ -f "$f" ] || { say FAIL "the pages link $f and it is not here"; FAIL=1; ICONS=1; }
done
while IFS= read -r p; do
  for want in 'rel="icon"' 'apple-touch-icon'; do
    grep -q "$want" "$p" || { say FAIL "${p#./} has no $want"; FAIL=1; ICONS=1; }
  done
done < <(find . -name index.html | sort)
[ "$ICONS" = 0 ] && say PASS "every page asks for its icons, and the files are here"

# One page, one address, DERIVED from the path and never read back from the
# page and compared with itself: a head copied from a sibling and left
# unedited is the one fault this tag actually suffers.
CANON=0
while IFS= read -r f; do
  rel="${f#./}"; want="$HOST/${rel%index.html}"
  n=$(grep -cE '<link[^>]+rel="canonical"' "$f" 2>/dev/null || true); n=${n:-0}
  if [ "$n" != 1 ]; then
    say FAIL "$rel carries $n canonical links, and a page has exactly one address"; FAIL=1; CANON=1; continue
  fi
  got=$(grep -oE '<link[^>]+rel="canonical"[^>]*>' "$f" | grep -oE 'href="[^"]*"' | sed -E 's/^href="//; s/"$//')
  [ "$got" = "$want" ] || { say FAIL "$rel calls $got its own address, and its own address is $want"; FAIL=1; CANON=1; }
done < <(find . -name index.html | sort)
[ "$CANON" = 0 ] && say PASS "every page names itself as canonical, at the address its own path gives it"

# A set of translations is a set: every page in it names the same members,
# itself included. Asked of every member, so one page cannot be the only one
# telling the truth.
sets_of() {
  grep -oE '<link[^>]+rel="alternate"[^>]*>' "$1" 2>/dev/null \
  | sed -E 's/.*hreflang="([^"]+)"[^>]*href="([^"]+)".*/\1 \2/' | sort
}
HREF=0
while IFS= read -r f; do
  rel="${f#./}"; me="/${rel%index.html}"
  mine=$(sets_of "$f")
  if [ -z "$mine" ]; then say FAIL "$rel names no language version at all"; FAIL=1; HREF=1; continue; fi
  printf '%s\n' "$mine" | awk '{print $2}' | grep -qxF "$me" \
    || { say FAIL "$rel lists language versions and leaves itself ($me) out"; FAIL=1; HREF=1; }
  for a in $(printf '%s\n' "$mine" | awk '{print $2}' | sort -u); do
    tgt=".${a}index.html"
    if [ ! -f "$tgt" ]; then
      say FAIL "$rel names $a as a language version of itself, and no page is there"; FAIL=1; HREF=1; continue
    fi
    [ "$(sets_of "$tgt")" = "$mine" ] \
      || { say FAIL "$rel and $a disagree about who is in their set, so Google believes neither"; FAIL=1; HREF=1; }
  done
done < <(find . -name index.html | sort)
[ "$HREF" = 0 ] && say PASS "every set of translations names the same members on every page in it"

# robots.txt: allows everything, names the sitemap, and names NO path of its
# own. A path written here is published to everyone who reads the file.
ROBOTS=0
r_fail() { say FAIL "$1"; FAIL=1; ROBOTS=1; }
if [ ! -f robots.txt ]; then
  r_fail "there is no robots.txt, so a crawler reaching the root is told nothing"
else
  grep -qE '^[Uu]ser-agent:[[:space:]]*\*[[:space:]]*$' robots.txt || r_fail "robots.txt speaks to no crawler"
  grep -qE '^[Aa]llow:[[:space:]]*/[[:space:]]*$' robots.txt || r_fail "robots.txt does not allow the site"
  grep -qE "^[Ss]itemap:[[:space:]]*$HOST/sitemap\.xml[[:space:]]*$" robots.txt \
    || r_fail "robots.txt does not name the sitemap at its absolute address"
  [ -f sitemap.xml ] || r_fail "robots.txt sends a crawler to a sitemap that is not in this tree"
  NAMED=$(grep -iE '^[[:space:]]*(allow|disallow):' robots.txt \
          | sed -E 's/^[^:]*:[[:space:]]*//; s/[[:space:]]*$//' | grep -vxE '/?' || true)
  if [ -n "$(printf '%s' "$NAMED" | tr -d '[:space:]')" ]; then
    r_fail "robots.txt names a path of its own, and so publishes it:"
    printf '%s\n' "$NAMED" | sed 's/^/           /'
  fi
  HEXY=$(grep -nE '[0-9a-f]{8}' robots.txt || true)
  [ -n "$HEXY" ] && { r_fail "robots.txt carries a fingerprint-shaped name:"; printf '%s\n' "$HEXY" | sed 's/^/           /'; }
fi
[ "$ROBOTS" = 0 ] && say PASS "robots.txt allows every crawler, names the sitemap, and names no path of its own"

# The two project links are the practical reason this site exists, so they are
# held to 200: a stranger clicking them must arrive. Our own addresses are not
# asked of the network at all — check_sitemap.py proves them against the tree,
# which is what a guard that runs BEFORE the deploy can honestly say.
MINE=$(grep -rhoE "href=\"$HOST/[^\"]*\"" --include='*.html' . 2>/dev/null | sort -u | wc -l)
say PASS "$MINE of our own addresses are checked against the tree, not asked of the network"
DESTS=$(grep -rhoE '(href)="https?://[^"]+"' --include='*.html' . 2>/dev/null \
        | sed -E 's/^href="//; s/"$//' | grep -vE "^$HOST/" | sort -u)
if ! command -v curl >/dev/null 2>&1; then
  say FAIL "curl is missing, so no destination could be checked"; FAIL=1
else
  for u in $DESTS; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$u" 2>/dev/null || true)
    case "$code" in [0-9][0-9][0-9]) : ;; *) code=000 ;; esac
    if [ "$code" = 200 ]; then
      say PASS "answers 200: $u"
    else
      say FAIL "a project this page sends people to does not answer ($code): $u"; FAIL=1
    fi
  done
fi

PAGES=0
for f in index.html sv/index.html en/index.html de/index.html ar/index.html; do
  [ -f "$f" ] || { say FAIL "missing $f"; FAIL=1; PAGES=1; }
done
[ "$PAGES" = 0 ] && say PASS "all five pages present"

if command -v python3 >/dev/null 2>&1; then
  python3 ../scripts/check_sitemap.py || FAIL=1
  python3 ../scripts/check_contrast.py || FAIL=1
else
  say FAIL "no python3, so neither the page list nor the contrast was measured"; FAIL=1
fi

echo
[ "$FAIL" = 0 ] && echo "site ready to publish" || echo "SITE NOT READY"
exit "$FAIL"

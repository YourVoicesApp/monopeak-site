# mono-peak.com

The company's front door: **Faruk AB** is the company, **mono-peak** is the name
the work is built under, and the page's practical job is to hand a reader — or a
crawler — on to the projects, Z Privacy first.

Five pages: a chooser at `/`, then `/sv/`, `/en/`, `/de/`, `/ar/`. Static HTML,
no build step; `site/` is the tree that gets uploaded.

## Checking it

    ./scripts/check_site.sh              # the verdict: links, guards, robots, sitemap, palette
    python3 scripts/measure_first_screen.py   # what a visitor actually sees, in a real renderer
    python3 scripts/check_sitemap.py     # the page list against the tree, both ways
    python3 scripts/check_contrast.py    # every colour against the ground it sits on

`check_site.sh` calls the last two, so one command still answers. It needs the
network: the two project links are held to **200**, because a company page that
sends people to a dead address is worse than one that names nothing.

## Rules this site is built under

- **Every sentence is a measurement.** Z Privacy is Linux and in beta and offers
  no download; YourVoices is a closed circle with no public launch; Mono Peak
  Mail is infrastructure and is not offered as a product. Nothing here says more
  than that.
- **No script, no cookie, nothing counted, no third-party request.** The page
  says so in four languages and the guard is what holds it to that — the fonts
  are served from this domain, which is why they are in the repository.
- **The webmail keeps `/mail/`, `/mailbox/` and `/pilot/`** on this same domain.
  This site replaces the 308 at the root and may not link into them; the guard
  fails on one `href` that tries.
- **The mark is the company's own**, byte for byte the picture the webmail has
  served since before this site existed, pinned in the guard by fingerprint.
- **Found by a crawler from the first day**, not as a debt: a canonical on each
  page derived from its path, one reciprocal hreflang set with the chooser as
  `x-default`, `robots.txt`, and a `sitemap.xml` walked against the tree.

## Not published

Nothing here goes anywhere by the builder's hand. The lead measures and deploys;
the live site moves on the owner's word. The repository is local — whether it
goes to GitHub is the owner's decision.

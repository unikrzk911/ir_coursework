"""
Generates a small fake "Pure Portal" site under ./site/ that mirrors the
real markup structure (list-result-item / h3.title / a.link.person /
span.date / a.nextLink, plus a robots.txt with a Crawl-Delay) closely
enough to exercise the real crawler code end-to-end, without needing
network access to the real pureportal.coventry.ac.uk (which this sandbox
cannot reach). Run once: `python generate_fixtures.py`.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
ORG_PATH = "/en/organisations/centre-for-healthcare-and-community-transformation/publications"

PUBLICATIONS = [
    dict(
        slug="community-nutrition-intervention-outcomes",
        title="Community-based nutrition intervention improves outcomes in older adults",
        year=2023,
        authors=[("Deborah Lycett", "/en/persons/deborah-lycett"), ("Petra Wark", "/en/persons/petra-wark")],
        abstract="This study evaluates a community nutrition programme delivered across "
                 "primary care settings, reporting significant improvements in dietary "
                 "quality and wellbeing among older adults with obesity risk factors.",
    ),
    dict(
        slug="physical-activity-diabetes-prevention",
        title="Physical activity and exercise interventions for type 2 diabetes prevention",
        year=2022,
        authors=[("Tom Bason", "/en/persons/tom-bason")],
        abstract="A systematic review of exercise-based interventions for diabetes "
                 "prevention in community and sport settings, highlighting the role of "
                 "structured physical activity programmes.",
    ),
    dict(
        slug="mental-health-community-transformation",
        title="Mental health and community transformation: a co-production approach",
        year=2024,
        authors=[("Michael Duncan", "/en/persons/michael-duncan"), ("Sally Abbott", None)],
        abstract="Explores co-production methods for improving mental health services "
                 "through community engagement and healthcare transformation initiatives.",
    ),
    dict(
        slug="obesity-management-primary-care",
        title="Obesity management strategies in UK primary care: a scoping review",
        year=2021,
        authors=[("Petra Wark", "/en/persons/petra-wark")],
        abstract="Reviews obesity management strategies delivered in primary care, "
                 "including nutrition counselling and referral pathways to community "
                 "weight management programmes.",
    ),
    dict(
        slug="research-engagement-happy-healthy-lives",
        title="Developing research engagement for happy, healthy lives",
        year=2023,
        authors=[("Sally Abbott", None), ("Deborah Lycett", "/en/persons/deborah-lycett")],
        abstract="Describes a public engagement project connecting healthcare researchers "
                 "with community members to co-design studies that support healthy lives.",
    ),
    dict(
        slug="digital-health-community-monitoring",
        title="Digital health tools for remote community health monitoring",
        year=2024,
        authors=[("Tom Bason", "/en/persons/tom-bason"), ("Michael Duncan", "/en/persons/michael-duncan")],
        abstract="Assesses the adoption of digital health monitoring tools within "
                 "community healthcare transformation programmes across the West Midlands.",
    ),
]

PAGE_SIZE = 4


def item_html(pub, base):
    authors_html = ""
    for name, href in pub["authors"]:
        if href:
            authors_html += f'<a class="link person" rel="Person" href="{href}">{name}</a>, '
        else:
            authors_html += f'<span class="unlinked-person">{name}</span>, '
    authors_html = authors_html.rstrip(", ")
    return f"""
    <li class="list-result-item list-result-item-... researchoutput">
      <div class="result-container">
        <h3 class="title"><a class="link" href="{base}/{pub['slug']}"><span>{pub['title']}</span></a></h3>
        <div class="persons">{authors_html}</div>
        <span class="date">{pub['year']}</span>
      </div>
    </li>
    """


def render_listing_page(page_num, base, pub_base):
    start = page_num * PAGE_SIZE
    chunk = PUBLICATIONS[start:start + PAGE_SIZE]
    items = "\n".join(item_html(p, pub_base) for p in chunk)
    has_next = (start + PAGE_SIZE) < len(PUBLICATIONS)
    next_link = f'<a class="nextLink" rel="next" href="{base}?page={page_num + 1}">Next</a>' if has_next else ""
    return f"""<!DOCTYPE html>
<html><head><title>Publications — Centre for Healthcare and Community Transformation</title></head>
<body>
<h1>Research output</h1>
<ul class="list-results">
{items}
</ul>
{next_link}
</body></html>"""


def render_detail_page(pub):
    return f"""<!DOCTYPE html>
<html><head>
<title>{pub['title']}</title>
<meta name="citation_abstract" content="{pub['abstract']}">
</head>
<body>
<h1 class="title">{pub['title']}</h1>
<div class="rendering_researchoutput">
  <div class="textblock">{pub['abstract']}</div>
</div>
</body></html>"""


def main():
    org_dir = os.path.join(SITE, ORG_PATH.strip("/"))
    os.makedirs(org_dir, exist_ok=True)

    # Listing pages: page 0 served at .../publications/index.html AND
    # .../publications/ (the http.server default), later pages at ?page=N
    # -- since a plain file server can't do query strings, we pre-render
    # them as page-1.html etc. and the test's tiny WSGI-ish handler below
    # maps "?page=N" to that file. See test_crawler_offline.py.
    n_pages = (len(PUBLICATIONS) + PAGE_SIZE - 1) // PAGE_SIZE
    pub_base = "/en/publications"
    for page_num in range(n_pages):
        html = render_listing_page(page_num, ORG_PATH + "/", pub_base)
        fname = "index.html" if page_num == 0 else f"page-{page_num}.html"
        with open(os.path.join(org_dir, fname), "w") as f:
            f.write(html)

    pub_dir = os.path.join(SITE, pub_base.strip("/"))
    os.makedirs(pub_dir, exist_ok=True)
    for pub in PUBLICATIONS:
        with open(os.path.join(pub_dir, f"{pub['slug']}.html"), "w") as f:
            f.write(render_detail_page(pub))

    with open(os.path.join(SITE, "robots.txt"), "w") as f:
        f.write("User-Agent: *\nCrawl-Delay: 1\nDisallow: /*?*format=rss\n")

    print(f"Generated fixture site at {SITE} ({n_pages} listing pages, {len(PUBLICATIONS)} publications)")


if __name__ == "__main__":
    main()

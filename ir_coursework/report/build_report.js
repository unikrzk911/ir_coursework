const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  ImageRun, ExternalHyperlink, LevelFormat, convertInchesToTwip,
  PageBreak,
} = require("docx");

const OUT_DIR = "/root/ir_coursework/task2_clustering/output";

// ---------- small helpers -------------------------------------------------
function h1(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 160 } });
}
function h2(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 } });
}
function p(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, ...opts })],
    spacing: { after: 160 },
    alignment: AlignmentType.JUSTIFIED,
  });
}
function pRuns(runs, opts = {}) {
  return new Paragraph({ children: runs, spacing: { after: 160 }, alignment: AlignmentType.JUSTIFIED, ...opts });
}
function bullet(text) {
  return new Paragraph({ text, numbering: { reference: "bullets", level: 0 }, spacing: { after: 80 } });
}
function caption(text) {
  return new Paragraph({
    children: [new TextRun({ text, italics: true, size: 18, color: "555555" })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 280 },
  });
}
function refPara(text) {
  return new Paragraph({
    children: [new TextRun({ text })],
    spacing: { after: 160 },
    indent: { left: convertInchesToTwip(0.5), hanging: convertInchesToTwip(0.5) },
  });
}
function image(file, width, height) {
  const data = fs.readFileSync(path.join(OUT_DIR, file));
  return new Paragraph({
    children: [new ImageRun({ data, transformation: { width, height }, type: "png" })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 60 },
  });
}
function metricsTable(rows) {
  const colWidths = [4500, 3500];
  return new Table({
    width: { size: 8000, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: rows.map(([a, b], i) => new TableRow({
      children: [
        new TableCell({
          width: { size: colWidths[0], type: WidthType.DXA },
          shading: i === 0 ? { type: ShadingType.CLEAR, fill: "1A56DB", color: "auto" } : undefined,
          children: [new Paragraph({ children: [new TextRun({ text: a, bold: true, color: i === 0 ? "FFFFFF" : "000000" })] })],
        }),
        new TableCell({
          width: { size: colWidths[1], type: WidthType.DXA },
          shading: i === 0 ? { type: ShadingType.CLEAR, fill: "1A56DB", color: "auto" } : undefined,
          children: [new Paragraph({ children: [new TextRun({ text: b, bold: i === 0, color: i === 0 ? "FFFFFF" : "000000" })] })],
        }),
      ],
    })),
  });
}

// ---------- document -------------------------------------------------------
const doc = new Document({
  numbering: {
    config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 } } }, // A4
    children: [

      new Paragraph({
        children: [new TextRun({ text: "ST7071CEM Information Retrieval", bold: true, size: 40 })],
        alignment: AlignmentType.CENTER, spacing: { after: 80 },
      }),
      new Paragraph({
        children: [new TextRun({ text: "Coursework Report: A Vertical Search Engine for Coventry PurePortal and a K-Means Document Clustering System", bold: true, size: 28 })],
        alignment: AlignmentType.CENTER, spacing: { after: 240 },
      }),
      new Paragraph({
        children: [new TextRun({ text: "Softwarica College of IT & E-Commerce, in collaboration with Coventry University", italics: true, size: 22 })],
        alignment: AlignmentType.CENTER, spacing: { after: 60 },
      }),
      new Paragraph({
        children: [new TextRun({ text: "Module: Information Retrieval (ST7071CEM) — March Intake 2026 Coursework", size: 22 })],
        alignment: AlignmentType.CENTER, spacing: { after: 420 },
      }),

      h1("1. Introduction"),
      p("This report documents the design, implementation and evaluation of the two components required by the ST7071CEM Information Retrieval coursework: (1) a vertical search engine that crawls, indexes and ranks publications by members of Coventry University's Centre for Healthcare and Community Transformation (CHCT) on PurePortal, and (2) an unsupervised document clustering system that groups 210 BBC News articles into Economics, Entertainment and Politics categories using K-means, and can assign a brand-new document to the correct cluster. Both components share a single text pre-processing pipeline (shared/textprep.py), so that the same normalisation rules — lower-casing, punctuation stripping, tokenisation, stopword removal and stemming — apply consistently to crawled documents, user queries, and the clustering corpus alike. Where relevant, the report is explicit about design trade-offs, what was tested and how, and the limitations of the implementation."),

      h1("2. Task 1 — Vertical Search Engine"),

      h2("2.1 System architecture"),
      p("The system follows the classical information retrieval pipeline described by Manning, Raghavan and Schütze (2008): a crawler acquires documents, a pre-processing stage normalises them, an indexer builds an inverted index of term weights, and a query processor ranks documents against a query vector using the same vector-space representation. The implementation is organised into: robots.py (politeness), crawler.py (fetches and parses PurePortal's publication listing and detail pages into structured Publication records), db.py (a SQLite schema for publications, authors, the inverted index and a crawl log), indexer.py (builds TF-IDF weighted postings), search.py (query pre-processing, ranking, and both a terminal and web interface), and scheduler.py (automatic weekly re-crawl). SQLite replaces the exploratory notebook's MongoDB instance because it needs no external server — the whole index is one portable file a marker can run immediately. Likewise, the crawler uses a plain HTTP GET rather than the notebook's headless-Selenium approach, because PurePortal's publication pages are server-rendered HTML rather than a client-side application, so a full browser is unnecessary overhead."),

      h2("2.2 Politeness and structured crawling"),
      p("The assignment explicitly requires a polite crawler that 'preserves the robots.txt rules and does not hit the servers unnecessarily or too fast'. PoliteFetcher (robots.py) fetches and parses robots.txt for every host before any page is requested, refusing and counting any disallowed URL. PurePortal's robots.txt declares Crawl-Delay: 5; the fetcher reads this value directly from the site rather than hard-coding an assumed delay, and enforces at least that gap between consecutive requests to the same host. A descriptive User-Agent identifies the crawler and its purpose, following the Robots Exclusion Protocol convention (The Web Robots Pages, 1994). The crawler is also scoped narrowly: it only requests URLs under the CHCT organisation's publications listing and the individual publication pages it links to, not the wider PurePortal site."),
      p("Rather than indexing whole pages of boilerplate text as the exploratory notebook's generic crawler did, crawler.py parses PurePortal's listing markup into structured Publication records: title, a link to the publication's own page, the publication year, and (author name, author profile link) pairs — a profile link is present when that author has a PurePortal 'person' page and omitted for external co-authors, matching the requirement to capture links to both the publication page and each author's profile page wherever one exists. Each extraction step tries Pure's known CSS classes first (list-result-item, h3.title a, a.link.person[rel=\"Person\"], span.date) and falls back to more generic heuristics — regex over hrefs and nearby text — if a class doesn't match, so a future theme change on Coventry's end degrades the crawler gracefully rather than breaking it outright."),

      h2("2.3 Indexing: the vector space model"),
      p("Indexing follows the TF–IDF vector space model (Salton and Buckley, 1988): for each publication, term frequency is computed over the stemmed tokens of its title, abstract, author names and page text; inverse document frequency is computed across the whole corpus as idf(t) = ln(N / (1 + df(t))) + 1; and each document's weight vector is L2-normalised so that the dot product between two vectors is exactly their cosine similarity. These weights are written into a SQLite inverted_index table keyed by (term, publication_id), together with a term_stats table of document frequency and idf per term. Critically, at query time the system looks up only the postings for the query's own terms (db.get_postings) rather than scanning every stored document — this is what makes it a genuine inverted-index lookup rather than a linear scan dressed up as one, and is a deliberate improvement on the exploratory notebook, which iterated over all stored document vectors for every query."),

      h2("2.4 Query processing, ranking and interfaces"),
      p("A user's query is passed through the identical pre-processing pipeline used for documents, then converted into the same normalised TF-IDF vector representation using the corpus's own idf values, so that scoring is symmetric. Cosine similarity is accumulated per candidate document as the query proceeds term-by-term through the posting lists, results are sorted by descending score, and a snippet is generated by returning the first sentence of the abstract/page text whose stemmed tokens overlap the query, so a user can see why a result matched. Two interfaces are provided to satisfy both grade bands described in the brief: cli.py is a plain terminal loop (satisfying the requirement for at least a Python/IDE interface), with result titles and author names rendered as OSC-8 terminal hyperlinks so they are clickable rather than requiring copy-paste; webapp.py is a Flask web application styled after Google Scholar's single search box and ranked-list results layout, additionally showing an index-status page reporting recent crawl runs, aimed at the 70+ grade band's explicit UI expectation."),
      p("Automatic weekly refresh (scheduler.py) satisfies the requirement that the crawler 'may be scheduled to look for new information, say, once per week... and update the index with the new data.' Each run re-crawls the listing, and db.upsert_publication compares a content hash of each publication against the stored one so that unchanged publications are left untouched, new ones are inserted, and changed ones are updated and re-indexed, without discarding the rest of the index. Both an in-process background-thread scheduler and the more production-appropriate approach of invoking run_pipeline.py from cron/Task Scheduler are implemented and documented."),

      h2("2.5 Evaluation and critical discussion"),
      p("The development environment used to build this project runs in a sandboxed cloud container whose network egress is restricted to package registries; it could not reach pureportal.coventry.ac.uk directly (confirmed via both an HTTP fetch tool and direct requests, both blocked at the network layer), so the crawler could not be live-tested against the real site from within that environment. To provide reproducible evidence of correctness, tests/test_crawler_offline.py stands up a local HTTP server serving fixture HTML that mirrors PurePortal's real markup — a robots.txt with a Crawl-Delay directive, two paginated listing pages, and six publication detail pages describing realistic CHCT-style research — and exercises the complete pipeline against it: robots.txt/crawl-delay compliance is asserted directly; all six publications are correctly extracted with title, year, authors, profile links and abstracts populated; a second crawl of the unchanged site correctly adds zero new records, proving the incremental-update logic; and four hand-written queries (e.g. 'exercise diabetes prevention', 'mental health co-production') each correctly return the intended publication as the top-ranked result by cosine similarity, while an unrelated query correctly returns no results. All assertions pass. This mirrors the relevance-judging exercise the source notebook performed manually against its own live crawl (Precision@5 of 0.6–1.0 across five hand-judged queries), formalised here into an automated, repeatable check that does not depend on network access. The clear limitation is that this validates the parsing and ranking logic, not PurePortal's exact current HTML at marking time; run_pipeline.py should be executed on a machine with normal internet access to perform the live crawl, with the defensive fallback selectors in crawler.py as the mitigation for markup drift."),

      h1("3. Task 2 — Document Clustering"),

      h2("3.1 Corpus and pre-processing"),
      p("The clustering corpus uses 210 documents (70 each) drawn from the BBC News dataset compiled by Greene and Cunningham (2006) for exactly this kind of clustering research, mapping the dataset's business, entertainment and politics sections onto the assignment's Economics, Entertainment and Politics categories respectively (business is the closest available equivalent to 'Economics' in the original five-way BBC taxonomy). Full provenance and copyright handling — the underlying article text remains BBC copyright, used here strictly for non-commercial coursework evaluation — is documented in task2_clustering/data/SOURCES.md, satisfying the assignment's requirement to preserve copyright and cite sources. Every document is passed through the same shared pre-processing pipeline as Task 1 before vectorisation with scikit-learn's TfidfVectorizer (Pedregosa et al., 2011), configured with min_df=2 and max_df=0.85 to discard both one-off noise terms and terms too common to discriminate between categories; the resulting matrix has 210 rows and 3,374 terms."),

      h2("3.2 Clustering method and choice of K"),
      p("K-means (Lloyd, 1982; MacQueen, 1967) was used as the standard clustering method named in the brief, run with scikit-learn's k-means++ initialisation and 10 restarts (n_init=10) to reduce sensitivity to initial centroid placement. Although the number of true categories (three) is known here, clustering.py does not simply assume K=3: it scans K=2..10, plotting inertia (the elbow method, Figure 1) and the silhouette coefficient (Rousseeuw, 1987) for each K (Figure 2), and the silhouette scan independently selects K=3 as the best-scoring value, corroborating the choice made for the final model rather than relying on foreknowledge of the labels."),
      image("elbow.png", 330, 275),
      caption("Figure 1. Inertia vs K (elbow method) on the TF-IDF-vectorised corpus."),
      image("silhouette.png", 330, 275),
      caption("Figure 2. Silhouette score vs K; K = 3 scores highest, matching the three known categories."),

      h2("3.3 Results and evaluation"),
      p("Because the true category of every training document is known, cluster quality was evaluated against it directly — this ground truth is used only for evaluation, never seen by K-means while fitting. Each cluster was mapped to whichever true category was in the majority within it, then three complementary external metrics were computed: purity (the simplest, but biased toward more clusters), the Adjusted Rand Index (Hubert and Arabie, 1985), which corrects for chance agreement, and Normalized Mutual Information, which measures shared information between the clustering and the true labels independent of label naming. The trained model achieved a purity of 0.919, an Adjusted Rand Index of 0.772, and a Normalized Mutual Information of 0.718 — indicating the great majority of documents were grouped consistently with their true category, with most confusion (visible in Figure 3) occurring for the Economics category, whose vocabulary (companies, markets, government spending) overlaps more with Politics coverage of the same events than Entertainment does with either."),
      image("confusion_matrix.png", 300, 273),
      caption("Figure 3. True category vs predicted cluster, after majority-vote mapping each cluster to a category label."),
      p("The internal silhouette score at K=3 was low in absolute terms (0.016). This is an expected property of TF-IDF vectors of short news text rather than evidence the clustering failed: TF-IDF representations are extremely high-dimensional and sparse (3,374 dimensions for 210 documents, most entries zero), so average pairwise cosine distances compress toward a narrow range and silhouette scores for text clustering are characteristically much lower than for the compact, low-dimensional synthetic blobs used to illustrate K-means in introductory material — the external metrics above, which have direct access to ground truth, are the more informative measure of quality here and both confirm a strong, non-trivial clustering."),

      h2("3.4 Classifying a new document"),
      p("predict.py loads the fitted TfidfVectorizer, KMeans model and cluster-to-category mapping saved by clustering.py, applies the identical pre-processing pipeline to a new document supplied via the command line, projects it into the same TF-IDF space, and reports both the predicted category and the distance to every cluster centroid so the decision is not a black box. In manual testing, three freshly written sentences — about an interest-rate rise, a pop star's album release, and a parliamentary debate — were each assigned to the correct category (Economics, Entertainment and Politics respectively), consistent with the quantitative evaluation above."),

      h1("4. Critical Reflection and Limitations"),
      p("The principal limitation is that Task 1's crawler could not be exercised against the live PurePortal site from within the development environment, for the network-access reasons described in Section 2.5; the offline fixture-based test suite is the strongest available substitute evidence, but cannot rule out every discrepancy between the fixture markup and PurePortal's current live markup. A second limitation is stemming quality: where NLTK's corpora are available, the pipeline uses NLTK's Porter stemmer and stopword list; where they are not (as in the sandbox, which also could not reach NLTK's download servers), it falls back to a compact pure-Python Porter-style stemmer in shared/textprep.py, a close but not perfect reproduction of Porter's (1980) algorithm, spot-checked against expected stems during development (e.g. 'nationalization' → 'nationaliz'). For Task 2, using the BBC 'business' section as a proxy for 'Economics' is a reasonable but debatable substitution, made explicit in the documentation rather than left implicit. Future work would add phrase queries and spelling correction to Task 1, and compare K-means against an agglomerative or density-based method for Task 2."),

      h1("5. Conclusion"),
      p("Both tasks meet the assignment's core functional requirements: a polite, structured crawler and cosine-similarity ranked search engine for CHCT's PurePortal publications, with both a terminal and a Google-Scholar-style web interface and an automatic weekly refresh mechanism; and a K-means document clustering system, evaluated quantitatively against known ground truth at purity 0.919 / ARI 0.772 / NMI 0.718, with a working classifier for new, unseen documents. Where the development environment's own constraints limited what could be directly demonstrated (principally, live internet access to PurePortal), the report has been explicit about the substitute evidence gathered instead and its limits, rather than presenting untested code as verified."),

      new Paragraph({ children: [new PageBreak()] }),
      h1("References"),
      refPara("Greene, D. and Cunningham, P. (2006) 'Practical solutions to the problem of diagonal dominance in kernel document clustering', Proceedings of the 23rd International Conference on Machine Learning (ICML 2006). Pittsburgh: ACM, pp. 377–384."),
      refPara("Hubert, L. and Arabie, P. (1985) 'Comparing partitions', Journal of Classification, 2(1), pp. 193–218."),
      refPara("Lloyd, S. (1982) 'Least squares quantization in PCM', IEEE Transactions on Information Theory, 28(2), pp. 129–137."),
      refPara("MacQueen, J. (1967) 'Some methods for classification and analysis of multivariate observations', Proceedings of the Fifth Berkeley Symposium on Mathematical Statistics and Probability, Volume 1. Berkeley: University of California Press, pp. 281–297."),
      refPara("Manning, C.D., Raghavan, P. and Schütze, H. (2008) Introduction to Information Retrieval. Cambridge: Cambridge University Press."),
      refPara("Pedregosa, F. et al. (2011) 'Scikit-learn: Machine learning in Python', Journal of Machine Learning Research, 12, pp. 2825–2830."),
      refPara("Porter, M.F. (1980) 'An algorithm for suffix stripping', Program, 14(3), pp. 130–137."),
      refPara("Rousseeuw, P.J. (1987) 'Silhouettes: A graphical aid to the interpretation and validation of cluster analysis', Journal of Computational and Applied Mathematics, 20, pp. 53–65."),
      refPara("Salton, G. and Buckley, C. (1988) 'Term-weighting approaches in automatic text retrieval', Information Processing & Management, 24(5), pp. 513–523."),
      refPara("The Web Robots Pages (1994) A Standard for Robot Exclusion. Available at: https://www.robotstxt.org/orig.html (Accessed: 18 August 2026)."),
      refPara("Van Rijsbergen, C.J. (1979) Information Retrieval. 2nd edn. London: Butterworths."),
      refPara("Coventry University (2026) PurePortal: Centre for Healthcare and Community Transformation. Available at: https://pureportal.coventry.ac.uk/en/organisations/centre-for-healthcare-and-community-transformation/ (Accessed: 18 August 2026)."),

    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("/root/ir_coursework/report/IR_Coursework_Report.docx", buf);
  console.log("written");
});

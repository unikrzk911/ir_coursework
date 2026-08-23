"""
Builds a synthetic search-interest corpus for document clustering.

Categories:
    - Economics
    - Entertainment
    - Politics

The corpus is designed around topics that modern internet users commonly
search for rather than fabricated news events.

Entertainment has a strong focus on:
    - Marvel / MCU
    - superhero movies
    - streaming
    - pop music
    - major artists
    - albums and tours
    - TV shows

The generated documents are synthetic and intended for NLP / clustering
experiments. They should NOT be treated as real news articles or factual
reporting.
"""

import random
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

RANDOM_STATE = 42
DOCS_PER_CATEGORY = 250
SENTENCES_PER_DOC = (6, 10)

CORPUS_DIR = Path("corpus")


# ============================================================
# ECONOMICS
# ============================================================

ECONOMIC_TOPICS = [
    "artificial intelligence and jobs",
    "AI automation",
    "inflation and cost of living",
    "interest rates",
    "housing prices",
    "mortgage rates",
    "stock market investing",
    "technology stocks",
    "cryptocurrency",
    "Bitcoin",
    "Ethereum",
    "electric vehicles",
    "EV adoption",
    "semiconductor shortages",
    "chip manufacturing",
    "Big Tech",
    "remote work",
    "freelancing",
    "personal finance",
    "fintech",
    "digital payments",
    "global trade",
    "tariffs",
    "supply chains",
    "energy prices",
    "renewable energy",
    "unemployment",
    "wages",
    "recession",
    "consumer spending",
    "quarterly earnings reports",
    "stock market volatility",
    "central bank interest rate decisions",
    "bond yields",
    "labor market data",
    "GDP growth figures",
    "corporate mergers and acquisitions",
    "IPOs and public offerings",
    "shareholder returns",
    "market analyst forecasts",
]

ECONOMIC_ENTITIES = [
    "NVIDIA",
    "Apple",
    "Microsoft",
    "Google",
    "Amazon",
    "Tesla",
    "Meta",
    "OpenAI",
    "AMD",
    "Bitcoin",
    "Ethereum",
    "the Federal Reserve",
    "Wall Street",
    "the New York Stock Exchange",
    "the Bank of England",
    "the European Central Bank",
    "the International Monetary Fund",
]

ECONOMIC_TEMPLATES = [
    "People are increasingly searching for how {topic} could affect everyday life.",
    "One of the biggest questions surrounding {topic} is how it could change the economy over the next few years.",
    "Search interest around {topic} has grown as consumers try to understand its impact on prices, jobs, and spending.",
    "Many discussions about {topic} focus on whether the current trend is temporary or likely to continue.",
    "Consumers are looking for simple explanations of how {topic} works and why it matters.",
    "Investors often follow {topic} because changes in this area can influence technology companies and financial markets.",
    "Questions about {topic} frequently involve its effect on businesses, workers, and consumers.",
    "The relationship between {topic} and the wider economy is increasingly discussed online.",
    "People comparing different economic trends often look at {topic} alongside inflation, interest rates, and employment.",
    "A common search related to {topic} is whether it creates new opportunities or increases financial risks.",
    "Discussions about {topic} often mention companies such as {entity}.",
    "Technology companies including {entity} are frequently associated with conversations about {topic}.",
    "Understanding {topic} requires looking at both short-term market changes and longer-term economic trends.",
    "People researching {topic} are often interested in practical consequences rather than economic theory alone.",
    "Investors and analysts on Wall Street are closely watching {topic} ahead of the next earnings season.",
    "The Federal Reserve's decisions on {topic} often move stock prices within minutes of an announcement.",
    "Quarterly earnings reports tied to {topic} are closely tracked by shareholders and market analysts.",
    "Economists at {entity} regularly publish forecasts and data related to {topic}.",
    "Bond yields and stock market volatility often spike when new figures about {topic} are released.",
    "Traders reacted quickly to fresh data on {topic}, sending share prices higher on the New York Stock Exchange.",
    "Central bank policymakers weighing {topic} must balance inflation targets against the risk of slowing growth.",
]


# ============================================================
# ENTERTAINMENT
# ============================================================

MARVEL_TOPICS = [
    "Marvel Cinematic Universe timeline",
    "MCU movie watch order",
    "Marvel movie release dates",
    "upcoming Marvel movies",
    "Avengers movies",
    "Avengers storyline",
    "Secret Wars",
    "Fantastic Four",
    "Spider-Man",
    "Deadpool",
    "Wolverine",
    "Doctor Strange",
    "Thor",
    "Iron Man",
    "Captain America",
    "Black Panther",
    "Guardians of the Galaxy",
    "Loki",
    "Wanda Maximoff",
    "Scarlet Witch",
    "Kang",
    "Galactus",
    "Marvel multiverse",
    "Marvel post-credit scenes",
    "Marvel character origins",
    "Marvel theories",
    "MCU Easter eggs",
    "Marvel movie endings",
    "Marvel comics versus MCU",
]

POP_MUSIC_TOPICS = [
    "new pop music releases",
    "best new albums",
    "album release dates",
    "concert tours",
    "music festival lineups",
    "Grammy predictions",
    "pop music collaborations",
    "new singles",
    "music videos",
    "viral songs",
    "Spotify streaming trends",
    "music charts",
    "Taylor Swift",
    "Sabrina Carpenter",
    "Billie Eilish",
    "Olivia Rodrigo",
    "Dua Lipa",
    "Ariana Grande",
    "Beyoncé",
    "The Weeknd",
    "Lady Gaga",
    "Bruno Mars",
    "Harry Styles",
    "Chappell Roan",
    "K-pop",
]

ENTERTAINMENT_TOPICS = [
    *MARVEL_TOPICS,
    *POP_MUSIC_TOPICS,
    "Netflix shows",
    "Disney+ shows",
    "HBO series",
    "Amazon Prime Video shows",
    "best TV shows to watch",
    "movie recommendations",
    "new movie releases",
    "streaming subscriptions",
    "TV show endings explained",
    "movie endings explained",
    "celebrity news",
    "Hollywood trends",
    "video game adaptations",
    "superhero movies",
    "horror movies",
    "science fiction movies",
    "anime",
    "box office opening weekend numbers",
    "movie trailers and teasers",
    "award show red carpet looks",
    "concert tour setlists",
    "casting announcements",
    "critics' reviews and ratings",
    "soundtrack and score releases",
    "franchise crossover rumors",
]

ENTERTAINMENT_ENTITIES = [
    "Marvel Studios",
    "Disney+",
    "Netflix",
    "Sony Pictures",
    "Warner Bros.",
    "Taylor Swift",
    "Sabrina Carpenter",
    "Billie Eilish",
    "Olivia Rodrigo",
    "Ariana Grande",
    "Beyoncé",
    "Dua Lipa",
    "Lady Gaga",
    "The Weeknd",
    "the Oscars",
    "the Grammys",
    "the Billboard Hot 100",
    "Rotten Tomatoes",
]

ENTERTAINMENT_TEMPLATES = [
    "Fans searching for {topic} are usually interested in understanding the larger story and how different releases connect.",
    "A common search about {topic} is what viewers should watch first and what can be skipped.",
    "People researching {topic} often look for explanations of characters, storylines, and important details.",
    "Online discussions about {topic} frequently focus on theories, references, and hidden details.",
    "One reason {topic} attracts attention is the amount of speculation surrounding future releases.",
    "Searches related to {topic} often increase when a new trailer, album, episode, or announcement appears.",
    "Fans commonly compare different interpretations of {topic} and debate what could happen next.",
    "People interested in {topic} often want a chronological guide rather than a simple list of releases.",
    "Another popular question surrounding {topic} is how it connects to earlier movies, shows, albums, or events.",
    "Entertainment searches increasingly focus on explaining confusing storylines and endings.",
    "Fans frequently search for {topic} after seeing discussions about it on social media.",
    "People following {topic} are often interested in release dates, streaming availability, and future projects.",
    "A major part of the online conversation around {topic} involves predictions about what comes next.",
    "Discussions surrounding {topic} often include comparisons with {entity}.",
    "Searches for {topic} frequently ask whether a particular release is worth watching or listening to.",
    "Box office numbers for {topic} are tracked closely during opening weekend by studios and critics alike.",
    "Trailers and teaser clips related to {topic} often go viral within hours of release.",
    "Critics' reviews and audience ratings on Rotten Tomatoes shape how fans talk about {topic}.",
    "Red carpet appearances and award show buzz frequently accompany news about {topic}.",
    "Concert setlists and tour announcements tied to {topic} spread quickly across social media.",
    "Chart performance on the Billboard Hot 100 is often cited in coverage of {topic}.",
]


# ============================================================
# POLITICS
# ============================================================

POLITICAL_TOPICS = [
    "elections",
    "voter turnout",
    "political polls",
    "government policy",
    "AI regulation",
    "technology regulation",
    "social media regulation",
    "online privacy",
    "misinformation",
    "deepfakes",
    "immigration policy",
    "climate policy",
    "renewable energy policy",
    "healthcare policy",
    "education policy",
    "tax policy",
    "housing policy",
    "economic policy",
    "trade wars",
    "tariffs",
    "international relations",
    "cybersecurity policy",
    "data privacy",
    "digital rights",
    "free speech online",
    "geopolitical tensions",
    "military alliances",
    "foreign policy",
    "government spending",
    "political polarization",
    "election candidates",
    "presidential campaigns",
    "congressional hearings",
    "senate confirmation votes",
    "parliamentary debates",
    "political party primaries",
    "campaign fundraising",
    "voting rights legislation",
    "government shutdowns",
    "coalition governments",
    "impeachment proceedings",
    "political rallies",
    "lobbying and special interests",
    "gerrymandering and redistricting",
]

POLITICAL_ENTITIES = [
    "the United States",
    "the European Union",
    "China",
    "India",
    "the United Kingdom",
    "NATO",
    "the United Nations",
    "Congress",
    "the Senate",
    "the House of Representatives",
    "the White House",
    "the European Parliament",
    "10 Downing Street",
]

POLITICAL_TEMPLATES = [
    "People searching for {topic} are often trying to understand what the issue means in practical terms.",
    "A major question surrounding {topic} is how government decisions could affect ordinary people.",
    "Online discussions about {topic} frequently focus on competing political arguments and their possible consequences.",
    "Understanding {topic} often requires looking at both domestic policy and international developments.",
    "Searches related to {topic} commonly ask who benefits from a particular policy and who could be negatively affected.",
    "One reason {topic} receives significant attention is its connection to the economy and everyday life.",
    "People following {topic} often want explanations of political terminology, proposed policies, and possible outcomes.",
    "Debates over {topic} frequently involve disagreements about government responsibility and individual rights.",
    "Social media has changed how people discover and discuss information about {topic}.",
    "Another major issue connected to {topic} is the spread of misleading or incomplete information online.",
    "Discussions about {topic} often involve countries and institutions such as {entity}.",
    "People researching {topic} frequently compare different policy approaches used around the world.",
    "Questions about {topic} often become more popular around elections, major announcements, or international events.",
    "The online conversation around {topic} often includes arguments about long-term consequences rather than only immediate events.",
    "Lawmakers debating {topic} often clash over how new legislation should be worded and enforced.",
    "Candidates on the campaign trail frequently address {topic} during rallies and televised debates.",
    "Voters weighing in on {topic} often want to know how each political party plans to handle the issue.",
    "Coverage of {topic} increases sharply during election season as candidates outline competing policy plans.",
    "Legislators at {entity} often clash over funding and enforcement when debating {topic}.",
    "Party leaders and elected officials have sparred publicly over {topic} ahead of the next vote.",
    "Polling on {topic} is closely watched by strategists as campaigns head toward election day.",
    "Senators grilled technology executives during a hearing on {topic}, pressing for stronger oversight.",
    "A Senate committee advanced a bill on {topic} after weeks of testimony from technology executives.",
    "Lawmakers accused major technology companies of resisting new rules on {topic} during a heated hearing.",
    "A bipartisan group of senators introduced legislation targeting {topic}, setting up a fight with technology companies.",
]


# ============================================================
# Category configuration
# ============================================================

CATEGORIES = {
    "Economics": (
        ECONOMIC_TOPICS,
        ECONOMIC_ENTITIES,
        ECONOMIC_TEMPLATES,
    ),
    "Entertainment": (
        ENTERTAINMENT_TOPICS,
        ENTERTAINMENT_ENTITIES,
        ENTERTAINMENT_TEMPLATES,
    ),
    "Politics": (
        POLITICAL_TOPICS,
        POLITICAL_ENTITIES,
        POLITICAL_TEMPLATES,
    ),
}


# ============================================================
# Generation helpers
# ============================================================

def capitalize_first(text):
    return text[0].upper() + text[1:] if text else text


def generate_sentence(rng, topics, entities, templates):
    topic = rng.choice(topics)
    entity = rng.choice(entities)
    template = rng.choice(templates)

    return template.format(
        topic=topic,
        entity=entity,
    )


def generate_document(rng, topics, entities, templates):
    sentence_count = rng.randint(*SENTENCES_PER_DOC)

    sentences = [
        generate_sentence(
            rng,
            topics,
            entities,
            templates,
        )
        for _ in range(sentence_count)
    ]

    return " ".join(
        capitalize_first(sentence)
        for sentence in sentences
    )


# ============================================================
# Main
# ============================================================

def main():
    rng = random.Random(RANDOM_STATE)

    CORPUS_DIR.mkdir(exist_ok=True)

    manifest_lines = [
        "filepath,category,word_count"
    ]

    total = 0

    for category, (
        topics,
        entities,
        templates,
    ) in CATEGORIES.items():

        category_dir = CORPUS_DIR / category
        category_dir.mkdir(exist_ok=True)

        for i in range(1, DOCS_PER_CATEGORY + 1):

            text = generate_document(
                rng,
                topics,
                entities,
                templates,
            )

            filename = f"doc_{i:04d}.txt"

            filepath = category_dir / filename

            filepath.write_text(
                text,
                encoding="utf-8",
            )

            word_count = len(text.split())

            manifest_lines.append(
                f"{category}/{filename},{category},{word_count}"
            )

            total += 1

        print(
            f"{category}: "
            f"{DOCS_PER_CATEGORY} documents written to "
            f"{category_dir}"
        )

    manifest_path = CORPUS_DIR / "manifest.csv"

    manifest_path.write_text(
        "\n".join(manifest_lines),
        encoding="utf-8",
    )

    print(
        f"Total: {total} documents. "
        f"Manifest: {manifest_path}"
    )


if __name__ == "__main__":
    main()


# Data Source & Copyright Notice — Task 2 Document Clustering Corpus

## Source

This corpus is a 210-document subset (70 per category) of the **BBC News
dataset** compiled by:

> D. Greene and P. Cunningham, "Practical Solutions to the Problem of
> Diagonal Dominance in Kernel Document Clustering", Proc. 23rd
> International Conference on Machine Learning (ICML 2006), 2006.

Dataset homepage (original release, distributed for non-commercial,
research/educational use): http://mlg.ucd.ie/datasets/bbc.html

The underlying articles are BBC News stories published on
`bbc.co.uk`/`news.bbc.co.uk` between 2004 and 2005. **All copyright in the
article text remains with the BBC.** These files are used here strictly
for the non-commercial, educational purpose of this Information Retrieval
coursework (document clustering), as permitted by the dataset's stated
usage terms, and are not redistributed or published beyond the submission
of this assignment.

## Category mapping

The assignment asks for three categories: **Economics, Entertainment,
Politics**. The Greene & Cunningham corpus uses five original BBC
sections: business, entertainment, politics, sport, tech. The `business`
section is used as the source for the **Economics** category in this
project, since BBC's "business" desk is where UK economic
news/analysis (GDP, inflation, interest rates, trade, corporate
earnings) is published; the `entertainment` and `politics` sections are
used unchanged.

## Composition

| Assignment category | Source BBC section | Documents used |
|---|---|---|
| Economics            | business      | 70 |
| Entertainment         | entertainment | 70 |
| Politics              | politics      | 70 |
| **Total**             |               | **210** |

Files were selected with a fixed random seed (42) from the full section
folders (business: 510 docs, entertainment: 386 docs, politics: 417 docs
available) to keep the three classes balanced.

## File format

Each `.txt` file is one news article. The first line is the headline,
followed by a blank line and the article body — this matches the
original Greene & Cunningham release format.

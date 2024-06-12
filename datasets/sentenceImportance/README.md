# Open Bible Data (OBD)
# Sentence Importance Dataset

## Introduction

This is a TSV file with at least one entry for every Bible ‘verse’ giving rough indications of
1/ the **‘importance’** of each verse, 2/ whether or not it **contains textual issues**,
and 3/ the **‘clarity’ (or ‘understandability’)** of the original Hebrew or Greek text.

Since ‘verses’ are totally artificial units
(sometimes being only part of a sentence, yet other times containing two or more sentences)
this dataset also has the ability to roughly specify the first or second half of the verse
(in the original language that is), especially if multiple sentences are involved.

NOTE: Don't use this datafile yet -- it's **STILL IN DEVELOPMENT and VERY PRELIMINARY**

## Importance

For example, Gen 1:1 ‘In the beginning God created the heavens and the earth.’
and John 14:6 ‘Jesus answered, “I am the way and the truth and the life. No one comes to the Father except through Me.’
would surely seem more important to everyone than something like 2 Tim 4:13
‘When you come, bring the cloak that I left with Carpus at Troas, and my scrolls, especially the parchments.’
or Col 4:14 ‘Luke, the beloved physician, and Demas send you greetings.’?

On the other hand, we don’t want to be trying to discriminate between a saying
that one Christian denomination gives little importance to or considers to no longer apply,
when another considers it important. So we don't want to try to be too fine-grained.

Hence the importance values are:

- 0=T=Trivial (like a forgotten cloak, or greetings from some person we know longer know)
- 1=M=Medium (the great majority of sentences in the Bible)
- 2=I=Important (specific statements that are commonly considered to be more important, and hence often memorised)
- 3=V=Vital (specific statements that are commonly found in doctrinal statements)

## Textual issues

Secondly, another field indicates potential textual (known by experts as ‘textual criticism’) issues.
For example if this ‘verse’/‘sentence’ (or some part of it) doesn’t occur in all the ancient manuscripts.
It may have been deleted by some, added by some, or (intentionally or accidentally) amended by some.

Hence the textual issue values are:

- 0=No issue (so most translations are working from the same Hebrew/Greek text here)
- 1=Minor spelling or word order issues (with pretty-much no effect on meaning)
- 2=Minor word changes (some words vary in manuscripts of different origins)
- 3=Major differences (any translations might be expected to have a footnote her to explain textual differences in the source)

## Clarity / Understandability

In addition, a third field indicates where commentators are unsure what was actually meant.
For example, in the above quote from 2 Timothy 4:13, we’re not sure if Paul meant _blank parchments_ (i.e., like a writing pad)
or _parchments that he wanted to read_ (i.e., like library books).
But other passages are much more obscure than that.

Hence the clarity values are:

- 0=O=Obscure (we can only really guess at what was meant, and hence we might expect translations to differ widely)
- 1=U=Unclear (we’re unsure exactly what was meant, like the parchment example above)
- 2=C=Clear (it seems clear enough what the author or speaker meant, as far as we know)

## TSV format

The first line of the tab-separated data file contains the four column headers:

**FGRef**: Freely-Given verse reference (see below)

**Importance**: T, M, I, or V (representing numerical values 0, 1, 2, or 3)

**TextualIssue**: 0, 1, 2, or 3

**Clarity**: O, U, or C (representing numerical values 0, 1, or 2)

Each line (including the final one) is ended with a single newline character.

There are AT LEAST 41,899 data lines, representing each verse of the Old Testament,
the New Testament, and then the Deutercanon books.
However, any single verse line can be divided into two where necessary (see below),
so the number of lines is likely to increase over time (until the data become stabilised).

## Reference keys

Freely-Given.org uses our own reference system:

1. The bookcode is always an UPPERCASE three-character code starting with a letter,
e.g., GEN, KI1, EZE, JNA, NAM, MAT, JAM, PE2, JN3, JDE, JDT, TOB, etc.
See https://Freely-Given.org/Software/BibleOrganisationalSystem/BOSBooksCodes.html
and https://GitHub.com/Freely-Given-org/BibleBooksCodes.
(In our documentation and software, we always represent this three-character bookcode as BBB.)
2. A verse reference is **BBB_C:V**, e.g., EZE_17:5.
3. Verse references **may be split into two parts**:
roughly representing the first half and second half of verse,
e.g., (on two separate lines) EZE_17:5**a** and EZE_17:5**b**.
Note: these might be ‘logical’ halves,
e.g., there might be two sentences in a verse
(even if the second sentence is 3x the length of the first one).
Of course, splitting references like this increases the number of lines in the file.

## Versification scheme

This table uses the ‘original’ (Hebrew/Greek) versification.
Amongst other things, this means that many Psalms appear to have an extra verse
compared to many English translations because the introductory text like
‘A Psalm of David’ (which is usually placed in a
[USFM](https://ubsicap.github.io/usfm/characters/index.html)
[\d field](https://ubsicap.github.io/usfm/titles_headings/index.html#d))
is marked as v1 (and so traditional English v1 text can be found in v2).

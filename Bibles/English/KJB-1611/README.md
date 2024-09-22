# Open Bible Data KJB-1611 USFM

This is not the normal 1769 **King James Bible** that many people are so used to,
but rather a transcription of the original printing of one of the 1611 printings.

We are very grateful to [archive.org](https://archive.org) for hosting a facsimile
version of the 1611 ‘he’ printing of the King James Bible at
[[https://archive.org/details/1611TheAuthorizedKingJamesBible/]].

A transcription of the text is available at
[[https://en.wikisource.org/wiki/Bible_(King_James_Version,_1611)]].

## Markup

These files are [USFM 3.0](https://ubsicap.github.io/usfm/)
with some internal character markup including **\add** and **\nd** markers.
Marginal notes in the original printing are included as USFM footnotes
(even if many of them are actually cross-references).
Note that the footnote callers preceded the word (or words) being annotated
(which differs from modern styles where the callers tend to *follow* the text).

Note that words considered to be ‘added’ by the translators are marked in the publication
by printing them in a smaller font.
Because we’re more interested in knowing the thoughts of the early translators and
publishers (rather than being 100% tied to the ‘he’ printing),
we would also mark any text in these files which is marked as added text in the ‘she’ printing as well.

## Content

Filenames are in the form ‘KJB-1611_BBB.usfm’ where ‘BBB’ represents the three-character
Bible Book Code from [[https://Freely-Given.org/Software/BibleOrganisationalSystem/BOSBooksCodes.html]].

The 1611 KJB also included a section labelled ‘Apocrypha’
(between the ‘Olde Testament’ and the ‘New Testament’)
which included an additional fifteen ‘books’,
making a total of eighty-two USFM files here including the ‘FRT’ preface.

## Unfinished

Many footnotes remain at the start of the verse in question
and need to be manually moved to their correct position.
This can be done by looking at pages like
[[https://archive.org/details/1611TheAuthorizedKingJamesBible/page/n78/mode/1up?view=theater]]
and then noting where the footnote callers are placed and correcting the USFM files.
(If you wish to help with this, you would need to fork this repository
and create a new branch where you could edit your copy of these files,
then submit a merge or ‘pull’ request.)

# License

Publications from the 1600’s are out of copyright in most countries—England
being the exception where it might still be under Crown copyright.
As far as any of our own work is concerned (in formatting the KJB text in USFM files),
our work here is placed in the public domain and no copyright claim is asserted.

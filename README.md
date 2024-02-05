# Open Bible Data (OBD)

Code and datasets for the OpenBibleData project

This consists of three main components:

1. Some public domain or open-licenced Bible source files copied from other sites
2. Our own _sentenceImportance_ database (giving an importance value for each ‘verse’/‘sentence’)
3. Python code to generate a static website from the various Bible file sets

The copied Bibles are not committed yet (because we're unsure about ‘redistribution’ rights/licensing even for open-licensed resources)

The preliminary static website can currently be viewed (in an iFrame) at
[OpenEnglishTranslation.Bible](https://OpenEnglishTranslation.Bible/) at the <em>Reader</em> link
or directly at [Freely-Given.org/OBD](https://Freely-Given.org/OBD/).

Currently the static website is approx 9 GB
and includes almost thirty Bible translations
along with multiple Hebrew and Greek originals,
and then parallel and interlinear verse pages with two sets of notes for translators,
related/parallel section pages, and two dictionaries.

## Future Plans

The site doesn't yet contain any Strongs-indexed lexicons,
and so links to BibleHub.com for that.

Search functionality is provided by [Pagefind](https://Pagefind.app/).

Hopefully if BibleOrgSys is able to start using more Rust functions in the future,
then the memory use should reduce and the site build time should be greatly increased.
(Currently taking 94 minutes and using most of the 64GB RAM.)

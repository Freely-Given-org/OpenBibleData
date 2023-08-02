# Open Bible Data

Code and datasets for the OpenBibleData project

This consists of two main components:

1. Some public domain or open-licenced Bible source files copied from other sites
2. Python code to generate a static website from the various Bible file sets

The copied Bibles are not committed yet.

The preliminary static website can currently be viewed (in an iFrame) at
[OpenEnglishTranslation.Bible](https://OpenEnglishTranslation.Bible/) at the <em>Reader</em> link
or directly at [Freely-Given.org/OBD](https://Freely-Given.org/OBD/).

Currently the static website is approx 3 GB.

## Future Plans

The site doesn't yet contain any lexicons, and so links to BibleHub.com for that.

There's no search functionality yet.

Hopefully if BibleOrgSys is able to start using more Rust functions in the future,
then the memory use should reduce and the site build time should be greatly increased.
(Currently taking 94 minutes and using most of the 64GB RAM.)

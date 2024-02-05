# Open Bible Data (OBD)
# Sentence Importance Dataset

This is a TSV file with an entry for every Bible ‘verse’/‘sentence’
giving an ‘importance’ number.

For example, Gen 1:1 ‘In the beginning God created the heavens and the earth.’
and John 14:6 ‘Jesus answered, “I am the way and the truth and the life. No one comes to the Father except through Me.’
would surely seem more important to everyone than something like 2 Tim 4:13
‘When you come, bring the cloak that I left with Carpus at Troas, and my scrolls, especially the parchments.’
or Col 4:14 ‘Luke, the beloved physician, and Demas send you greetings.’?

On the other hand, we don’t want to be trying to discriminate between a saying
that one Christian denomination gives little importance to or considers to no longer apply,
when another considers it important. So we don't want to try to be too fine-grained.

Hence the importances values are:

1. Trivial (like a forgotten cloak, or greetings from some person we know longer know)
2. Medium (the great majority of sentences in the Bible)
3. Important (specific statements that are commonly considered to be more important, and hence often memorised)
4. Vital (specific statements that are commonly found in doctrinal statements)

Secondly, another field indicates potential textual (known by experts as ‘textual criticism’) issues.
This ‘verse’/‘sentence’ doesn’t occur in all the ancient manuscripts.
It may have been deleted by some, added by some, or (intentionally or accidentally) amended by some.

Hence the textual issue values are:

1. No issue (so most translations are working from the same Hebrew/Greek text here)
2. Minor spelling or word order issues (with pretty-much no effect on meaning)
3. Minor word changes (some words vary in manuscripts of different origins)
4. Major differences (a footnote might be expected to explain textual differences)

In addition, a third field indicates where commentators are unsure what was actually meant.
For example, in the above quote from 2 Timothy, we’re not sure if Paul meant _blank parchments_ (i.e., like a writing pad)
or _parchments that he wanted to read_ (i.e., like library books).
But other passages are much more obscure than that.

Hence the clarity values are:

1. Obscure (we can only really guess at what was meant, and hence we might expect translations to differ widely)
2. Unclear (we’re unsure exactly what was meant, like the parchment example above)
3. Clear (it seems clear enough what the author or speaker meant, as far as we know)


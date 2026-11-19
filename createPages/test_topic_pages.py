#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Check the topic page subheading ids and contents line.

CHANGELOG:
    2026-11-19 First version
"""
import unittest

from createTopicPages import topicHeadingId, topicHeadingContents


class TopicHeadingTests(unittest.TestCase):
    def test_ids_are_readable_unique_and_clear_of_verse_ids(self):
        used = set()
        self.assertEqual(topicHeadingId('Witness through words and conduct', used), 'WitnessThroughWordsAndConduct')
        self.assertEqual(topicHeadingId('Claim: <span style="background-color:khaki;">Jesus died</span>', used), 'ClaimJesusDied')
        self.assertEqual(topicHeadingId('Witness through words and conduct', used), 'WitnessThroughWordsAndConduct2')
        self.assertEqual(topicHeadingId('Yonah’s reluctance', used), 'YonahSReluctance')
        self.assertEqual(topicHeadingId('C3 v4', used), 'HC3V4')
        self.assertEqual(topicHeadingId('2 kings', used), 'H2Kings')
        self.assertEqual(topicHeadingId('“”', used), 'Heading')

    def test_contents_only_for_more_than_one_heading(self):
        self.assertEqual(topicHeadingContents([]), '')
        self.assertEqual(topicHeadingContents([('A','Only one')]), '')
        html = topicHeadingContents([('GoodNews','Good news'), ('Claim','Claim: <span style="x">Jesus died</span>')])
        self.assertEqual(html, '<p class="topicContents">Contents: <a href="#GoodNews">Good news</a> · <a href="#Claim">Claim: Jesus died</a></p>\n')


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Regression checks for OBD's parallel build-state wrapper.

CHANGELOG:
    2026-10-16 Verify ordered results, child state, and cleanup after failure.
"""
import multiprocessing
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Misc.Parallel import ParallelTaskError
from parallel import runParallelPages


def read_state(value):
    return value, BibleOrgSysGlobals.alreadyMultiprocessing


def fail(_):
    raise ValueError('KJB-1611 SA1 13:7And')


@unittest.skipUnless('fork' in multiprocessing.get_all_start_methods(), 'OBD requires fork')
class ParallelPageTests(unittest.TestCase):
    def test_order_and_inherited_multiprocessing_flag(self):
        with patch.object(BibleOrgSysGlobals,'alreadyMultiprocessing',False), \
             patch.object(BibleOrgSysGlobals,'maxProcesses',2):
            result = runParallelPages(read_state,[3,1,2],taskNames=['three','one','two'],freshProcess=True)
            self.assertEqual(result,[(3,True),(1,True),(2,True)])
            self.assertFalse(BibleOrgSysGlobals.alreadyMultiprocessing)

    def test_failure_restores_parent_state(self):
        for previous in (False,True):
            with patch.object(BibleOrgSysGlobals,'alreadyMultiprocessing',previous), \
                 patch.object(BibleOrgSysGlobals,'maxProcesses',2):
                with self.assertRaisesRegex(ParallelTaskError,'7And'):
                    runParallelPages(fail,[None],taskNames=['parallel verses SA1'])
                self.assertIs(BibleOrgSysGlobals.alreadyMultiprocessing,previous)


if __name__ == '__main__':
    unittest.main()

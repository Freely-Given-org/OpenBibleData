#!/usr/bin/env -S uv run
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run OBD page jobs with inherited datasets and visible worker failures.

CHANGELOG:
    2026-10-16 Use BOS fail-fast workers and restore multiprocessing state on errors.
"""
import multiprocessing

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Misc.Parallel import run_parallel


def runParallelPages(function, parameters, *, taskNames, freshProcess=False):
    """Preserve input order and fork sharing; stop the build when any task fails."""
    previous = BibleOrgSysGlobals.alreadyMultiprocessing
    BibleOrgSysGlobals.alreadyMultiprocessing = True
    try:
        return run_parallel(function, parameters, processes=BibleOrgSysGlobals.maxProcesses,
            context=multiprocessing.get_context('fork'), labels=taskNames,
            chunksize=1 if freshProcess else None)
    finally:
        BibleOrgSysGlobals.alreadyMultiprocessing = previous

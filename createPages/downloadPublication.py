#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Preserve independently built downloads when replacing generated OBD pages.

CHANGELOG:
    2026-11-06 Preserve published OET PDFs across site cleanup and promotion.
"""
from pathlib import Path
import shutil


def cleanVersionFolder(folder: Path, *, keepDownloads: bool = False):
    if not folder.exists():
        return
    if keepDownloads and (folder / 'Downloads').is_dir():
        for child in folder.iterdir():
            if child.name != 'Downloads':
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()
    else:
        shutil.rmtree(folder)


def moveGeneratedEntry(source: Path, destination: Path):
    target = destination / source.name
    if source.name == 'OET' and target.is_dir() and (target / 'Downloads').is_dir():
        if (source / 'Downloads').exists():
            raise ValueError('Staged OET Downloads must not overwrite independently published PDFs')
        for child in source.iterdir():
            shutil.move(child, target / child.name, copy_function=shutil.copy2)
        source.rmdir()
    else:
        shutil.move(source, destination, copy_function=shutil.copy2)

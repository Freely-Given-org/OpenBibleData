#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Persistent derived editions, shared by every consumer of substituted text.

The BOS substitutions operate on HTML (including phrase and footnote markup),
so these editions store their exact results rather than altering USFM entries.
One pickle per version holds native-reference-indexed fragments for all views.
Different rendering/options at the same reference are separate variants. Book
workers inherit the editions and return additions to the parent, the sole writer
within a build. A partial build simply adds the passages it actually requested.

CHANGELOG:
    2026-10-21 Cache all ten substituted editions with source/table date checks.
"""
from hashlib import sha256
from importlib import import_module
from importlib.util import find_spec
import logging
import os
from pathlib import Path
import pickle
import tempfile
import fcntl


ENGLISH_VERSIONS = ('RV', 'KJB-1769', 'KJB-1611', 'Bshps', 'Gnva', 'Cvdl', 'TNT', 'Wycl')
SUBSTITUTED_VERSIONS = (*ENGLISH_VERSIONS, 'Luth', 'ClVg')
FORMAT_VERSION = 1
PICKLE_SUFFIX = '.OBD_Substituted.pickle'
_TABLE_MODULES = {version: 'OldBiblicalEnglish' for version in ENGLISH_VERSIONS}
_TABLE_MODULES.update(Luth='LutherGermanToEnglish', ClVg='VulgateLatinToEnglish')


def sourceManifest(location) -> tuple:
    """Record source paths, sizes and nanosecond dates, including added/deleted files.

    Directory Bibles can have source subdirectories. Generated pickles, backups,
    logs and Python caches must not invalidate themselves or the derived editions.
    A missing source is an error, not permission to serve an old cached Bible.
    """
    root = Path(location).resolve(strict=True)
    paths = [root] if root.is_file() else (
        path for path in root.rglob('*') if path.is_file()
        and not any(part.startswith('.') or part == '__pycache__'
                    for part in path.relative_to(root).parts)
        and not path.name.endswith(('.pickle', '.pyc', '.log', '.tmp'))
        and '.bak' not in path.name)
    return tuple(sorted(_fileStamp(path) for path in paths))


def _fileStamp(path) -> tuple:
    path = Path(path).resolve(strict=True)
    stat = path.stat()
    return str(path), stat.st_mtime_ns, stat.st_size


def wordTablePath(version: str) -> Path:
    # find_spec locates the module without executing its large word tables.
    spec = find_spec(f'BibleOrgSys.Reference.{_TABLE_MODULES[version]}')
    if spec is None or spec.origin is None:
        raise ImportError(f'Cannot locate substitution table for {version}')
    return Path(spec.origin)


def substitute(version: str, text: str, allowOptions: bool = False) -> str:
    """Import the expensive tables only when a derived fragment needs building."""
    module = import_module(f'BibleOrgSys.Reference.{_TABLE_MODULES[version]}')
    if version in ENGLISH_VERSIONS:
        return module.moderniseEnglishWords(text, allowOptions=allowOptions)
    return (module.translateGerman if version == 'Luth' else module.translateLatin)(text)


def _readPickle(path):
    try:
        with path.open('rb') as stream:
            data = pickle.load(stream)
        if (not isinstance(data, dict) or data.get('format') != FORMAT_VERSION
                or not isinstance(data.get('entries'), dict)
                or not isinstance(data.get('dependencies'), dict)
                or not isinstance(data.get('version'), str)):
            raise ValueError('incompatible substituted-edition format')
        # These files contain only simple keys and strings, never BOS objects.
        for key, value in data['entries'].items():
            if (not isinstance(key, tuple) or len(key) != 4
                    or not all(isinstance(part, str) for part in (key[0], key[1], key[3]))
                    or not isinstance(key[2], bool) or not isinstance(value, str)):
                raise ValueError('invalid substituted-edition entry')
        return data
    except FileNotFoundError:
        return None
    except (OSError, EOFError, pickle.UnpicklingError, ValueError, TypeError,
            AttributeError, ImportError) as error:
        logging.warning('Rebuilding substituted edition %s: %s', path, error)
        return None


class SubstitutedVersions:
    """One logical derived Bible per version; originals remain unmodified."""

    def __init__(self, folder, locations, *, enabled=True, load=True):
        self.folder = Path(folder)
        self.locations = {v: location for v, location in locations.items()
                          if v in SUBSTITUTED_VERSIONS}
        self.enabled, self.load = enabled, load
        self.dependencies, self.entries, self.additions = {}, {}, {}
        self.hits = self.substitutions = 0
        for version, location in self.locations.items():
            self.dependencies[version] = {
                'sources': sourceManifest(location),
                'table': _fileStamp(wordTablePath(version)),
                'implementation': _fileStamp(__file__),
            }
            data = _readPickle(self.path(version)) if enabled and load else None
            valid = (data is not None and data.get('version') == version
                     and data.get('dependencies') == self.dependencies[version])
            self.entries[version] = data['entries'] if valid else {}
            self.additions[version] = {}
            if enabled:
                reason = 'cache loading disabled' if not load else 'missing or invalid pickle'
                if data is not None and not valid:
                    changed = [name for name, stamp in self.dependencies[version].items()
                               if data.get('dependencies', {}).get(name) != stamp]
                    reason = 'changed ' + ', '.join(changed or ['version'])
                logging.info('Substituted %s: %s', version,
                             f"loaded {len(self.entries[version]):,} fragments" if valid
                             else f'rebuilding on demand ({reason})')

    def path(self, version):
        return self.folder / f'{version}{PICKLE_SUFFIX}'

    def get(self, version: str, reference: str, text: str, *, kind='text', allowOptions=False) -> str:
        """Return an exact substitution, retaining all native-reference variants.

        Hashing the actual input also catches changes to rendering, mappings,
        links and preprocessing without invalidating every edition on a CSS edit.
        Spelling checks and page-specific comparisons run after this lookup.
        """
        if version not in self.entries:
            raise KeyError(f'Substituted edition {version} was not prepared')
        key = (reference, kind, bool(allowOptions), sha256(text.encode('utf-8')).hexdigest())
        if self.enabled and key in self.entries[version]:
            self.hits += 1
            return self.entries[version][key]
        result = substitute(version, text, allowOptions)
        self.substitutions += 1
        if self.enabled:
            self.entries[version][key] = self.additions[version][key] = result
        return result

    def startWorker(self):
        """Discard inherited parent counters/additions, retaining shared editions."""
        self.hits = self.substitutions = 0
        self.additions = {version: {} for version in self.entries}

    def workerResult(self):
        return self.additions, self.hits, self.substitutions

    def mergeWorkerResult(self, result):
        additions, hits, substitutions = result
        for version, fragments in additions.items():
            self.entries[version].update(fragments)
            self.additions[version].update(fragments)
        self.hits += hits
        self.substitutions += substitutions

    def save(self):
        """Publish complete version files atomically, merging concurrent additions."""
        if not self.enabled or not any(self.additions.values()):
            return
        self.folder.mkdir(parents=True, exist_ok=True)
        for version, additions in self.additions.items():
            if not additions:
                continue
            expected = self.dependencies[version]
            if (sourceManifest(self.locations[version]) != expected['sources']
                    or _fileStamp(wordTablePath(version)) != expected['table']
                    or _fileStamp(__file__) != expected['implementation']):
                raise RuntimeError(f'{version} sources or substitution code changed during the build; rerun it')
            path = self.path(version)
            # Book workers never write these files. The lock also protects two
            # independently running site builds from discarding one another's work.
            with path.with_suffix('.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                data = _readPickle(path) if self.load else None
                entries = {}
                if (data is not None and data.get('version') == version
                        and data.get('dependencies') == expected):
                    entries.update(data['entries'])
                entries.update(self.entries[version])
                payload = dict(format=FORMAT_VERSION, version=version,
                               dependencies=expected, entries=entries)
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(dir=self.folder, prefix=f'.{version}-',
                                                     suffix='.tmp', delete=False) as stream:
                        temporary = Path(stream.name)
                        pickle.dump(payload, stream, protocol=pickle.HIGHEST_PROTOCOL)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, path)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
                additions.clear()


def prepareSubstitutedVersions(state):
    """Load once in the parent; forked page workers inherit these editions."""
    if 'substitutedVersions' not in vars(state):
        locations = {version: state.BibleLocations[version]
                     for version in state.preloadedBibles
                     if version in SUBSTITUTED_VERSIONS
                     and version in state.BibleVersions
                     and (not state.TEST_VERSIONS_ONLY or version in state.TEST_VERSIONS_ONLY)}
        editions = SubstitutedVersions(state.SUBSTITUTED_VERSIONS_FOLDER, locations,
            enabled=state.CACHE_SUBSTITUTED_VERSIONS_FLAG,
            load=state.LOAD_RESOURCES_FROM_PICKLES_FLAG)
        for version in locations:
            loadedSources = getattr(state.preloadedBibles[version], '_OBDSourceManifest', None)
            if loadedSources is not None and loadedSources != editions.dependencies[version]['sources']:
                raise RuntimeError(f'{version} sources changed since loading the Bible; rerun the build')
        state.substitutedVersions = editions
    return state.substitutedVersions


def getSubstitutedText(state, version, reference, text, *, kind='text', allowOptions=False):
    return prepareSubstitutedVersions(state).get(version, reference, text,
                                                 kind=kind, allowOptions=allowOptions)


def saveSubstitutedVersions(state):
    editions = prepareSubstitutedVersions(state)
    editions.save()
    from BibleOrgSys.BibleOrgSysGlobals import vPrint
    vPrint('Normal', False, f'Substituted editions: {editions.hits:,} cache hits; '
                           f'{editions.substitutions:,} substitutions this run')

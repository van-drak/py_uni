# Implement class ‹Merkle› which provides the following methods:
#
#  • ‹__init__( conn )› sets up the object, using ‹conn› as the
#    database connection (you can assume that this is an ‹sqlite3›
#    connection),
#  • ‹store( path )› stores the tree corresponding to the directory
#    ‹path› from the filesystem into the database (see below about
#    format) and returns its hash,
#  • ‹diff_path( hash_old, path_new )› computes a recursive diff
#    between the directory given by the ‹hash_old› stored in the
#    database and the directory given by ‹path_new› (in the
#    filesystem),
#  • ‹diff( hash_old, hash_new )› computes a recursive diff between
#    two directories stored in the database,
#  • ‹fetch( hash, path )› creates directory ‹path› in the
#    filesystem (it is an error if it already exists, or if anything
#    else is in the way) and makes a copy of the tree with root
#    directory given by ‹hash› (from the database into the
#    filesystem), returning ‹True› on success and ‹False› on error,
#  • ‹find( root_hash, node_path )› returns the hash of a node that
#    is reached by following ‹node_path› starting from the directory
#    given by ‹root_hash›, or ‹None› if there is no such node.
#
# The format of the trees is as follows:
#
#  • a regular file corresponds to a leaf node, and its hash is
#    simply the hash of its content,
#  • a directory node is a list of (item hash, item name) tuples; to
#    compute its hash, sort the tuples lexicographically by name,
#    separate the item hash from the name by a single space, and put
#    each tuple on a separate line (each line ended by a newline
#    character).
#
# These are the only node types. The same node (two nodes are the
# same if they have the same hash) must never be stored in the
# database twice. The ‹find› operation must be «fast» even for very
# large directories (i.e. do not scan directories sequentially).
# Paths are given as strings, components separated by a single ‹/›
# (forward slash) character.
#
# The recursive diff should be returned as a ‹dict› instance with
# file paths as its keys, where:
#
#  • a path appears in the dictionary if it appears in either of
#    the trees being compared (except if it is in both, and the
#    content of the associated files is the same),
#  • the values are ‹Diff› objects, with the following methods:
#    ◦ predicates ‹is_new›, ‹is_removed› and ‹is_changed›,
#    ◦ ‹old_content›, ‹new_content› which return a ‹bytes› object
#      with the content of the respective file (if applicable),
#    ◦ ‹unified› which returns a ‹str› instance with a
#      ‹difflib›-formatted unified diff (it is the responsibility of
#      the caller to make sure the files are utf8-encoded text
#      files).
#
# For instance, doing ‹diff( foo, foo )› should return an empty
# ‹dict›. You are encouraged to fetch the file content lazily.
# Diffing trees with a few hundred files each, where most files are
# 100MiB, should be very fast and use very little memory if we only
# actually read the content diff for a single small file.
#
# The hashes are SHA-2 256 and in the API, they are always passed
# around as a ‹bytes› object (which contains the raw hash, 32 bytes
# long).

# when hashing directories, the sub-hashes should be hex-formatted
# (not raw bytes) – bytes are only used in the API

# only create Diff object for files (they don't really make much
# sense for directories), i.e. if a single file differs,
# there should only be one item in the resulting dictionary;
# do include the item if one of the sides has a directory
# in place of a file or vice versa, and treat it the same
# as addition or deletion of the file (i.e. as if the directory did not exist)

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from hashlib import sha256
from pathlib import Path
from difflib import unified_diff
import sqlite3


class Diff:
    def __init__(self) -> None:
        self.old_data: Optional[bytes] = None
        self.new_data: Optional[bytes] = None

    def is_new(self) -> bool:
        return self.old_data is None and self.new_data is not None

    def is_changed(self) -> bool:
        return self.old_data is not None and self.new_data is not None

    def is_removed(self) -> bool:
        return self.old_data is not None and self.new_data is None

    def old_content(self) -> bytes:
        if self.old_data is None:
            raise RuntimeError('File has no old content')
        return self.old_data

    def new_content(self) -> bytes:
        if self.new_data is None:
            raise RuntimeError('File has no new content')
        return self.new_data

    def unified(self) -> str:
        if self.old_data is None or self.new_data is None:
            raise RuntimeError(
                'Can not compare file with missing old or new content')

        res = ''
        for row in unified_diff(self.old_data.decode('utf-8').split('\n'), self.new_data.decode('utf-8').split('\n')):
            res += row + '\n' if len(row) > 0 and row[-1] != '\n' else row

        return res


class Merkle:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        conn.cursor().execute(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                hash BLOB NOT NULL,
                is_file INT NOT NULL,
                PRIMARY KEY(hash)
            );
            """
        )
        conn.cursor().execute(
            """ 
            CREATE TABLE IF NOT EXISTS contains (
                parent BLOB NOT NULL, 
                child_name TEXT NOT NULL,
                child_hash BLOB NOT NULL,
                PRIMARY KEY(parent, child_name)
            );
            """
        )
        conn.cursor().execute(
            """
            CREATE TABLE IF NOT EXISTS contents (
                hash BLOB NOT NULL,
                data BLOB NOT NULL,
                PRIMARY KEY(hash)
            );
            """
        )

    def store(self, path: str) -> bytes:
        if not (Path(path).exists()):
            raise RuntimeError('Path is invalid')

        return self.store_rec(Path(path))

    def store_rec(self, node: Path) -> bytes:
        cur = self.conn.cursor()
        if node.is_file():
            data = node.read_bytes()
            hash = sha256(data).digest()
            cur.execute(
                'INSERT OR IGNORE INTO contents(hash, data) VALUES (?, ?);', (hash, data))
        elif node.is_dir():
            tmp: List[Tuple[str, bytes]] = []
            for child in node.iterdir():
                tmp.append((child.name, self.store_rec(child)))

            str_hash = b''
            for child_name, child_hash in sorted(tmp):
                str_hash += f'{child_hash.hex()} {child_name}\n'.encode('utf-8')

            hash = sha256(str_hash).digest()
            for child_name, child_hash in tmp:
                cur.execute('INSERT OR IGNORE INTO contains(parent, child_name, child_hash) VALUES (?, ?, ?);',
                            (hash, child_name, child_hash))
        else:
            raise RuntimeError(f'{node} is invalid type of file')

        cur.execute(
            'INSERT OR IGNORE INTO nodes(hash, is_file) VALUES (?, ?);', (hash, node.is_file()))
        self.conn.commit()

        return hash

    def build_from_path(self, f: Path, path: str) -> Dict[str, Diff]:
        res: Dict[str, Diff] = dict()
        if f.is_file():
            res[path] = Diff()
            res[path].new_data = f.read_bytes()
        elif f.is_dir():
            for child in f.iterdir():
                res.update(self.build_from_path(
                    child, self.build_path(path, f.name)))

        return res

    def diff_path_rec(self, hash_old: bytes, path_new: Path, path: str) -> Dict[str, Diff]:
        cur = self.conn.cursor()
        tmp_old = cur.execute(
            'SELECT is_file FROM nodes WHERE hash=?;', (hash_old,)).fetchone()
        if tmp_old is None:
            raise RuntimeError('Invalid hash')

        old_is_file, = tmp_old
        res: Dict[str, Diff] = dict()
        res[path] = Diff()
        if old_is_file:
            res[path].old_data, = cur.execute(
                'SELECT data FROM contents WHERE hash=?;', (hash_old,)).fetchone()
        if path_new.is_file():
            res[path].new_data = path_new.read_bytes()
            if not old_is_file:
                res.update(self.build_folder(hash_old, False, path))
        if res[path].old_data == res[path].new_data:
            del res[path]

        if path_new.is_dir():
            for child in path_new.iterdir():
                tmp = cur.execute(
                    'SELECT child_hash FROM contains WHERE parent=? AND child_name=?;', (hash_old, child.name)).fetchone()
                if tmp is None:
                    res.update(self.build_from_path(
                        child, self.build_path(path, child.name)))
                else:
                    child_hash, = tmp
                    res.update(self.diff_path_rec(
                        child_hash, child, self.build_path(path, child.name)))

        return res

    def diff_path(self, hash_old: bytes, path_new: str) -> Dict[str, Diff]:
        if not(Path(path_new).exists()):
            raise RuntimeError('Invalid path')
        return self.diff_path_rec(hash_old, Path(path_new), '')

    def diff(self, hash_old: bytes, hash_new: bytes) -> Dict[str, Diff]:
        return self.diff_rec(hash_old, hash_new, '')

    def file_comparison(self, old: Tuple[bytes, bool], new: Tuple[bytes, bool]) -> Diff:
        old_hash, old_is_file = old
        new_hash, new_is_file = new
        res = Diff()
        if old_is_file:
            res.old_data, = self.conn.cursor().execute(
                'SELECT data FROM contents WHERE hash=?;', (old_hash,)).fetchone()
        if new_is_file:
            res.new_data, = self.conn.cursor().execute(
                'SELECT data FROM contents WHERE hash=?;', (new_hash,)).fetchone()

        return res

    def build_folder(self, node: bytes, is_new: bool, path: str) -> Dict[str, Diff]:
        res: Dict[str, Diff] = dict()
        cur = self.conn.cursor()
        is_file, = cur.execute(
            'SELECT is_file FROM nodes WHERE hash=?;', (node,)).fetchone()
        if is_file:
            res[path] = Diff()
            data, = cur.execute(
                'SELECT data FROM contents WHERE hash=?;', (node,)).fetchone()
            if is_new:
                res[path].new_data = data
            else:
                res[path].old_data = data
            return res

        for name, hash in cur.execute('SELECT child_name, child_hash FROM contains WHERE parent=?;', (node,)):
            res.update(self.build_folder(hash, is_new, path + '/' + name))

        return res

    def build_path(self, path: str, to_add: str) -> str:
        return path + '/' + to_add if path != '' else to_add

    def diff_rec(self, old: bytes, new: bytes, path: str) -> Dict[str, Diff]:
        if old == new:
            return dict()

        cur = self.conn.cursor()
        tmp_old = cur.execute(
            'SELECT is_file FROM nodes WHERE hash=?;', (old,)).fetchone()
        old_is_file, = tmp_old if tmp_old is not None else (None,)
        tmp_new = cur.execute(
            'SELECT is_file FROM nodes WHERE hash=?;', (new,)).fetchone()
        new_is_file, = tmp_new if tmp_new is not None else (None,)
        if old_is_file is None or new_is_file is None:
            raise RuntimeError('Invalid hashes of the objects')

        res: Dict[str, Diff] = dict()
        if old_is_file or new_is_file:
            res[path] = self.file_comparison(
                (old, old_is_file), (new, new_is_file))

        old_children: List[Tuple[str, bytes]] = [selected for selected in cur.execute(
            'SELECT child_name, child_hash FROM contains WHERE parent=?;', (old,))]
        new_children: List[Tuple[str, bytes]] = [selected for selected in cur.execute(
            'SELECT child_name, child_hash FROM contains WHERE parent=?;', (new,))]

        used: List[str] = []
        for old_name, old_hash in old_children:
            for new_name, new_hash in new_children:
                if old_name != new_name:
                    continue

                used.append(old_name)
                res.update(self.diff_rec(old_hash, new_hash,
                                         self.build_path(path, old_name)))

        for name, hash in old_children:
            if not name in used:
                res.update(self.build_folder(
                    hash, False, self.build_path(path, name)))

        for name, hash in new_children:
            if not name in used:
                res.update(self.build_folder(
                    hash, True, self.build_path(path, name)))

        return res

    def fetch_creation(self, conn: sqlite3.Connection, path: str, hash: bytes, name: str) -> None:
        cur = conn.cursor()
        new_path = path + name
        is_file, = cur.execute(
            'SELECT is_file FROM nodes WHERE hash=?;', (hash,)).fetchone()

        if is_file:
            data, = cur.execute(
                'SELECT data FROM contents WHERE hash=?;', (hash,)).fetchone()
            with open(path + name, 'wb') as f:
                f.write(data)
        else:
            Path(path + name).mkdir()
            for child_name, child_hash in cur.execute('SELECT child_name, child_hash FROM contains WHERE parent=?;', (hash,)):
                self.fetch_creation(conn, new_path + '/',
                                    child_hash, child_name)

    def fetch(self, hash: bytes, path: str) -> bool:
        try:
            if path[-1] != '/':
                path += '/'
            self.fetch_creation(self.conn, path, hash, '')

            return True
        except BaseException as e:
            return False

    def find(self, root_hash: bytes, node_path: str) -> Optional[bytes]:
        if node_path is None:
            raise ValueError(f'Invalid path')

        path = node_path.split('/')
        if path[0] == '':
            path.pop(0)

        if len(path) > 0 and path[-1] == '':
            path.pop(-1)

        cur = self.conn.cursor()

        for node_name in path:
            tmp_hash = cur.execute("""
            SELECT child_hash FROM contains WHERE parent = ? and child_name = ?
            """, (root_hash, node_name)).fetchone()

            if tmp_hash is None:
                return None

            root_hash, = tmp_hash

        return root_hash

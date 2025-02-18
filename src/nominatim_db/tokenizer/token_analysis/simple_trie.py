# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Simple dict-based implementation of a trie structure.
"""
from typing import TypeVar, Generic, Tuple, Optional, List, Dict
from collections import defaultdict

T = TypeVar('T')


class SimpleTrie(Generic[T]):
    """ A simple read-only trie structure.
        This structure supports examply one lookup operation,
        which is longest-prefix lookup.
    """

    def __init__(self, data: Optional[List[Tuple[str, T]]] = None) -> None:
        self._tree: Dict[str, 'SimpleTrie[T]'] = defaultdict(SimpleTrie[T])
        self._value: Optional[T] = None
        self._prefix = ''

        if data:
            for key, value in data:
                self._add(key, 0, value)

            self._make_compact()

    def _add(self, word: str, pos: int, value: T) -> None:
        """ (Internal) Add a sub-word to the trie.
            The word is added from index 'pos'. If the sub-word to add
            is empty, then the trie saves the given value.
        """
        if pos < len(word):
            self._tree[word[pos]]._add(word, pos + 1, value)
        else:
            self._value = value

    def _make_compact(self) -> None:
        """ (Internal) Compress tree where there is exactly one subtree
            and no value.

            Compression works recursively starting at the leaf.
        """
        for t in self._tree.values():
            t._make_compact()

        if len(self._tree) == 1 and self._value is None:
            assert not self._prefix
            for k, v in self._tree.items():
                self._prefix = k + v._prefix
                self._tree = v._tree
                self._value = v._value

    def longest_prefix(self, word: str, start: int = 0) -> Tuple[Optional[T], int]:
        """ Return the longest prefix match for the given word starting at
            the position 'start'.

            The function returns a tuple with the value for the longest match and
            the position of the word after the match. If no match was found at
            all, the function returns (None, start).
        """
        cur = self
        pos = start
        result: Tuple[Optional[T], int] = None, start

        while True:
            if cur._prefix:
                if not word.startswith(cur._prefix, pos):
                    return result
                pos += len(cur._prefix)

            if cur._value:
                result = cur._value, pos

            if pos >= len(word) or word[pos] not in cur._tree:
                return result

            cur = cur._tree[word[pos]]
            pos += 1

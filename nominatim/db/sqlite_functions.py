# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Custom functions for SQLite.
"""
from typing import cast, Optional, Set, Any
import json

# pylint: disable=protected-access

def weigh_search(search_vector: Optional[str], rankings: str, default: float) -> float:
    """ Custom weight function for search results.
    """
    if search_vector is not None:
        svec = [int(x) for x in search_vector.split(',')]
        for rank in json.loads(rankings):
            if all(r in svec for r in rank[1]):
                return cast(float, rank[0])

    return default


class ArrayIntersectFuzzy:
    """ Compute the array of common elements of all input integer arrays.
        Very large input parameters may be ignored to speed up
        computation. Therefore, the result is a superset of common elements.

        Input and output arrays are given as comma-separated lists.
    """
    def __init__(self) -> None:
        self.first = ''
        self.values: Optional[Set[int]] = None

    def step(self, value: Optional[str]) -> None:
        """ Add the next array to the intersection.
        """
        if value is not None:
            if not self.first:
                self.first = value
            elif len(value) < 10000000:
                if self.values is None:
                    self.values = {int(x) for x in self.first.split(',')}
                self.values.intersection_update((int(x) for x in value.split(',')))

    def finalize(self) -> str:
        """ Return the final result.
        """
        if self.values is not None:
            return ','.join(map(str, self.values))

        return self.first


class ArrayUnion:
    """ Compute the set of all elements of the input integer arrays.

        Input and output arrays are given as strings of comma-separated lists.
    """
    def __init__(self) -> None:
        self.values: Optional[Set[str]] = None

    def step(self, value: Optional[str]) -> None:
        """ Add the next array to the union.
        """
        if value is not None:
            if self.values is None:
                self.values = set(value.split(','))
            else:
                self.values.update(value.split(','))

    def finalize(self) -> str:
        """ Return the final result.
        """
        return '' if self.values is None else ','.join(self.values)


def array_contains(container: Optional[str], containee: Optional[str]) -> Optional[bool]:
    """ Is the array 'containee' completely contained in array 'container'.
    """
    if container is None or containee is None:
        return None

    vset = container.split(',')
    return all(v in vset for v in containee.split(','))


def array_pair_contains(container1: Optional[str], container2: Optional[str],
                        containee: Optional[str]) -> Optional[bool]:
    """ Is the array 'containee' completely contained in the union of
        array 'container1' and array 'container2'.
    """
    if container1 is None or container2 is None or containee is None:
        return None

    vset = container1.split(',') + container2.split(',')
    return all(v in vset for v in containee.split(','))


def install_custom_functions(conn: Any) -> None:
    """ Install helper functions for Nominatim into the given SQLite
        database connection.
    """
    conn.create_function('weigh_search', 3, weigh_search, deterministic=True)
    conn.create_function('array_contains', 2, array_contains, deterministic=True)
    conn.create_function('array_pair_contains', 3, array_pair_contains, deterministic=True)
    _create_aggregate(conn, 'array_intersect_fuzzy', 1, ArrayIntersectFuzzy)
    _create_aggregate(conn, 'array_union', 1, ArrayUnion)


async def _make_aggregate(aioconn: Any, *args: Any) -> None:
    await aioconn._execute(aioconn._conn.create_aggregate, *args)


def _create_aggregate(conn: Any, name: str, nargs: int, aggregate: Any) -> None:
    try:
        conn.await_(_make_aggregate(conn._connection, name, nargs, aggregate))
    except Exception as error: # pylint: disable=broad-exception-caught
        conn._handle_exception(error)

# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for intersection query parsing and parser-only search wiring.
"""
import pytest

from nominatim_api.search.intersection_parser import parse_intersection_query
from nominatim_api.search.geocoder import ForwardGeocoder, POC_INTERSECTION_PENALTY
from nominatim_api.search.db_searches.base import AbstractSearch
from nominatim_api.search.db_searches import IntersectionSearch
from nominatim_api.search.query import Phrase, QueryStruct, PHRASE_ANY, PHRASE_STREET, BREAK_END
from nominatim_api.types import SearchDetails, Point
from nominatim_api.results import SearchResult, SourceTable, SearchResults
from nominatim_api.timeout import Timeout


class _DummyAnalyzer:
    async def analyze_query(self, phrases):
        return QueryStruct(phrases)

    def normalize_text(self, text):
        return text


class _DummyAnalyzerOneSlot:
    async def analyze_query(self, phrases):
        query = QueryStruct(phrases)
        query.add_node(BREAK_END, PHRASE_ANY)
        return query

    def normalize_text(self, text):
        return text


class _FixedSearch(AbstractSearch):
    def __init__(self, penalty, results):
        super().__init__(penalty)
        self._results = results

    async def lookup(self, conn, details):
        del conn, details
        return self._results


@pytest.mark.parametrize(
    "phrases, street_a, street_b, context",
    [
        ([Phrase(PHRASE_ANY, "Main St and First Ave")], "Main St", "First Ave", []),
        ([Phrase(PHRASE_ANY, "Main St AND First Ave")], "Main St", "First Ave", []),
        ([Phrase(PHRASE_ANY, "Main St & First Ave")], "Main St", "First Ave", []),
        ([Phrase(PHRASE_ANY, "I-465 and I-69")], "I-465", "I-69", []),
        ([Phrase(PHRASE_ANY, "I-465 & I-69")], "I-465", "I-69", []),
        ([Phrase(PHRASE_ANY, "Main St and First Ave"),
          Phrase(PHRASE_ANY, "Boston")], "Main St", "First Ave", ["Boston"]),
        ([Phrase(PHRASE_ANY, "I 465 and I 69"),
          Phrase(PHRASE_ANY, "Indianapolis")], "I 465", "I 69", ["Indianapolis"]),
    ],
)
def test_parse_intersection_query_detects_basic_patterns(phrases, street_a, street_b, context):
    parsed = parse_intersection_query(phrases)

    assert parsed is not None
    assert parsed.street_a == street_a
    assert parsed.street_b == street_b
    assert parsed.context == context


@pytest.mark.parametrize(
    "phrases",
    [
        [Phrase(PHRASE_ANY, "Main St First Ave")],
        [Phrase(PHRASE_ANY, "Main St and First Ave and Third Ave")],
        [Phrase(PHRASE_ANY, "Main St and")],
    ],
)
def test_parse_intersection_query_rejects_ambiguous_or_invalid(phrases):
    assert parse_intersection_query(phrases) is None


def test_parse_intersection_query_rejects_structured_phrases():
    phrases = [Phrase(PHRASE_STREET, "Main St and First Ave")]
    assert parse_intersection_query(phrases) is None


@pytest.mark.parametrize("phrase", [
    "Calle A con Calle B",
    "Strasse A und Strasse B",
    "Rue A et Rue B",
])
def test_parse_intersection_query_remains_narrow_for_pr1(phrase):
    assert parse_intersection_query([Phrase(PHRASE_ANY, phrase)]) is None


@pytest.mark.asyncio
async def test_geocoder_build_searches_adds_intersection_search():
    geocoder = ForwardGeocoder(None, SearchDetails(), Timeout(10))  # type: ignore[arg-type]
    geocoder.query_analyzer = _DummyAnalyzer()

    phrases = [Phrase(PHRASE_ANY, "Main St and First Ave"),
               Phrase(PHRASE_ANY, "Boston")]
    _, searches = await geocoder.build_searches(phrases)

    assert len(searches) == 1
    assert isinstance(searches[0], IntersectionSearch)
    assert searches[0].street_a == "Main St"
    assert searches[0].street_b == "First Ave"
    assert searches[0].context == ["Boston"]


@pytest.mark.asyncio
async def test_geocoder_build_searches_no_intersection_for_plain_query():
    geocoder = ForwardGeocoder(None, SearchDetails(), Timeout(10))  # type: ignore[arg-type]
    geocoder.query_analyzer = _DummyAnalyzer()

    phrases = [Phrase(PHRASE_ANY, "Main Street Boston")]
    _, searches = await geocoder.build_searches(phrases)

    assert not any(isinstance(search, IntersectionSearch) for search in searches)


@pytest.mark.asyncio
async def test_geocoder_build_searches_keeps_regular_searches(monkeypatch):
    geocoder = ForwardGeocoder(None, SearchDetails(), Timeout(10))  # type: ignore[arg-type]
    geocoder.query_analyzer = _DummyAnalyzerOneSlot()

    class _RegularSearch(AbstractSearch):
        def __init__(self):
            super().__init__(2.0)

        async def lookup(self, conn, details):
            del conn, details
            return SearchResults()

    class _FakeBuilder:
        def __init__(self, query, details):
            del query, details

        def build(self, assignment):
            del assignment
            return [_RegularSearch()]

    monkeypatch.setattr("nominatim_api.search.geocoder.SearchBuilder", _FakeBuilder)
    monkeypatch.setattr("nominatim_api.search.geocoder.yield_token_assignments",
                        lambda query: [object()])

    phrases = [Phrase(PHRASE_ANY, "Main St and First Ave")]
    _, searches = await geocoder.build_searches(phrases)

    assert len(searches) == 2
    assert searches[0].penalty == 2.0
    assert isinstance(searches[1], IntersectionSearch)
    assert searches[1].penalty == POC_INTERSECTION_PENALTY


@pytest.mark.asyncio
async def test_execute_searches_falls_back_after_empty_intersection():
    geocoder = ForwardGeocoder(None, SearchDetails(), Timeout(10))  # type: ignore[arg-type]

    query = QueryStruct([Phrase(PHRASE_ANY, "Main St and First Ave")])
    query.add_node(BREAK_END, PHRASE_ANY)

    expected = SearchResult(source_table=SourceTable.PLACEX,
                            category=("highway", "residential"),
                            centroid=Point(1.0, 2.0),
                            place_id=42,
                            accuracy=0.2)

    searches = [
        _FixedSearch(2.0, SearchResults([expected])),
        IntersectionSearch(POC_INTERSECTION_PENALTY, "Main St", "First Ave", []),
    ]

    results = await geocoder.execute_searches(query, searches)

    assert len(results) == 1
    assert results[0].place_id == 42


@pytest.mark.asyncio
async def test_intersection_search_lookup_is_noop_in_pr1():
    search = IntersectionSearch(0.0, "Main St", "First Ave", [])
    results = await search.lookup(None, SearchDetails())  # type: ignore[arg-type]
    assert results == []

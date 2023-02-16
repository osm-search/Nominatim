# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Output formatters for API version v1.
"""
from typing import Mapping, Any
import collections

import nominatim.api as napi
from nominatim.api.result_formatting import FormatDispatcher
from nominatim.api.v1.classtypes import ICONS
from nominatim.utils.json_writer import JsonWriter

dispatch = FormatDispatcher()

@dispatch.format_func(napi.StatusResult, 'text')
def _format_status_text(result: napi.StatusResult, _: Mapping[str, Any]) -> str:
    if result.status:
        return f"ERROR: {result.message}"

    return 'OK'


@dispatch.format_func(napi.StatusResult, 'json')
def _format_status_json(result: napi.StatusResult, _: Mapping[str, Any]) -> str:
    out = JsonWriter()

    out.start_object()\
         .keyval('status', result.status)\
         .keyval('message', result.message)\
         .keyval_not_none('data_updated', result.data_updated,
                          lambda v: v.isoformat())\
         .keyval('software_version', str(result.software_version))\
         .keyval_not_none('database_version', result.database_version, str)\
       .end_object()

    return out()


def _add_address_row(writer: JsonWriter, row: napi.AddressLine,
                     locales: napi.Locales) -> None:
    writer.start_object()\
            .keyval('localname', locales.display_name(row.names))\
            .keyval_not_none('place_id', row.place_id)

    if row.osm_object is not None:
        writer.keyval('osm_id', row.osm_object[1])\
              .keyval('osm_type', row.osm_object[0])

    if row.extratags:
        writer.keyval_not_none('place_type', row.extratags.get('place_type'))

    writer.keyval('class', row.category[0])\
          .keyval('type', row.category[1])\
          .keyval_not_none('admin_level', row.admin_level)\
          .keyval('rank_address', row.rank_address)\
          .keyval('distance', row.distance)\
          .keyval('isaddress', row.isaddress)\
        .end_object()


def _add_address_rows(writer: JsonWriter, section: str, rows: napi.AddressLines,
                      locales: napi.Locales) -> None:
    writer.key(section).start_array()
    for row in rows:
        _add_address_row(writer, row, locales)
        writer.next()
    writer.end_array().next()


def _add_parent_rows_grouped(writer: JsonWriter, rows: napi.AddressLines,
                             locales: napi.Locales) -> None:
    # group by category type
    data = collections.defaultdict(list)
    for row in rows:
        sub = JsonWriter()
        _add_address_row(sub, row, locales)
        data[row.category[1]].append(sub())

    writer.key('hierarchy').start_object()
    for group, grouped in data.items():
        writer.key(group).start_array()
        grouped.sort() # sorts alphabetically by local name
        for line in grouped:
            writer.raw(line).next()
        writer.end_array().next()

    writer.end_object().next()


@dispatch.format_func(napi.SearchResult, 'details-json')
def _format_search_json(result: napi.SearchResult, options: Mapping[str, Any]) -> str:
    locales = options.get('locales', napi.Locales())
    geom = result.geometry.get('geojson')
    centroid = result.centroid.to_geojson()

    out = JsonWriter()
    out.start_object()\
         .keyval_not_none('place_id', result.place_id)\
         .keyval_not_none('parent_place_id', result.parent_place_id)

    if result.osm_object is not None:
        out.keyval('osm_type', result.osm_object[0])\
           .keyval('osm_id', result.osm_object[1])

    out.keyval('category', result.category[0])\
         .keyval('type', result.category[1])\
         .keyval('admin_level', result.admin_level)\
         .keyval('localname', locales.display_name(result.names))\
         .keyval_not_none('names', result.names or None)\
         .keyval_not_none('addresstags', result.address or None)\
         .keyval_not_none('housenumber', result.housenumber)\
         .keyval_not_none('calculated_postcode', result.postcode)\
         .keyval_not_none('country_code', result.country_code)\
         .keyval_not_none('indexed_date', result.indexed_date, lambda v: v.isoformat())\
         .keyval_not_none('importance', result.importance)\
         .keyval('calculated_importance', result.calculated_importance())\
         .keyval_not_none('extratags', result.extratags or None)\
         .keyval_not_none('calculated_wikipedia', result.wikipedia)\
         .keyval('rank_address', result.rank_address)\
         .keyval('rank_search', result.rank_search)\
         .keyval('isarea', 'Polygon' in (geom or result.geometry.get('type') or ''))\
         .key('centroid').raw(centroid).next()\
         .key('geometry').raw(geom or centroid).next()

    if options.get('icon_base_url', None):
        icon = ICONS.get(result.category)
        if icon:
            out.keyval('icon', f"{options['icon_base_url']}/{icon}.p.20.png")

    if result.address_rows is not None:
        _add_address_rows(out, 'address', result.address_rows, locales)

    if result.linked_rows is not None:
        _add_address_rows(out, 'linked_places', result.linked_rows, locales)

    if result.name_keywords is not None or result.address_keywords is not None:
        out.key('keywords').start_object()

        for sec, klist in (('name', result.name_keywords), ('address', result.address_keywords)):
            out.key(sec).start_array()
            for word in (klist or []):
                out.start_object()\
                     .keyval('id', word.word_id)\
                     .keyval('token', word.word_token)\
                   .end_object().next()
            out.end_array().next()

        out.end_object().next()

    if result.parented_rows is not None:
        if options.get('group_hierarchy', False):
            _add_parent_rows_grouped(out, result.parented_rows, locales)
        else:
            _add_address_rows(out, 'hierarchy', result.parented_rows, locales)

    out.end_object()

    return out()

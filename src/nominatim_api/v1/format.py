# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Output formatters for API version v1.
"""
from typing import List, Dict, Mapping, Any
import collections
import datetime as dt

from ..utils.json_writer import JsonWriter
from ..status import StatusResult
from ..results import DetailedResult, ReverseResults, SearchResults, \
                      AddressLines, AddressLine
from ..localization import Locales
from ..result_formatting import FormatDispatcher
from .classtypes import ICONS
from . import format_json, format_xml
from .. import logging as loglib
from ..server import content_types as ct


class RawDataList(List[Dict[str, Any]]):
    """ Data type for formatting raw data lists 'as is' in json.
    """


dispatch = FormatDispatcher({'text': ct.CONTENT_TEXT,
                             'xml': ct.CONTENT_XML,
                             'debug': ct.CONTENT_HTML})


@dispatch.error_format_func
def _format_error(content_type: str, msg: str, status: int) -> str:
    if content_type == ct.CONTENT_XML:
        return f"""<?xml version="1.0" encoding="UTF-8" ?>
                   <error>
                     <code>{status}</code>
                     <message>{msg}</message>
                   </error>
                """

    if content_type == ct.CONTENT_JSON:
        return f"""{{"error":{{"code":{status},"message":"{msg}"}}}}"""

    if content_type == ct.CONTENT_HTML:
        loglib.log().section('Execution error')
        loglib.log().var_dump('Status', status)
        loglib.log().var_dump('Message', msg)
        return loglib.get_and_disable()

    return f"ERROR {status}: {msg}"


@dispatch.format_func(StatusResult, 'text')
def _format_status_text(result: StatusResult, _: Mapping[str, Any]) -> str:
    if result.status:
        return f"ERROR: {result.message}"

    return 'OK'


@dispatch.format_func(StatusResult, 'json')
def _format_status_json(result: StatusResult, _: Mapping[str, Any]) -> str:
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


def _add_address_row(writer: JsonWriter, row: AddressLine,
                     locales: Locales) -> None:
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


def _add_address_rows(writer: JsonWriter, section: str, rows: AddressLines,
                      locales: Locales) -> None:
    writer.key(section).start_array()
    for row in rows:
        _add_address_row(writer, row, locales)
        writer.next()
    writer.end_array().next()


def _add_parent_rows_grouped(writer: JsonWriter, rows: AddressLines,
                             locales: Locales) -> None:
    # group by category type
    data = collections.defaultdict(list)
    for row in rows:
        sub = JsonWriter()
        _add_address_row(sub, row, locales)
        data[row.category[1]].append(sub())

    writer.key('hierarchy').start_object()
    for group, grouped in data.items():
        writer.key(group).start_array()
        grouped.sort()  # sorts alphabetically by local name
        for line in grouped:
            writer.raw(line).next()
        writer.end_array().next()

    writer.end_object().next()


@dispatch.format_func(DetailedResult, 'json')
def _format_details_json(result: DetailedResult, options: Mapping[str, Any]) -> str:
    locales = options.get('locales', Locales())
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
       .keyval('localname', result.locale_name or '')\
       .keyval('names', result.names or {})\
       .keyval('addresstags', result.address or {})\
       .keyval_not_none('housenumber', result.housenumber)\
       .keyval_not_none('calculated_postcode', result.postcode)\
       .keyval_not_none('country_code', result.country_code)\
       .keyval_not_none('indexed_date', result.indexed_date, lambda v: v.isoformat())\
       .keyval_not_none('importance', result.importance)\
       .keyval('calculated_importance', result.calculated_importance())\
       .keyval('extratags', result.extratags or {})\
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

    if result.linked_rows:
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


@dispatch.format_func(ReverseResults, 'xml')
def _format_reverse_xml(results: ReverseResults, options: Mapping[str, Any]) -> str:
    return format_xml.format_base_xml(results,
                                      options, True, 'reversegeocode',
                                      {'querystring': options.get('query', '')})


@dispatch.format_func(ReverseResults, 'geojson')
def _format_reverse_geojson(results: ReverseResults,
                            options: Mapping[str, Any]) -> str:
    return format_json.format_base_geojson(results, options, True)


@dispatch.format_func(ReverseResults, 'geocodejson')
def _format_reverse_geocodejson(results: ReverseResults,
                                options: Mapping[str, Any]) -> str:
    return format_json.format_base_geocodejson(results, options, True)


@dispatch.format_func(ReverseResults, 'json')
def _format_reverse_json(results: ReverseResults,
                         options: Mapping[str, Any]) -> str:
    return format_json.format_base_json(results, options, True,
                                        class_label='class')


@dispatch.format_func(ReverseResults, 'jsonv2')
def _format_reverse_jsonv2(results: ReverseResults,
                           options: Mapping[str, Any]) -> str:
    return format_json.format_base_json(results, options, True,
                                        class_label='category')


@dispatch.format_func(SearchResults, 'xml')
def _format_search_xml(results: SearchResults, options: Mapping[str, Any]) -> str:
    extra = {'querystring': options.get('query', '')}
    for attr in ('more_url', 'exclude_place_ids', 'viewbox'):
        if options.get(attr):
            extra[attr] = options[attr]
    return format_xml.format_base_xml(results, options, False, 'searchresults',
                                      extra)


@dispatch.format_func(SearchResults, 'geojson')
def _format_search_geojson(results: SearchResults,
                           options: Mapping[str, Any]) -> str:
    return format_json.format_base_geojson(results, options, False)


@dispatch.format_func(SearchResults, 'geocodejson')
def _format_search_geocodejson(results: SearchResults,
                               options: Mapping[str, Any]) -> str:
    return format_json.format_base_geocodejson(results, options, False)


@dispatch.format_func(SearchResults, 'json')
def _format_search_json(results: SearchResults,
                        options: Mapping[str, Any]) -> str:
    return format_json.format_base_json(results, options, False,
                                        class_label='class')


@dispatch.format_func(SearchResults, 'jsonv2')
def _format_search_jsonv2(results: SearchResults,
                          options: Mapping[str, Any]) -> str:
    return format_json.format_base_json(results, options, False,
                                        class_label='category')


@dispatch.format_func(RawDataList, 'json')
def _format_raw_data_json(results: RawDataList,  _: Mapping[str, Any]) -> str:
    out = JsonWriter()
    out.start_array()
    for res in results:
        out.start_object()
        for k, v in res.items():
            if isinstance(v, dt.datetime):
                out.keyval(k, v.isoformat(sep=' ', timespec='seconds'))
            else:
                out.keyval(k, v)
        out.end_object().next()

    out.end_array()

    return out()

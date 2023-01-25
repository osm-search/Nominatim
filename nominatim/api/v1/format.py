# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Output formatters for API version v1.
"""
from nominatim.api.result_formatting import FormatDispatcher
from nominatim.api import StatusResult
from nominatim.utils.json_writer import JsonWriter

dispatch = FormatDispatcher()

@dispatch.format_func(StatusResult, 'text')
def _format_status_text(result: StatusResult) -> str:
    if result.status:
        return f"ERROR: {result.message}"

    return 'OK'


@dispatch.format_func(StatusResult, 'json')
def _format_status_json(result: StatusResult) -> str:
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

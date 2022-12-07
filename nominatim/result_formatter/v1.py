# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Output formatters for API version v1.
"""
from typing import Dict, Any
from collections import OrderedDict
import json

from nominatim.result_formatter.base import FormatDispatcher
from nominatim.apicmd.status import StatusResult

create = FormatDispatcher()

@create.format_func(StatusResult, 'text')
def _format_status_text(result: StatusResult) -> str:
    if result.status:
        return f"ERROR: {result.message}"

    return 'OK'


@create.format_func(StatusResult, 'json')
def _format_status_json(result: StatusResult) -> str:
    # XXX write a simple JSON serializer
    out: Dict[str, Any] = OrderedDict()
    out['status'] = result.status
    out['message'] = result.message
    if result.data_updated is not None:
        out['data_updated'] = result.data_updated.isoformat()
    out['software_version'] = result.software_version
    if result.database_version is not None:
        out['database_version'] = result.database_version

    return json.dumps(out)

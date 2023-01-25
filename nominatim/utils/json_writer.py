# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Streaming JSON encoder.
"""
from typing import Any, TypeVar, Optional, Callable
import io
try:
    import ujson as json
except ModuleNotFoundError:
    import json # type: ignore[no-redef]

T = TypeVar('T') # pylint: disable=invalid-name

class JsonWriter:
    """ JSON encoder that renders the output directly into an output
        stream. This is a very simple writer which produces JSON in a
        compact as possible form.

        The writer does not check for syntactic correctness. It is the
        responsibility of the caller to call the write functions in an
        order that produces correct JSON.

        All functions return the writer object itself so that function
        calls can be chained.
    """

    def __init__(self) -> None:
        self.data = io.StringIO()
        self.pending = ''


    def __call__(self) -> str:
        """ Return the rendered JSON content as a string.
            The writer remains usable after calling this function.
        """
        if self.pending:
            assert self.pending in (']', '}')
            self.data.write(self.pending)
            self.pending = ''
        return self.data.getvalue()


    def start_object(self) -> 'JsonWriter':
        """ Write the open bracket of a JSON object.
        """
        if self.pending:
            self.data.write(self.pending)
        self.pending = '{'
        return self


    def end_object(self) -> 'JsonWriter':
        """ Write the closing bracket of a JSON object.
        """
        assert self.pending in (',', '{', '')
        if self.pending == '{':
            self.data.write(self.pending)
        self.pending = '}'
        return self


    def start_array(self) -> 'JsonWriter':
        """ Write the opening bracket of a JSON array.
        """
        if self.pending:
            self.data.write(self.pending)
        self.pending = '['
        return self


    def end_array(self) -> 'JsonWriter':
        """ Write the closing bracket of a JSON array.
        """
        assert self.pending in (',', '[', '')
        if self.pending == '[':
            self.data.write(self.pending)
        self.pending = ']'
        return self


    def key(self, name: str) -> 'JsonWriter':
        """ Write the key string of a JSON object.
        """
        assert self.pending
        self.data.write(self.pending)
        self.data.write(json.dumps(name, ensure_ascii=False))
        self.pending = ':'
        return self


    def value(self, value: Any) -> 'JsonWriter':
        """ Write out a value as JSON. The function uses the json.dumps()
            function for encoding the JSON. Thus any value that can be
            encoded by that function is permissible here.
        """
        return self.raw(json.dumps(value, ensure_ascii=False))


    def next(self) -> 'JsonWriter':
        """ Write out a delimiter comma between JSON object or array elements.
        """
        if self.pending:
            self.data.write(self.pending)
        self.pending = ','
        return self


    def raw(self, raw_json: str) -> 'JsonWriter':
        """ Write out the given value as is. This function is useful if
            a value is already available in JSON format.
        """
        if self.pending:
            self.data.write(self.pending)
            self.pending = ''
        self.data.write(raw_json)
        return self


    def keyval(self, key: str, value: Any) -> 'JsonWriter':
        """ Write out an object element with the given key and value.
            This is a shortcut for calling 'key()', 'value()' and 'next()'.
        """
        self.key(key)
        self.value(value)
        return self.next()


    def keyval_not_none(self, key: str, value: Optional[T],
                        transform: Optional[Callable[[T], Any]] = None) -> 'JsonWriter':
        """ Write out an object element only if the value is not None.
            If 'transform' is given, it must be a function that takes the
            value type and returns a JSON encodable type. The transform
            function will be called before the value is written out.
        """
        if value is not None:
            self.key(key)
            self.value(transform(value) if transform else value)
            self.next()
        return self

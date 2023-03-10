# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for specialised logging with HTML output.
"""
from typing import Any, cast
from contextvars import ContextVar
import textwrap
import io

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

try:
    from pygments import highlight
    from pygments.lexers import PythonLexer, PostgresLexer
    from pygments.formatters import HtmlFormatter
    CODE_HIGHLIGHT = True
except ModuleNotFoundError:
    CODE_HIGHLIGHT = False


class BaseLogger:
    """ Interface for logging function.

        The base implementation does nothing. Overwrite the functions
        in derived classes which implement logging functionality.
    """
    def get_buffer(self) -> str:
        """ Return the current content of the log buffer.
        """
        return ''

    def function(self, func: str, **kwargs: Any) -> None:
        """ Start a new debug chapter for the given function and its parameters.
        """


    def section(self, heading: str) -> None:
        """ Start a new section with the given title.
        """


    def comment(self, text: str) -> None:
        """ Add a simple comment to the debug output.
        """


    def var_dump(self, heading: str, var: Any) -> None:
        """ Print the content of the variable to the debug output prefixed by
            the given heading.
        """


    def sql(self, conn: AsyncConnection, statement: 'sa.Executable') -> None:
        """ Print the SQL for the given statement.
        """


class HTMLLogger(BaseLogger):
    """ Logger that formats messages in HTML.
    """
    def __init__(self) -> None:
        self.buffer = io.StringIO()


    def get_buffer(self) -> str:
        return HTML_HEADER + self.buffer.getvalue() + HTML_FOOTER


    def function(self, func: str, **kwargs: Any) -> None:
        self._write(f"<h1>Debug output for {func}()</h1>\n<p>Parameters:<dl>")
        for name, value in kwargs.items():
            self._write(f'<dt>{name}</dt><dd>{self._python_var(value)}</dd>')
        self._write('</dl></p>')


    def section(self, heading: str) -> None:
        self._write(f"<h2>{heading}</h2>")


    def comment(self, text: str) -> None:
        self._write(f"<p>{text}</p>")


    def var_dump(self, heading: str, var: Any) -> None:
        self._write(f'<h5>{heading}</h5>{self._python_var(var)}')


    def sql(self, conn: AsyncConnection, statement: 'sa.Executable') -> None:
        sqlstr = str(cast('sa.ClauseElement', statement)
                      .compile(conn.sync_engine, compile_kwargs={"literal_binds": True}))
        if CODE_HIGHLIGHT:
            sqlstr = highlight(sqlstr, PostgresLexer(),
                               HtmlFormatter(nowrap=True, lineseparator='<br />'))
            self._write(f'<div class="highlight"><code class="lang-sql">{sqlstr}</code></div>')
        else:
            self._write(f'<code class="lang-sql">{sqlstr}</code>')


    def _python_var(self, var: Any) -> str:
        if CODE_HIGHLIGHT:
            fmt = highlight(repr(var), PythonLexer(), HtmlFormatter(nowrap=True))
            return f'<div class="highlight"><code class="lang-python">{fmt}</code></div>'

        return f'<code class="lang-python">{str(var)}</code>'


    def _write(self, text: str) -> None:
        """ Add the raw text to the debug output.
        """
        self.buffer.write(text)


class TextLogger(BaseLogger):
    """ Logger creating output suitable for the console.
    """
    def __init__(self) -> None:
        self.buffer = io.StringIO()


    def get_buffer(self) -> str:
        return self.buffer.getvalue()


    def function(self, func: str, **kwargs: Any) -> None:
        self._write(f"#### Debug output for {func}()\n\nParameters:\n")
        for name, value in kwargs.items():
            self._write(f'  {name}: {self._python_var(value)}\n')
        self._write('\n')


    def section(self, heading: str) -> None:
        self._write(f"\n# {heading}\n\n")


    def comment(self, text: str) -> None:
        self._write(f"{text}\n")


    def var_dump(self, heading: str, var: Any) -> None:
        self._write(f'{heading}:\n  {self._python_var(var)}\n\n')


    def sql(self, conn: AsyncConnection, statement: 'sa.Executable') -> None:
        sqlstr = str(cast('sa.ClauseElement', statement)
                      .compile(conn.sync_engine, compile_kwargs={"literal_binds": True}))
        sqlstr = '\n| '.join(textwrap.wrap(sqlstr, width=78))
        self._write(f"| {sqlstr}\n\n")


    def _python_var(self, var: Any) -> str:
        return str(var)


    def _write(self, text: str) -> None:
        self.buffer.write(text)


logger: ContextVar[BaseLogger] = ContextVar('logger', default=BaseLogger())


def set_log_output(fmt: str) -> None:
    """ Enable collecting debug information.
    """
    if fmt == 'html':
        logger.set(HTMLLogger())
    elif fmt == 'text':
        logger.set(TextLogger())
    else:
        logger.set(BaseLogger())


def log() -> BaseLogger:
    """ Return the logger for the current context.
    """
    return logger.get()


def get_and_disable() -> str:
    """ Return the current content of the debug buffer and disable logging.
    """
    buf = logger.get().get_buffer()
    logger.set(BaseLogger())
    return buf


HTML_HEADER: str = """<!DOCTYPE html>
<html>
<head>
  <title>Nominatim - Debug</title>
  <style>
""" + \
(HtmlFormatter(nobackground=True).get_style_defs('.highlight') if CODE_HIGHLIGHT else '') +\
"""
    h2 { font-size: x-large }

    dl {
      padding-left: 10pt;
      font-family: monospace
    }

    dt {
      float: left;
      font-weight: bold;
      margin-right: 0.5em
    }

    dt::after { content: ": "; }

    dd::after {
      clear: left;
      display: block
    }

    .lang-sql {
      color: #555;
      font-size: small
    }

    h5 {
        border: solid lightgrey 0.1pt;
        margin-bottom: 0;
        background-color: #f7f7f7
    }

    h5 + .highlight {
        padding: 3pt;
        border: solid lightgrey 0.1pt
    }
  </style>
</head>
<body>
"""

HTML_FOOTER: str = "</body></html>"

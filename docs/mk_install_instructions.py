# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
from pathlib import Path

import mkdocs_gen_files

VAGRANT_PATH = Path(__file__, '..', '..', 'vagrant').resolve()

for infile in VAGRANT_PATH.glob('Install-on-*.sh'):
    outfile = f"admin/{infile.stem}.md"
    title = infile.stem.replace('-', ' ')

    with mkdocs_gen_files.open(outfile, "w", encoding='utf-8') as outfd, infile.open(encoding='utf-8') as infd:
        print("#", title, file=outfd)
        has_empty = False
        for line in infd:
            line = line.rstrip()
            docpos = line.find('#DOCS:')
            if docpos >= 0:
                line = line[docpos + 6:]
            elif line == '#' or line.startswith('#!'):
                line = ''
            elif line.startswith('# '):
                line = line[2:]
            if line or not has_empty:
                print(line, file=outfd)
                has_empty = not bool(line)

    mkdocs_gen_files.set_edit_path(outfile, "docs/mk_install_instructions.py")

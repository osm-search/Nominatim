import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__, '..', '..', 'src').resolve()))

from nominatim_db.cli import get_set_parser

def get_parser():
    parser = get_set_parser()

    return parser.parser

import sys
from pathlib import Path

# always test against the source
sys.path.insert(0, str((Path(__file__) / '..' / '..' / '..').resolve()))


# MkDocs Documentation Setup

This project uses **MkDocs** along with additional plugins for generating and serving documentation.

---

## Requirements

The project depends on the following packages:

- mkdocs
- mkdocs-material (theme)
- mkdocstrings (for automatic documentation from Python code)
- mkdocs-gen-files (for generating files dynamically)

---

## Quick Start

Run the following commands to start the documentation server:

```bash
python -m venv venv
source venv/bin/activate      # Linux / Mac
venv\Scripts\activate         # Windows

pip install -r docs/requirements.txt
mkdocs serve
```
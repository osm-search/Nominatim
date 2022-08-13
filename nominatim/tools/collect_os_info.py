# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Collection of host system information including software versions, memory,
storage, and database configuration.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Union, cast

import psutil
from psycopg2.extensions import make_dsn, parse_dsn

from nominatim.config import Configuration
from nominatim.db.connection import connect
from nominatim.typing import DictCursorResults
from nominatim.version import version_str


def convert_version(ver_tup: Tuple[int, int]) -> str:
    """converts tuple version (ver_tup) to a string representation"""
    return ".".join(map(str, ver_tup))


def friendly_memory_string(mem: float) -> str:
    """Create a user friendly string for the amount of memory specified as mem"""
    mem_magnitude = ("bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    mag = 0
    # determine order of magnitude
    while mem > 1000:
        mem /= 1000
        mag += 1

    return f"{mem:.1f} {mem_magnitude[mag]}"


def run_command(cmd: Union[str, List[str]]) -> str:
    """Runs a command using the shell and returns the output from stdout"""
    try:
        if sys.version_info < (3, 7):
            cap_out = subprocess.run(cmd, stdout=subprocess.PIPE, check=False)
        else:
            cap_out = subprocess.run(cmd, capture_output=True, check=False)
        return cap_out.stdout.decode("utf-8")
    except FileNotFoundError:
        # non-Linux system should end up here
        return f"Unknown (unable to find the '{cmd}' command)"


def os_name_info() -> str:
    """Obtain Operating System Name (and possibly the version)"""
    os_info = None
    # man page os-release(5) details meaning of the fields
    if Path("/etc/os-release").is_file():
        os_info = from_file_find_line_portion(
            "/etc/os-release", "PRETTY_NAME", "=")
    # alternative location
    elif Path("/usr/lib/os-release").is_file():
        os_info = from_file_find_line_portion(
            "/usr/lib/os-release", "PRETTY_NAME", "="
        )

    # fallback on Python's os name
    if os_info is None or os_info == "":
        os_info = os.name

    # if the above is insufficient, take a look at neofetch's approach to OS detection
    return os_info


# Note: Intended to be used on informational files like /proc
def from_file_find_line_portion(
    filename: str, start: str, sep: str, fieldnum: int = 1
) -> Optional[str]:
    """open filename, finds the line starting with the 'start' string.
    Splits the line using seperator and returns a "fieldnum" from the split."""
    with open(filename, encoding='utf8') as file:
        result = ""
        for line in file:
            if line.startswith(start):
                result = line.split(sep)[fieldnum].strip()
        return result


def get_postgresql_config(version: int) -> str:
    """Retrieve postgres configuration file"""
    try:
        with open(f"/etc/postgresql/{version}/main/postgresql.conf", encoding='utf8') as file:
            db_config = file.read()
            file.close()
            return db_config
    except IOError:
        return f"**Could not read '/etc/postgresql/{version}/main/postgresql.conf'**"


def report_system_information(config: Configuration) -> None:
    """Generate a report about the host system including software versions, memory,
    storage, and database configuration."""

    with connect(make_dsn(config.get_libpq_dsn(), dbname='postgres')) as conn:
        postgresql_ver: str = convert_version(conn.server_version_tuple())

        with conn.cursor() as cur:
            cur.execute(f"""
            SELECT datname FROM pg_catalog.pg_database 
            WHERE datname='{parse_dsn(config.get_libpq_dsn())['dbname']}'""")
            nominatim_db_exists = cast(Optional[DictCursorResults], cur.fetchall())
            if nominatim_db_exists:
                with connect(config.get_libpq_dsn()) as conn:
                    postgis_ver: str = convert_version(conn.postgis_version_tuple())
            else:
                postgis_ver = "Unable to connect to database"

    postgresql_config: str = get_postgresql_config(int(float(postgresql_ver)))

    # Note: psutil.disk_partitions() is similar to run_command("lsblk")

    # Note: run_command("systemd-detect-virt") only works on Linux, on other OSes
    # should give a message: "Unknown (unable to find the 'systemd-detect-virt' command)"

    # Generates the Markdown report.

    report = f"""
    **Instructions**
    Use this information in your issue report at https://github.com/osm-search/Nominatim/issues
    Redirect the output to a file:
    $ ./collect_os_info.py > report.md


    **Software Environment:**
    - Python version: {sys.version}
    - Nominatim version: {version_str()} 
    - PostgreSQL version: {postgresql_ver} 
    - PostGIS version: {postgis_ver}
    - OS: {os_name_info()}
    
    
    **Hardware Configuration:**
    - RAM: {friendly_memory_string(psutil.virtual_memory().total)}
    - number of CPUs: {psutil.cpu_count(logical=False)}
    - bare metal/AWS/other cloud service (per systemd-detect-virt(1)): {run_command("systemd-detect-virt")} 
    - type and size of disks:
    **`df -h` - df - report file system disk space usage: **
    ```
    {run_command(["df", "-h"])}
    ```
    
    **lsblk - list block devices: **
    ```
    {run_command("lsblk")}
    ```
    
    
    **Postgresql Configuration:**
    ```
    {postgresql_config}
    ```
    **Notes**
    Please add any notes about anything above anything above that is incorrect.
"""
    print(report)

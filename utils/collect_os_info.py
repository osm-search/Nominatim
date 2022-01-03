
import os
from pathlib import Path
import subprocess
import sys
from typing import Optional, Union

# external requirement
import psutil

# from nominatim.version import NOMINATIM_VERSION
# from nominatim.db.connection import connect


class ReportSystemInformation:
	"""Generate a report about the host system including software versions, memory,
	   storage, and database configuration."""
	def __init__(self):
		self._memory: int = psutil.virtual_memory().total
		self.friendly_memory: str = self._friendly_memory_string(self._memory)
		# psutil.cpu_count(logical=False) returns the number of CPU cores.
		# For number of logical cores (Hypthreaded), call psutil.cpu_count() or os.cpu_count() 
		self.num_cpus: int = psutil.cpu_count(logical=False)
		self.os_info: str = self._os_name_info()

### These are commented out because they have not been tested.
#		self.nominatim_ver: str = '{0[0]}.{0[1]}.{0[2]}-{0[3]}'.format(NOMINATIM_VERSION)
#    	self._pg_version = conn.server_version_tuple()
#   	self._postgis_version = conn.postgis_version_tuple()
#		self.postgresql_ver: str = self._convert_version(self._pg_version)
#		self.postgis_ver: str = self._convert_version(self._postgis_version)

		self.nominatim_ver: str = ""
		self.postgresql_ver: str = ""
		self.postgresql_config: str = ""
		self.postgis_ver: str = ""

		# the below commands require calling the shell to gather information
		self.disk_free: str = self._run_command(["df", "-h"])
		self.lsblk: str = self._run_command("lsblk")
		# psutil.disk_partitions() <- this function is similar to the above, but it is cross platform

		# Note: `systemd-detect-virt` command only works on Linux, on other OSes
		# should give a message: "Unknown (unable to find the 'systemd-detect-virt' command)"
		self.container_vm_env: str = self._run_command("systemd-detect-virt")

	def _convert_version(self, ver_tup: tuple) -> str:
		"""converts tuple version (ver_tup) to a string representation"""
		return ".".join(map(str,ver_tup))

	def _friendly_memory_string(self, mem: int) -> str:
		"""Create a user friendly string for the amount of memory specified as mem"""
		mem_magnitude = ('bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
		mag = 0
		# determine order of magnitude
		while mem > 1000:
			mem /= 1000
			mag += 1
		
		return f"{mem:.1f} {mem_magnitude[mag]}"


	def _run_command(self, cmd: Union[str, list]) -> str:
		"""Runs a command using the shell and returns the output from stdout"""
		try:
			if sys.version_info < (3, 7):
				cap_out = subprocess.run(cmd, stdout=subprocess.PIPE)
			else:
				cap_out = subprocess.run(cmd, capture_output=True)
			return cap_out.stdout.decode("utf-8")
		except FileNotFoundError:
				# non-Linux system should end up here
				return f"Unknown (unable to find the '{cmd}' command)"


	def _os_name_info(self) -> str:
		"""Obtain Operating System Name (and possibly the version)"""

		os_info = None
		# man page os-release(5) details meaning of the fields
		if Path("/etc/os-release").is_file():
			os_info = self._from_file_find_line_portion("/etc/os-release", "PRETTY_NAME", "=")
		# alternative location 
		elif Path("/usr/lib/os-release").is_file():
			os_info = self._from_file_find_line_portion("/usr/lib/os-release", "PRETTY_NAME", "=")

		# fallback on Python's os name
		if(os_info is None or os_info == ""):
			os_info = os.name

		# if the above is insufficient, take a look at neofetch's approach to OS detection 		
		return os_info


	# Note: Intended to be used on informational files like /proc
	def _from_file_find_line_portion(self, filename: str, start: str, sep: str,
									 fieldnum: int = 1) -> Optional[str]:
		"""open filename, finds the line starting with the 'start' string.
		   Splits the line using seperator and returns a "fieldnum" from the split."""
		with open(filename) as fh:
			for line in fh:
				if line.startswith(start):
					result = line.split(sep)[fieldnum].strip()
					return result

	def report(self, out = sys.stdout, err = sys.stderr) -> None:
		"""Generates the Markdown report. 
		
		Optionally pass out or err parameters to redirect the output of stdout
		 and stderr to other file objects."""
		
		# NOTE: This should be a report format.  Any conversions or lookup has be
		#  done, do that action in the __init__() or another function. 
		message = """
Use this information in your issue report at https://github.com/osm-search/Nominatim/issues
Copy and paste or redirect the output of the file:
    $ ./collect_os_info.py > report.md
"""
		report = f"""
**Software Environment:**
- Python version: {sys.version}
- Nominatim version: {self.nominatim_ver} 
- PostgreSQL version: {self.postgresql_ver} 
- PostGIS version: {self.postgis_ver}
- OS: {self.os_info}


**Hardware Configuration:**
- RAM: {self.friendly_memory}
- number of CPUs: {self.num_cpus}
- bare metal/AWS/other cloud service (per systemd-detect-virt(1)): {self.container_vm_env} 
- type and size of disks:
**`df -h` - df - report file system disk space usage: **
```
{self.disk_free}
```

**lsblk - list block devices: **
```
{self.lsblk}
```


**Postgresql Configuration:**
```
{self.postgresql_config}
```
**Notes**
Please add any notes about anything above anything above that is incorrect.
	"""

		print(message, file = err)
		print(report, file = out)


if __name__ == "__main__":
	sys_info = ReportSystemInformation()
	sys_info.report()
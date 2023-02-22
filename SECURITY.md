# Security Policy

## Supported Versions

All Nominatim releases receive security updates for two years.

The following table lists the end of support for all currently supported
versions.

| Version | End of support for security updates |
| ------- | ----------------------------------- |
| 4.2.x   | 2024-11-24                          |
| 4.1.x   | 2024-08-05                          |
| 4.0.x   | 2023-11-02                          |
| 3.7.x   | 2023-04-05                          |

## Reporting a Vulnerability

If you believe, you have found an issue in Nominatim that has implications on
security, please send a description of the issue to **security@nominatim.org**.
You will receive an acknowledgement of your mail within 3 work days where we
also notify you of the next steps.

## How we Disclose Security Issues

** The following section only applies to security issues found in released
versions. Issues that concern the master development branch only will be
fixed immediately on the branch with the corresponding PR containing the
description of the nature and severity of the issue. **

Patches for identified security issues are applied to all affected versions and
new minor versions are released. At the same time we release a statement at
the [Nominatim blog](https://nominatim.org/blog/) describing the nature of the
incident. Announcements will also be published at the
[geocoding mailinglist](https://lists.openstreetmap.org/listinfo/geocoding).

## List of Previous Incidents

* 2020-05-04 - [SQL injection issue on /details endpoint](https://lists.openstreetmap.org/pipermail/geocoding/2020-May/002012.html)
* 2023-02-21 - [cross-site scripting vulnerability](https://nominatim.org/2023/02/21/release-421.html)

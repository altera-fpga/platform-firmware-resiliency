# Reference platforms

The platform trees in this directory were copied verbatim from the archived Intel reference repositories.

| Directory | Platform | Quartus Prime Standard Edition | Repository | Commit |
| --- | --- | --- | --- | --- |
| `wilson_city/` | Wilson City | 18.1std | [intel/pfr-wilson-city](https://github.com/intel/pfr-wilson-city) | [`886d6a297c147c2a8cba46869718cf75fd6bf39e`](https://github.com/intel/pfr-wilson-city/commit/886d6a297c147c2a8cba46869718cf75fd6bf39e) |
| `eagle_stream/` | Eagle Stream | 20.1.0 | [intel/pfr-eagle-stream](https://github.com/intel/pfr-eagle-stream) | [`99a0dd971aecb52c21c8ae1e940025103a29799b`](https://github.com/intel/pfr-eagle-stream/commit/99a0dd971aecb52c21c8ae1e940025103a29799b) |

Each design is supported only by the Quartus Prime Standard Edition release below. Open and compile it with that release. Quartus Prime Pro, and any other Standard Edition version or build, is not supported.

| Platform | Required Quartus version |
| --- | --- |
| Wilson City | `Version 18.1.1 Build 646 04/11/2019 Patches 1.01std SJ Standard Edition` |
| Eagle Stream | `Version 20.1.0 Build 711 06/05/2020 SJ Standard Edition` |

Both snapshots are the `master` branch. Eagle Stream's default branch is `main`, which does not contain this design.

Intel archived both repositories on September 29, 2025. They are read-only, and Intel no longer accepts patches. These copies were brought over unchanged so this project can keep building against the published reference designs.

Each platform directory still contains the README, license notes, and sources from that commit. See those files for the original Intel(R) Platform Firmware Resilience description and license terms.

## Preserved tools

| Directory | Tool | Version | Repository | Branch | Commit |
| --- | --- | --- | --- | --- | --- |
| `tools/intel-pfr-signing-utility/` | Intel(R) Platform Firmware Resilience Signing Utility | 1.0 | [Intel-BMC/intel-pfr-signing-utility](https://github.com/Intel-BMC/intel-pfr-signing-utility) | `master` | [`b807f6aaedf1f394b888a206ce0cdc56a3025aa4`](https://github.com/Intel-BMC/intel-pfr-signing-utility/commit/b807f6aaedf1f394b888a206ce0cdc56a3025aa4) |

Intel archived the signing utility repository on August 26, 2024. The
preserved copy is unchanged from the commit above and retains its
`COPYING.apache-2.0` license file. Its upstream build prerequisites are the
libxml2 development files and OpenSSL 1.1.1 development files.

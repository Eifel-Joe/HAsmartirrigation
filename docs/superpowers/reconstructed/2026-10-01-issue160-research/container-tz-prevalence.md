# HA Container: how often does the process time zone differ from HA's configured zone?

Retrieved 2026-10-01 (07:06-08:00 UTC). Read-only: only GET requests (gh api, curl, WebFetch, WebSearch). Nothing was posted, commented or written to any remote system. Other files in this folder pre-existed (not created by me) and were not touched.

Quote policy for this file: prose from third-party pages (docs, issues, forums) is paraphrased, with exactly one short verbatim fragment (section 4). Short config/code values are shown as data. Every row names the URL or file and line so the exact wording can be checked. "unverified" marks anything I could not confirm from a primary source.

---

## 0. Bottom line

1. **Mechanism (verified).** Core never sets the process zone. The official image has no `TZ` and ships no `/etc/localtime`. So an official-image container with no `TZ` and no mount runs at UTC, while HA's configured zone is chosen separately (onboarding, from browser/IP). HAOS and Supervised are the exception: the Supervisor injects `TZ`.
2. **Defaults.** Most distribution channels leave the process at UTC unless the operator edits something (official `docker run` placeholder, lsio example `Etc/UTC`, TrueNAS schema default `Etc/UTC`, Portainer/lsio template default `Etc/UTC`, Helm chart without `TZ`, Umbrel app with neither `TZ` nor mount). Unraid and CasaOS propagate the host zone automatically. The Proxmox helper script and several popular guides rely on a `/etc/localtime` bind mount (host zone, so wrong if the host is UTC).
3. **Measured proxy (GitHub public compose files that reference the official image, n=3,663, 2026-10-01):** 7.5 % set neither `TZ` nor a `/etc/localtime` mount, 25.3 % `TZ` only, 31.0 % mount only, 33.3 % both. Counts are approximate (section 3.3).
4. **Real mismatches are reported repeatedly** (core issues 2018-2026, newest: core#178469 in Aug 2026 and core#165037 in Mar 2026). Maintainers treat it as operator error, yet many integrations (local_calendar, alexa_devices, solaredge, xiaomi_miio/micloud, goodwe, google_sheets, KNX time expose, ...) read the process zone.
5. **HA does not warn.** The only place both zones appear side by side is the diagnostics download of the calendar integrations (`timezone` and `system_timezone`).
6. **Unverified planning estimate (my judgment, not measured):** about 5-15 % of Container installs run with a process zone different from HA's zone, which is roughly 6k-19k installs, or 0.9-2.7 % of all analytics-reporting installs (section 3.4).

---

## 1. Verified mechanism

| Fact | Evidence (retrieved 2026-10-01) |
|---|---|
| Core only sets a Python-level default zone, never the process zone | `homeassistant/core_config.py` `async_set_time_zone` (L718-724 on master) calls `dt_util.set_default_time_zone`; `homeassistant/util/dt.py` L82-93 only assigns a module global. Code search in `home-assistant/core` finds no production use of `tzset`, `tzlocal`, `get_localzone`, `/etc/localtime` or `tzname` under `homeassistant/`. Places that read the system zone via `astimezone()`: `components/onvif/device.py` L206 (camera clock sync) and three diagnostics (section 5). |
| Core itself documents that naive "now" is the system zone | `dt.py` L130-147: `naive_now()` docstring says it returns the naive system-local time; `dt_util.now()` is the configured zone. |
| Official image sets no `TZ` | Registry config blob of `ghcr.io/home-assistant/home-assistant:stable` (amd64 manifest `sha256:e47c978e1b80...`, config `sha256:cd74b0e02cee...`, created 2026-09-27T09:57:02Z, HA 2026.9.4): `Config.Env` = PATH, LANG, S6_*, PIP/UV_* only. Dockerfiles checked for `TZ`/`localtime`: `home-assistant/core` Dockerfile, `docker-base` `alpine/Dockerfile` (ENV block L139-146), `docker-base` `python/3.14/Dockerfile`: none. Image build history (35 entries, 22 layers): none mention localtime, TZ=, zoneinfo, tzdata or timezone. |
| Official image ships `tzdata` but no `/etc/localtime` | `docker-base/alpine/Dockerfile` L73 `apk add ... tzdata`; `docker-base/alpine/rootfs` contains only `etc/pip.conf`. https://pkgs.alpinelinux.org/contents?file=localtime&path=%2Fetc&branch=v3.24 returns "No matching files found" (also v3.22 main). Image layers themselves were not unpacked (unverified at file-system level). So `TZ=<zone>` works when set; unset gives UTC. |
| HAOS/Supervised get `TZ` from the Supervisor | `home-assistant/supervisor` `supervisor/docker/homeassistant.py` L194 `ENV_TIME: self.sys_timezone` (`ENV_TIME = "TZ"` in `supervisor/docker/const.py` L165). Core's `hassio` integration pushes `hass.config.time_zone` to the Supervisor on `EVENT_CORE_CONFIG_UPDATE` (`components/hassio/__init__.py` L469-491). |
| HA's configured zone is a separate input | Docs `source/_docs/configuration/basic.markdown` L9: zone chosen from IP geolocation during onboarding; frontend `src/onboarding/onboarding-core-config.ts` L41-43 starts from the browser-resolved IANA zone. Nothing reads the container's `TZ`. |
| Analytics classes | `helpers/system_info.py` L82-90: `container` = in container AND user root AND official image (`/OFFICIAL_IMAGE`, written in `.github/workflows/builder.yml` L198); every other container = `unsupported_container` (lsio runs non-root, so it lands there). |

---

## 2. Channel table

TZ default = what the process zone is if the user changes nothing. "Prompt" = does the setup UI/template/doc make the user choose a zone.

| Channel | TZ default if user does nothing | Prompts for TZ? | Source (URL, location, key value) | Popularity signal |
|---|---|---|---|---|
| Official image, `docker run` per HA docs | UTC (no `TZ`, no `/etc/localtime` in image) | Docs only: replace placeholder in `-e TZ=MY_TIME_ZONE`. Pasting the placeholder literally gives an invalid zone (core#123698). | https://www.home-assistant.io/installation/linux/ ; repo `source/_includes/installation/container.md` L24, `container/cli.md` L11 and L42. History: until 2021-07-20 (commit 86436ca1, PR #18564 by pvizeli) the example mounted `/etc/localtime` instead; rationale given there: host zone files may be in a format the container does not expect. | Analytics `container` 120,750 of 691,612 (17.46 %, fetch 07:10Z); Docker Hub `homeassistant/home-assistant` pull_count 794,115,209; GHCR page "Total downloads 195M" |
| Official docs, compose example | Until 2025-11-10: host zone via mount only (no `TZ`). Since then: `TZ: Europe/Amsterdam` plus mount. Host at UTC gives UTC. | No placeholder; example value is a real zone (Amsterdam). | `container/compose.md` L8 (`- /etc/localtime:/etc/localtime:ro`) and L15 (`TZ: Europe/Amsterdam`); TZ added by PR #41707 (commit 98e63151, 2025-11-10) after home-assistant.io#41617. Ubuntu Server installer does not ask for a zone, host defaults to UTC (https://rdr-it.com/en/ubuntu-server-configure-the-time-zone/, 2023-09-27; newer releases unverified). | See 3.3 |
| linuxserver.io image `lscr.io/linuxserver/homeassistant` | UTC. README examples use `TZ=Etc/UTC`; base image installs tzdata but sets no TZ. | Example default is UTC; user must edit. README says parameters not flagged optional are mandatory. | https://github.com/linuxserver/docker-homeassistant README L119 (`- TZ=Etc/UTC`), L137, L155 (param table); `docker-baseimage-alpine` (branch 3.24) Dockerfile L85 `tzdata`. | Docker Hub `linuxserver/homeassistant` pull_count 5,206,385; analytics: lsio counts in `unsupported_container` 4,763 (upper bound, 0.69 %); GitHub compose files naming it: 110 (docker-compose.yml), 11 with `Etc/UTC`, 7 with no TZ |
| Unraid Community Apps (lsio template; official "Home Assistant Container" template by balloob) | Unraid server zone. Dockerman appends `TZ` to every container it creates. | No, automatic. lsio template has no TZ variable (only PUID, PGID, UMASK, port, appdata, device). balloob template: no env, `BindTime=true`; repo last pushed 2023-10-02, presence in current CA unverified. | https://github.com/unraid/webgui `emhttp/plugins/dynamix.docker.manager/include/Helpers.php` L433 on master (`$Variables[] = 'TZ="'.$var['timeZone'].'"';`, also in tag 6.12.0 L254, not found in 6.10.3 by file grep). Forum https://forums.unraid.net/topic/193830-how-to-pass-server-timezone-to-docker-container/ (answers 2025-09-28: added on every add/edit). Templates: https://github.com/linuxserver/templates/blob/main/unraid/homeassistant.xml ; https://github.com/balloob/unraid-docker-templates/blob/master/balloob/home-assistant.xml | CA page https://ca.unraid.net/apps/homeassistant-0z830pg0kwl1e0: Total Downloads 5,029,870; This Month 250,852; Average per Month 179,438 (lsio template). Official template: unknown |
| Synology DSM Container Manager | UTC unless the user adds `TZ` (inferred; Synology's own doc could not be retrieved). | No; HA docs tell the user to add it by hand. | `source/_includes/installation/container/alternative.md` L18 (GUI Environment tab), L44 (`-e TZ=Australia/Melbourne`). User reports: https://www.synoforum.com/threads/docker-timezone-update.2313/ (2020, container hours behind; TZ only works if image has tzdata). | Unknown. HA Community tag `synology` 261 topics (docker 1,001), weak proxy |
| QNAP Container Station | UTC unless the user adds `TZ` (user report, https://forum.qnapclub.de/thread/44626-zeit-in-den-containern-falsch/ , 2017-07-20; vendor doc not retrieved). | No; HA docs tell the user to add it (`alternative.md` L84). | as left | Unknown (unverified) |
| TrueNAS SCALE app `home-assistant` (catalog 1.8.67, HA 2026.9.4) | Schema default `Etc/UTC`, required. Whether the wizard preselects the system zone: unverified. | Yes, a "Timezone" field in the install wizard. App is flagged deprecated in its own template notes. | https://github.com/truenas/apps `trains/stable/home-assistant/1.8.67/questions.yaml` L16-24 (`variable: TZ`, `default: Etc/UTC`, `$ref: definitions/timezone`); `templates/docker-compose.yaml` (deprecation text). Forum thread 2025-03 (24.10.2): containers show UTC, https://forums.truenas.com/t/docker-containers-are-using-utc-timezone/37088 | Unknown |
| Helm: pajikos/home-assistant-helm-chart | No `TZ` (`env: []`, commented example) so UTC | No | https://github.com/pajikos/home-assistant-helm-chart `charts/home-assistant/values.yaml` L53-56. Older k8s-at-home chart (archived 2022-08-21): `TZ: UTC`, `values.yaml` L19-21 | pajikos: 340 GitHub stars, Artifact Hub 41 stars (top "home-assistant" chart); k8s-at-home/charts 1,434 stars |
| Portainer templates | Default list `portainer/templates` `templates-2.0.json` (68 entries): no Home Assistant. Community list Lissy93/portainer-templates (800 entries): "Homeassistant" = `linuxserver/homeassistant:latest`, TZ default `Etc/UTC`. | Yes, a form field, prefilled with UTC | https://github.com/Lissy93/portainer-templates `templates.json`, entry "Homeassistant" | Lissy93 list 2,923 stars; portainer/templates 413 stars |
| CasaOS app store | Host zone: `TZ: $TZ` plus `/etc/localtime` bind (image `homeassistant/home-assistant:2026.5.4`); CasaOS fills `$TZ` with the system zone name | Automatic, editable env | https://github.com/IceWhaleTech/CasaOS-AppStore `Apps/HomeAssistant/docker-compose.yml` L7, L19-22; https://github.com/IceWhaleTech/CasaOS-AppManagement `service/compose_service.go` L206 (`timeutils.GetSystemTimeZoneName()`), `pkg/utils/envHelper/env.go` (`$TZ` mapping) | Store repo 360 stars |
| Umbrel app store | UTC always: compose has neither `TZ` nor mount (image `homeassistant/home-assistant:2026.9.4`) | No | https://github.com/getumbrel/umbrel-apps `home-assistant/docker-compose.yml` | Repo 782 stars |
| Proxmox VE Helper Scripts ("Home Assistant Container" LXC) | LXC zone via `-v /etc/localtime:/etc/localtime:ro`, no `TZ` | No | https://github.com/community-scripts/ProxmoxVE `install/homeassistant-install.sh` L44-53 | Repo 29,706 stars (whole repo, not HA-specific) |
| Popular compose guides | Mount only, no `TZ` for HA | No | https://pimylifeup.com/home-assistant-docker-compose/ (updated 2025-11-10: HA service has the mount, `TZ` only for other services); https://www.homeautomationguy.io/blog/home-assistant-tips/installing-docker-home-assistant-and-portainer-on-ubuntu-linux (2023-02-23: same). heyvaldemar guide: compose lives in a GitHub repo, not inspected (unverified). | n/a |
| (context) HAOS and Supervised | Zone from Supervisor `TZ`, follows HA setting | n/a | see section 1 | analytics `os` 551,051 (79.7 %), `supervised` 7,554 |

---

## 3. Popularity and quantification

### 3.1 HA analytics (https://analytics.home-assistant.io/data.json, `current.installation_types`)

| Fetch | active | os | container | supervised | core | unsupported_container | unknown |
|---|---|---|---|---|---|---|---|
| 2026-10-01 ~07:10Z | 691,612 | 551,067 | 120,750 | 7,556 | 6,934 | 4,763 | 542 |
| 2026-10-01 ~07:50Z | 691,602 | 551,051 | 120,761 | 7,554 | 6,933 | 4,761 | 542 |

`current.last_updated` = 2026-09-29T12:30:13Z; the history series is updated hourly, so counts drift by about 0.01 %.

- Second fetch: container 17.46 %, unsupported_container 0.69 %, together 125,522 (18.15 %). lsio is at most 3.79 % of that (4,761 / 125,522), because `unsupported_container` also holds other non-official or non-root setups.
- Container growth (history, same calendar date, rounded): about 55.7k (2024-10-01), 83.5k (2025-10-01), 120.8k (2026-10-01), i.e. share 15.1 %, 16.2 %, 17.5 %.
- Analytics is opt-in and does not collect the process zone.

### 3.2 Image pulls and other usage signals

- Docker Hub API (retrieved 2026-10-01 07:06:49Z): `homeassistant/home-assistant` pull_count 794,115,209 (stars 3,346, last_updated 2026-10-01T02:53Z); `linuxserver/homeassistant` pull_count 5,206,385 (stars 272, last_updated 2026-09-30T06:17Z). Ratio lsio / official Hub image = 0.66 %. Cumulative counts include automated pulls, so this is not an install ratio.
- HA's own docs point to GHCR (`site.installation.container` = `ghcr.io/home-assistant/home-assistant`); the package page shows "Total downloads 195M" (WebFetch, 2026-10-01). Several app stores (CasaOS, Umbrel, TrueNAS) pull the Docker Hub name, so the two counts cannot be split by channel.
- HA Community tag topic counts (tags.json, 2026-10-01): `docker` 1,001; `home-assistant-os` 1,159; `synology` 261; `supervised` 98; `proxmox` 69; `container` 59; `vm` 57; `lxc` 3. `unraid`, `truenas`, `qnap` were not in the returned list (unverified). Discussion volume only.

### 3.3 Public compose files that reference `ghcr.io/home-assistant/home-assistant`

GitHub code search (REST, `total_count`, `incomplete_results=false`), 2026-10-01. Query pattern: `"ghcr.io/home-assistant/home-assistant" [NOT] TZ [NOT] "/etc/localtime" filename:<name>`.

| filename | total | TZ only | mount only | both | neither |
|---|---|---|---|---|---|
| docker-compose.yml | 1,356 | 368 | 382 | 418 | 99 |
| docker-compose.yaml | 276 | 63 | 98 | 101 | 23 |
| compose.yaml | 543 | 115 | 177 | 206 | 42 |
| compose.yml | 1,488 | 380 | 480 | 494 | 111 |
| sum | 3,663 | 926 (25.3 %) | 1,137 (31.0 %) | 1,219 (33.3 %) | 275 (7.5 %) |

Caveats: the four categories sum to 3,557, not 3,663 (index inconsistency, about 3 %); "TZ" may be satisfied by another service in the same file; `${TZ}` from an `.env` file counts as present but cannot be resolved; public repos skew toward careful GitOps users; `docker run` users are not covered. Related counts (docker-compose.yml): `TZ=UTC` 43, `Etc/UTC` 23. lsio image, docker-compose.yml: 110 files, 11 with `Etc/UTC`, 102 without it, 7 without `TZ` (not additive, index noise).

### 3.4 Back-of-envelope (unverified, illustrative)

- Container population: 125,522 installs (both container classes, second fetch).
- Hard-UTC proxy: 7.5 % of 125,522 is about 9,400 installs (1.4 % of 691,602).
- Not measured, but real: wrong or placeholder `TZ` values (core#123698, core#124530, linuxserver#89), mount from a UTC host (31 % of compose files rely on the mount alone; Ubuntu Server installs at UTC), explicit UTC values.
- Planning range (my judgment): 5-15 % of Container installs, which is 6,276-18,828 installs or 0.9-2.7 % of all analytics-reporting installs. Core installs on a UTC host (6,933, 1.0 %) would add to this population.

---

## 4. Evidence of real mismatches

| Date | Link | Setup | One-line summary |
|---|---|---|---|
| 2026-08-07 | https://github.com/home-assistant/core/issues/178469 | Container | Ohme slot times 1 h off in BST, HA zone Europe/London. Code owner asked for the container zone (`docker exec homeassistant date`); it was UTC. Fixed by setting TZ (closed 2026-08-11). |
| 2026-03-07 | https://github.com/home-assistant/core/issues/165037 | Container, host and container UTC, HA zone Berlin | Alexa alarms shown 1 h late: Amazon sends no zone, the library takes the machine zone. Fixed after the user set the container zone (2026-04-06). Code owner chemelli74 on that day: "Setting the time zone is part of the basic installation". |
| 2024-08-12 | https://github.com/home-assistant/core/issues/123698 | Container | Xiaomi Miio login failed (micloud via tzlocal): the user had left the docs placeholder `MY_TIME_ZONE` in the container deployment. |
| 2024-08-24 | https://github.com/home-assistant/core/issues/124530 | Container | Same failure: `TZ` written with quotes in an `.env` file became an invalid zone; saving the zone in HA's General settings had no effect. Fixed by removing the quotes. |
| 2024-02-16 | https://github.com/mampfes/hacs_waste_collection_schedule/issues/1792 | Container with `/etc/localtime` mount only | Popular HACS integration: `daysTo` flipped at UTC midnight (`datetime.now()`); adding the `TZ` variable fixed it (2024-02-17). Shows the mount alone was not enough for this user (cause unverified). |
| 2023-11-20 | https://github.com/home-assistant/core/issues/104262 | Container | Local Calendar recurring events misfired: reporter's container UTC, HA at UTC-5. Code owner: the library fell back to the container zone. Fixed by setting `TZ`. |
| 2023-10-17 | https://github.com/home-assistant/core/issues/102147 (earlier: #86905, 2023-01-29) | Container | SolarEdge energy data offset: the integration used the container zone (UTC). User fixed it with `TZ`, asked for the integration to follow HA's zone; closed not_planned 2024-02-27. |
| 2023-11-13 | https://github.com/linuxserver/docker-homeassistant/issues/89 | lsio container | Reporter wrote `TZ=Berlin/Europe` (reversed), container and logs ran at UTC; maintainer pointed to the typo. |
| 2020-11-20 | https://github.com/home-assistant/core/issues/43412 | Supervised/Container (32-bit ARM) | `datetime.now()` returned UTC although `TZ` was set. HA's founder (balloob) stated that `datetime.now()` follows the system zone, not HA's setting. A maintainer (pvizeli) linked it to an Alpine tzdata problem (alpinelinux/docker-alpine#117); the reporter concluded it hit 32-bit installs only and confirmed it working again on 2020-11-24. |
| 2018-12-07 | https://github.com/home-assistant/core/issues/19082 | Docker | radiotherm set the thermostat clock to UTC; a commenter (2019-05) said it affects all components using `datetime.now()` in Docker. Closed 2019-08-20 after a stale-bot warning; a later comment (2019-08-27) says it was still an issue. |
| 2025-11-05 | https://github.com/home-assistant/home-assistant.io/issues/41617 -> PR #41707 (merged 2025-11-10) | Container, compose | Official compose example had no `TZ`; a user hit `ValueError: Invalid TZif file` from `tzlocal.get_localzone()`. Docs fixed. |
| 2024-01-20 | https://github.com/home-assistant/home-assistant.io/issues/30944 | docs | Request to add `TZ` to the compose example; maintainer frenck replied it is not needed because HA handles time zones itself; closed. Shows the project's own guidance was inconsistent until Nov 2025. |
| 2026-08-24/25 | https://github.com/home-assistant/core/pull/180047 (goodwe), https://github.com/home-assistant/core/pull/180214 (google_sheets) | contributor claim | Both merged. PR text: a container started without TZ writes UTC while HA is configured elsewhere; goodwe PR calls "a container on UTC" the common case (assertion, not data). Part of epic home-assistant/epics#117 (opened 2026-07-31) and pylint rule C7427 `home-assistant-enforce-naive-now` (PR #174053, merged 2026-06-17 per the commit log). |
| 2020-04-29 | https://community.home-assistant.io/t/different-timezone-in-docker-and-container/191126 | Docker on Synology | Container two hours behind HA's logs despite TZ/mount attempts; 10,054 views at retrieval; no resolution in thread. |
| 2024-11-03 | https://community.home-assistant.io/t/knx-time-always-gmt-on-devices/790089 | Docker on NAS | KNX time shown wrong; maintainer said the expose uses the system time and pointed to the container-zone thread; no confirmed resolution. KNX docs state the system zone is used (`source/_integrations/knx.markdown` L1342). |

Not a mismatch, checked and excluded: core#153283 (calendar DST in NZ). The maintainer's first triage question was "does the container `TZ` differ from HA's zone", the reporter's matched, and the real cause was an ical compat-mode DST bug (2026-03-16). It shows the question is now a standard triage step. Also excluded: community t/348630 (Firefox fingerprinting) and t/276518 (browser zone), t/194434 (logbook shown in UTC while `TZ` was set; no answer in the thread), t/74113 (Node-RED add-on).

---

## 5. Does HA warn about a mismatch?

No warning or repair was found.

- No production code reads the process zone for comparison: code search for `tzset`, `tzlocal`, `get_localzone`, `/etc/localtime`, `tzname` under `homeassistant/` finds nothing relevant (see section 1).
- System information shows only the configured zone: `helpers/system_info.py` L63 `"timezone": str(hass.config.time_zone)`; the only "timezone" string in `components/homeassistant/strings.json` is that label (L346). `components/repairs/strings.json` has none.
- Frontend English strings (`src/translations/en.json`, 11 lines mention time zone): only the zone picker, onboarding and the profile option "local vs server zone"; no mismatch text.
- Only diagnostics expose both zones: `components/local_calendar/diagnostics.py`, `remote_calendar/diagnostics.py`, `google/diagnostics.py` each emit `timezone` (configured) and `system_timezone` (`dt_util.naive_now().astimezone().tzinfo`). PR #178237 (merged 2026-08-21) kept the field, stating it exists so a mismatch becomes visible in diagnostics. Introduced for local_calendar in PR #89776 (2023-03-17) to help diagnose trigger problems.
- Docs: `homeassistant.markdown` `time_zone` option and `basic.markdown` do not mention the process zone; only the container install pages mention `TZ`.

---

## 6. Uncertainties

- There is no telemetry on the process zone. Analytics counts installs only; the 5-15 % range in 3.4 is my judgment built on a compose-file proxy.
- GitHub code-search counts are approximate (about 3 % internal inconsistency), public repos only, tokenised matches, `.env` substitution invisible, `docker run`-only users missing.
- Docker Hub and GHCR numbers are cumulative, include automated pulls and cannot be split by channel. The GHCR figure comes from a page-text extraction.
- Synology and QNAP vendor documentation could not be retrieved; their defaults are inferred from HA's docs and user reports (2017, 2020).
- TrueNAS wizard prefill, Unraid behaviour for templates that define their own `TZ` (a later `-e` would win), Unraid versions before 6.12, and the current CA listing of the official template are unverified.
- The official image's file system was not unpacked; "no `/etc/localtime`" rests on Dockerfiles, image history and Alpine package contents.
- Alpine/musl zone handling has had bugs (docker-alpine#117, 2020; core#43412) and a maintainer moved the docs from the `/etc/localtime` mount to `TZ` in 2021 (PR #18564) for format reasons, yet the compose example still mounts it. Present-day reliability of the mount on musl is unverified.
- HAOS: whether a changed HA zone reaches a running Core process before the container is recreated is unverified.
- Contributor statements such as "a container on UTC is the common case" are assertions, not measurements.
- Two of the evidence items are partly unresolved in their threads (community t/191126, t/790089) and one is closed as not_planned without a code fix (core#102147); whether SolarEdge still uses the process zone today is unverified.

---

## Appendix: reproduction commands (read-only)

```bash
curl -s https://hub.docker.com/v2/repositories/homeassistant/home-assistant/    # pull_count
curl -s https://analytics.home-assistant.io/data.json                            # current.installation_types
# official image config (anonymous pull token):
curl -s "https://ghcr.io/token?service=ghcr.io&scope=repository:home-assistant/home-assistant:pull"
# then GET /v2/home-assistant/home-assistant/manifests/stable (OCI index), the amd64 manifest, and the config blob
gh api -X GET search/code -f q='"ghcr.io/home-assistant/home-assistant" NOT TZ NOT "/etc/localtime" filename:compose.yaml' --jq .total_count
gh api "repos/unraid/webgui/contents/emhttp/plugins/dynamix.docker.manager/include/Helpers.php?ref=master" --jq .content | base64 -d | grep -n 'TZ='
```

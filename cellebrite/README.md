# SAUCE – SIM And UFDR Content Evaluator

`sauce.py` – traffic light for importing Cellebrite UFDR files into analysis software that licenses
**per extraction** (Python 3.8+, standard library only).

For every given UFDR file, and every `*.ufdr` in a given folder, it checks integrity, the number of
extractions, SIM extractions and the content per extraction, and rates the UFDR:

| Light | GUI | Reasons |
|---|---|---|
| 🔴 RED | STOP | UFDR defective · **empty SIM extraction** (costs a license, no data) · 3 or more extractions |
| 🟡 YELLOW | CHECK | 2 extractions (separate memory card / SIM?) · SIM extraction with data · hardly any content · warnings |
| 🟢 GREEN | GO | everything else |

Definitions:

- **SIM extraction**: `SIM` or `USIM`, not touching other letters (e.g. `SIM Card`, `EXTRACTION_SIM`), in the extraction's name/type/device name.
- **Empty SIM**: no messages, contacts or calls in that extraction (ICCID/IMSI alone are no data).
- **Hardly any content**: messages, contacts, locations and calls are each below `--min-items` (default 5).
- Categories: Messages = InstantMessage, SMS, MMS, Email (incl. chat messages) · Contacts = Contact ·
  Locations = Location, Journey · Calls = Call.
- **More**: further figures from the item counts – Chats (`Chat`), Accounts (`UserAccount`), Installed
  apps (`InstalledApplication`), Web history (`VisitedPage`), WiFi networks (`WirelessNetwork`). Per UFDR;
  not part of the rating. Not available in quick mode. Constant `FACTS`.
- **Files**: number and size of the files in the UFDR per category under `files/<category>/` (e.g.
  `Image`, `Audio`, `Video`, `Document`, `Database`, `Application`), i.e. exactly Cellebrite's own file
  categorization, taken over as is (no own logic; it can include cache/system files such as `.exo` or
  `.tts`). The overview shows the total and Audio / Video (`FILE_CATS`), the details (`-s`, GUI, HTML)
  and the CSV all categories. Per UFDR, not per extraction; not part of the rating.
- **Apps**: messages (category Messages) per app with the first and last message, plus the period
  of all messages (first – last), per UFDR; not part of the rating. The app is Cellebrite's `Source`
  of the message (e.g. `WhatsApp`, `Signal Private Messenger`, `Native Messages`, `Gmail`); a chat
  message without its own Source takes that of its chat, SMS/MMS/Email without Source are listed as
  `SMS`/`MMS`/`Email`, anything else as `(unknown app)`. Times are the message `TimeStamp` in UTC;
  timestamps before 1990 (placeholders such as `0001-01-01`) or in the future are ignored, so an app can
  have messages but no period. Not available in quick mode.

- **Passwords** (optional, `-p` / GUI checkbox *Export: Passwords*): writes per UFDR
  `<ufdr>_passwords.txt` (unique passwords, one per line, UTF-8, e.g. as a wordlist) and
  `<ufdr>_passwords_context.csv` (kind, type, source, account, service, server, label, SSID, password,
  excluded, extraction, deleted state; `;` separated). Same data source as the check (DB if present,
  otherwise report.xml). Exported are Cellebrite's `Password` items of type `Default` (password
  managers, saved passwords, app PINs) and `Secret` (e.g. iOS keychain), plus WiFi passwords
  (`WirelessNetwork`); not `Key` / `Token` (account keys, OAuth / web tokens). Binary and empty values
  are skipped. Readable values that are no passwords are **excluded** from the list but kept in the
  context CSV with the reason in `excluded`: `longer than 64`, `uuid`, `hex` (32+ hex digits: hashes /
  keys; not for WiFi, where 64 hex digits are the WPA key), `json`, `xml`, `url`, `jwt`.
  These rules come from the length x shape of all values in 7 real UFDRs: saved passwords and WiFi
  keys were all <= 64 characters; the iOS keychain held thousands of UUIDs. Digits (PINs) and other
  short values stay in, so the list is a good wordlist but not a clean one. The reports (screen, CSV,
  HTML) only show the numbers, never the passwords. Not part of the rating.

- **Accounts** (optional, `-a` / GUI checkbox *Export: Accounts*): writes per UFDR `<ufdr>_accounts.csv`
  (`;` separated) with all `UserAccount` items: source (app), service, name, username, email, phone,
  user id, server, created (UTC), extraction, deleted state. Email / phone / user id come from the
  account's contact entries (several: ` | ` separated; profile pictures are not exported). Same data
  source as the check. Also accounts nested in another account (report.xml `RelatedModels`, typically the
  Android system account of an app) – database.db has them as own rows, so both sources give the same
  list (checked on a real Pixel UFDR: 92 accounts, identical). The account's password is not exported
  here. Not part of the rating.

`-p` and `-a` write next to the UFDR, or into `--export-dir DIR`; the GUI asks for the folder once.

Rules and categories are constants at the top of `sauce.py` (`MIN_ITEMS`, `CATEGORIES`,
`CONTENT_CATS`, `SIM_DATA_CATS`, `FACTS`, `FILE_CATS`) and `evaluate()`.

## Usage

```
python3 sauce.py                     # GUI
python3 sauce.py <ufdr|folder> [<ufdr|folder> ...] [-r] [-s] [-v] [-q] [-j N] [--source auto|xml|db]
                      [--min-items N] [--case NO] [--csv out.csv] [--html report.html]
                      [-p] [-a] [--export-dir DIR]

  -r, --recursive   search subfolders of given folders too
  -s, --summary     also list all item types and all file categories with counts
  -v, --verify      verify ZIP integrity: read every member and check its CRC (slow)
  -q, --quick       only count extractions and detect SIMs (seconds instead of minutes);
                    no content counts, so an empty SIM is only YELLOW and a truncated
                    report.xml is not noticed - use the full check before importing
  -j, --jobs N      check N UFDRs in parallel (default: CPU cores, max. 4; use 1 on a single HDD)
  --source          auto (default): DbData/database.db if present (much faster), otherwise report.xml
  --min-items N     threshold for "hardly any content" (default 5)
  --case NO         optional case number, shown in CSV and HTML
  --csv FILE        also write results as CSV (; separated, opens in Excel), plus FILE_apps.csv
                    (one row per UFDR and app: messages, first / last message)
  --html FILE       also write an HTML report (single file, printable)
  -p, --passwords   export passwords per UFDR (see Passwords above), next to the UFDR
  -a, --accounts    export user accounts per UFDR (see Accounts above), next to the UFDR
  --export-dir DIR  write the export files of -p / -a to DIR instead
                    (the former --passwords-dir DIR still works, = -p --export-dir DIR)
```

Exit code: 0 all green, 1 at least one yellow, 2 at least one red.

## GUI

Start without arguments (or with `--gui`): drop UFDR files and/or folders onto the window (or add
them via the buttons), press **Run**. The table shows the light, extractions, SIM, messages, contacts,
locations, calls, audio/video files and the reasons; a click on a row shows the details (per
extraction, more figures, files per category, message period, apps with first/last message, all item
types).
After a run the worst UFDR is selected. An optional **case number** can be entered; it is used in
the exports and suggested in the file name. **Save HTML report…** writes a single printable HTML file
(case number, date, settings, overview, results table, details per UFDR); **Save CSV…** exports
everything for Excel (plus `<name>_apps.csv`). With **Export: Passwords** and/or **Accounts** checked,
**Run** first asks for the folder for the export files (cancel: nothing is run); after the run,
**Open export folder** opens it in the file manager.

Uses tkinter (part of Python; on Debian/Ubuntu `apt install python3-tk`).
Drag & drop needs the optional package `tkinterdnd2` (`pip install -r requirements.txt`); it is bundled
in the executables. Without it everything else works.

## Executables

Prebuilt executables are created by the GitHub Action `.github/workflows/sauce.yml`:

- every push touching `cellebrite/` (or manual run): download from the workflow run's *Artifacts*
- tag `sauce-v*` (e.g. `git tag sauce-v1.0 && git push --tags`): GitHub release with the files

| File | Platform | |
|---|---|---|
| `sauce_gui.exe` | Windows | GUI, no console window |
| `sauce.exe` | Windows | CLI (starts the GUI without arguments) |
| `sauce` / `sauce-linux` | Linux | GUI without arguments, CLI with arguments |

Version: the workflow writes it into `VERSION` in `sauce.py` before building – tag `sauce-v1.4` gives
`v1.4`, any other build `dev-<commit>`; running from source or a local build shows `dev`. It is shown
in the GUI title and header, the HTML report (header, settings, footer), the CSV (`sauce_version`) and
by `--version`.

Local build (PyInstaller cannot cross-compile, build on the target OS):
`build_exe.bat` (Windows) or `./build_exe.sh` (Linux). Output in `dist/`.
The Linux binary needs a glibc at least as new as the build system's.

## Data sources

| Source | File | UFDR versions |
|---|---|---|
| `xml` | `report.xml` | all |
| `db`  | `DbData/database.db` (PostgreSQL `pg_dump -Fc` archive) | PA 10+ |

`auto` (default) uses the DB if present, otherwise report.xml. The DB is much faster (60 GB iPhone
UFDR: 11 s instead of 2 min). If the DB cannot be read (e.g. zstd/lz4-compressed dump), report.xml is
used with a warning.

Both are streamed directly from the ZIP, nothing is extracted to disk. Items are assigned to their
extraction via `extractionId` (XML) or `SourceExtraction` (DB). If `DbData/database.json` exists,
its `SourceExtractionIds` are compared with the extractions found (mismatch: yellow).

Counts differ slightly between the sources:

- report.xml lists many chat messages twice (in the chat and at top level); SAUCE counts each
  message id once, so the message counts of both sources match. Messages embedded in other
  messages are listed separately as `EmbeddedInstantMessage(s)` and are not counted as messages.

- XML uses Cellebrite's model names (`Contact`, `Call`), the DB its table names (`Contacts`, `Calls`).
- Apps: XML from the `Source` / `TimeStamp` fields of the messages, DB from the `Source` / `TimeStamp`
  columns of the message tables (stored without time zone, in UTC; checked against the XML of a real
  Pixel UFDR: same first/last times, counts differ only as the message counts do).
- Passwords: XML values are mostly Base64 (decoded), the DB stores them decoded; NUL bytes are
  written as `~!!~` in the DB and converted back. Checked on 7 real UFDRs: identical password lists
  from both sources (order may differ).
- Accounts: the XML count (*More*) only includes top-level `UserAccount`s, the DB count also the
  accounts nested in another one (real Pixel UFDR: 72 vs. 92). The account export contains all of
  them from both sources.
- The XML only contains what was exported into the report; the DB contains the full project
  data. Counts from the DB can therefore be higher (seen e.g. for `DeviceConnectivities`).

Encrypted UFDRs are reported as defective (not supported).

## Tests

`tests/make_test_ufdrs.py` creates synthetic test UFDRs, one per rule; the file name starts with the
expected light (`green_`, `yellow_`, `red_`):

```
python3 tests/make_test_ufdrs.py testdata              # create the test UFDRs
python3 sauce.py testdata --csv testdata/result.csv -p -a --export-dir testdata/exports   # run SAUCE
python3 tests/make_test_ufdrs.py --check testdata/result.csv
```

The GitHub Action runs the same check against the built executables.

## Logo and version

GUI header and window icon (gravy boat) and the HTML report header show the logo (`ICON_PNG`); the
executables get it too (`sauce.ico`, `pyinstaller --icon`). Same look as BASIL (`crypto/`), with its own
accent color. The HTML report (settings, footer), the `tool` column of the CSV and `--version` show
`SAUCE <version>` - no author or link, the results are neutral.

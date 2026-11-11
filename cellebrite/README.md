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
- **Audio / Video files**: number of files in the UFDR under `files/Audio/` and `files/Video/`, i.e.
  exactly Cellebrite's own file categorization, taken over as is (no own logic; it can include
  cache/system files such as `.exo` or `.tts`). Per UFDR, not per extraction; not part of the rating.

Rules and categories are constants at the top of `sauce.py` (`MIN_ITEMS`, `CATEGORIES`,
`CONTENT_CATS`, `SIM_DATA_CATS`) and `evaluate()`.

## Usage

```
python3 sauce.py                     # GUI
python3 sauce.py <ufdr|folder> [<ufdr|folder> ...] [-r] [-s] [-v] [-q] [-j N] [--source auto|xml|db]
                      [--min-items N] [--case NO] [--csv out.csv] [--html report.html]

  -r, --recursive   search subfolders of given folders too
  -s, --summary     also list all item types with counts
  -v, --verify      verify ZIP integrity: read every member and check its CRC (slow)
  -q, --quick       only count extractions and detect SIMs (seconds instead of minutes);
                    no content counts, so an empty SIM is only YELLOW and a truncated
                    report.xml is not noticed - use the full check before importing
  -j, --jobs N      check N UFDRs in parallel (default: CPU cores, max. 4; use 1 on a single HDD)
  --source          auto (default): DbData/database.db if present (much faster), otherwise report.xml
  --min-items N     threshold for "hardly any content" (default 5)
  --case NO         optional case number, shown in CSV and HTML
  --csv FILE        also write results as CSV (; separated, opens in Excel)
  --html FILE       also write an HTML report (single file, printable)
```

Exit code: 0 all green, 1 at least one yellow, 2 at least one red.

## GUI

Start without arguments (or with `--gui`): drop UFDR files and/or folders onto the window (or add
them via the buttons), press **Run**. The table shows the light, extractions, SIM, messages, contacts,
locations and the reasons; a click on a row shows the details (per extraction, all item types).
After a run the worst UFDR is selected. An optional **case number** can be entered; it is used in
the exports and suggested in the file name. **Save HTML report…** writes a single printable HTML file
(case number, date, settings, overview, results table, details per UFDR); **Save CSV…** exports
everything for Excel.

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
- The XML only contains what was exported into the report; the DB contains the full project
  data. Counts from the DB can therefore be higher (seen e.g. for `DeviceConnectivities`).

Encrypted UFDRs are reported as defective (not supported).

## Tests

`tests/make_test_ufdrs.py` creates synthetic test UFDRs, one per rule; the file name starts with the
expected light (`green_`, `yellow_`, `red_`):

```
python3 tests/make_test_ufdrs.py testdata              # create the test UFDRs
python3 sauce.py testdata --csv testdata/result.csv    # run SAUCE (or open the folder in the GUI)
python3 tests/make_test_ufdrs.py --check testdata/result.csv
```

The GitHub Action runs the same check against the built executables.

# BASIL – Blockchain Assets, Seeds, Identifiers & Ledgers

Crypto wallets, seeds and keys in mobile extractions.

`basil.py` searches full file system extractions of phones for crypto wallets, seed phrases,
private keys and addresses (Python 3.8+, standard library only). It reads the ZIPs directly,
nothing has to be unpacked or processed beforehand.

Inputs:

| Input | Examples |
|---|---|
| FFS ZIP | Cellebrite `EXTRACTION_FFS.zip` (`Dump/…`, `filesystem1/…`), GrayKey `*_files_full.zip` (`/data/…`, `/private/var/…`), Magnet and others (path prefix is detected automatically) |
| iTunes / Finder backup | folder or ZIP with `Manifest.db` (not encrypted) |
| Keychain | GrayKey `*_keychain.plist` (decrypted) |
| Extracted dump | any folder, with `-d` |

Folders are searched for `*.zip`, `*keychain*.plist` and backup folders (`-r`: subfolders too).

## Where BASIL searches (which data)

BASIL reads the archives directly (ZIP members are streamed, nothing is unpacked) and decides per file:

**1. Which part of the extraction.** The path prefix of the tool (`Dump/`, `filesystem1/`, `/` …) is
detected and removed, then only the **user data** is searched (`SCAN_ROOTS`):

| Source | Searched | Not searched |
|---|---|---|
| Android FFS | `data/data/`, `data/user/`, `data/user_de/` (app data of all apps), `data/media/` (internal storage: `Download`, `Documents`, `DCIM`, `Android/data` …) | system (`system/`, `vendor/`, `apex/`), installed APKs (`data/app/`), `data_mirror/` (copy of `data/data`); GrayKey's `data/user/0/` when the same file is in `data/data/` |
| iOS FFS | `private/var/mobile/` (app containers, app groups, `Library/SMS`, Notes, Media …) | system, app bundles (`private/var/containers/Bundle/`), `private/var/root/`, the keychain DB (encrypted) |
| iTunes / Finder backup | every file (mapped to `<domain>/<path>` via `Manifest.db`) | – (encrypted backups: not readable) |
| GrayKey keychain plist | every item of `genp` (passwords) and `inet` (internet passwords): its value `v_Data` | `keys`, `cert` |
| unknown layout / `-d` folder | every file | – |

**2. Which files.** Every file in these parts, of any app, **except**:

- media and binaries by extension (`SKIP_EXT`): images (`jpg png gif webp heic …`), video / audio
  (`mp4 mov mp3 m4a opus amr …`), code (`so dex odex oat apk jar …`), fonts, `pdf`, `zip`, map tiles
  (`mwm`), heap dumps (`hprof`), `shm`
- files whose first bytes are a media / binary header (`SKIP_MAGIC`: JPEG, PNG, GIF, RIFF, Ogg, MP3,
  ELF, DEX, ZIP, PDF, FLAC, MP4 `ftyp`) – also without extension
- files larger than `--max-size` (default 1024 MB; counted as "too large" in the summary)
- empty files

So searched are e.g. SQLite databases **with their WAL / journal files**, XML (`shared_prefs`), JSON,
plists, text files, logs, LevelDB / IndexedDB, caches, MMKV and other app files.

**3. How.** Each file is searched as **raw bytes**, in 16 MB chunks that overlap (no hit is cut at a
chunk border). Raw means: SQLite free pages and freeblocks are included, so **deleted rows** (messages,
notes) are found as long as they were not overwritten. **gzip blobs** inside a file (e.g. the note text
of Apple Notes in `ZICNOTEDATA.ZDATA`) are unpacked (up to 4 MB) and searched too. Text has to be
UTF-8 / ASCII (any case).

Besides the raw bytes:

- **Office documents** (`OFFICE_EXT`: `docx xlsx pptx` and their macro / template variants, `odt ods
  odp odg` …, `epub`) are ZIP containers: they are opened and the text of their XML files is searched
  (Word: body, headers / footers, comments, deleted text with change tracking; Excel: `sharedStrings`,
  cells; PowerPoint: slides, notes). Tags are removed first (Word splits words into runs, e.g. at a
  spell check mark), paragraphs / cells become line breaks. Old `doc` / `xls` (OLE) are searched raw.
- **Mails** (MIME): parts in **base64** / **quoted-printable** are decoded wherever they are – `.eml`,
  Apple Mail `.emlx` (`Library/Mail/`), `mbox`, raw messages in mail app databases. Text parts are
  searched, HTML parts without tags, **office attachments** as documents (above), images and other
  binary attachments not. Encoded headers (`Subject: =?UTF-8?B?…?=`) too. Up to 4 MB per part.
- **HTML** files (`html htm xhtml enex`) are searched a second time without tags: a seed with one word
  per `<div>` / `<p>` / `<br>` (HTML notes, mail bodies, Evernote exports) is not a word run in the raw
  bytes.

**Wallet apps** are detected from the paths of **all** files (also the ones not searched): Android
package (`data/data/<pkg>/`, `data/user*/<n>/<pkg>/`, `data/media/0/Android/data|media|obb/<pkg>/`), iOS
bundle id / app group (container UUID → `MCMMetadataIdentifier` of
`.com.apple.mobile_container_manager.metadata.plist`), iTunes domain (`AppDomain-<id>`), keychain
access group (`agrp`, team id removed).

## What BASIL searches for (patterns)

| Kind | Pattern | Check | `verified` |
|---|---|---|---|
| `seed` (BIP39) | 12, 15, 18, 21 or 24 words of the BIP39 English list in a row | BIP39 checksum (last 4–8 bits = SHA-256 of the entropy) | `yes` |
| `seed` (Electrum) | 12 (13) BIP39 words in a row | Electrum 2.0+ seed version: HMAC-SHA512("Seed version", words) starts with `01`, `100`, `101`, `102` | `yes` |
| `seed` (unverified) | 12–48 BIP39 words in a row, no valid checksum | – (typo, other scheme, or chance) | `no` |
| `private_key` | WIF: `5…` (51 chars), `K…` / `L…` (52) | Base58Check, version `0x80` | `yes` |
| `private_key` | `xprv` / `yprv` / `zprv` / `tprv` (111 chars) | Base58Check, BIP32 version bytes | `yes` |
| `xpub` | `xpub` / `ypub` / `zpub` / `tpub` (111 chars) | Base58Check, BIP32 version bytes | `yes` |
| `address` | BTC `1…` / `3…`, LTC `L…` / `M…`, DOGE `D…`, TRX `T…` (26–35 chars) | Base58Check, version byte of the coin | `yes` |
| `address` | `bc1…`, `ltc1…`, `tb1…` | bech32 / bech32m checksum | `yes` |
| `address` | ETH `0x` + 40 hex | none (Keccak not in Python's standard library): pattern only | empty |
| `wallet_file` | file name (`WALLET_FILE_RE`): `wallet.dat`, `*.wallet`, `default_wallet` (Electrum), Ethereum keystore `UTC--<date>T…`, names with `mnemonic`, `seed phrase`, `recovery phrase`, `secret phrase`, `private key` | – (content may be encrypted, e.g. keystore) | – |
| `keychain` | keychain item of a wallet app (access group or service name), with its value (text, or `hex:`) | – | – |
| `wordlist` | more than 48 BIP39 words in a row: an app ships the word list (hint that it handles seeds) | – | – |
| **wallet app** | package / bundle id in `KNOWN_APPS` (48 ids: Trust Wallet, MetaMask, Coinbase (Wallet), Binance, Kraken, Exodus, Ledger Live, Trezor Suite, Electrum, BlueWallet, Phantom, Samsung Blockchain Keystore, …) → name; other ids containing a wallet word (`APP_WORDS`: `wallet`, `crypto`, `coin`, `bitcoin`, `btc`, `ledger`, `monero`, `defi`, …) → *possible* (not `com.apple.*`, `com.android.*`, Google / Samsung Pay: `APP_IGNORE`) | – | – |

Tokens are only taken whole: an address or key inside a longer Base58 / Base64 / hex string does not
count, a seed word inside a longer word neither.

**Seed rules** (against false hits from code, CSS and text, which gave thousands of hits in browser
caches and app bundles before):

- the words must be separated the way a seed is written down (`SEED_SEP`): spaces / tabs / line
  breaks, numbering (`1. `, `2) `, `3:`), list commas / semicolons, quotes (`"abandon","ability"`) –
  not `:`, `;` without space, `{`, `.`, `(`, `=` as in `top:0;right:0;bottom:0` or `case 1:return`
- at most 2 repeated words (`MAX_REPEATS`): a random seed repeats a word in 3 % (12 words) / 13 %
  (24 words) of the cases, 3 or more repeats in 0.04 % – but `case case case` or `this … this` in code
- glued words: SQLite stores the columns of a row without separator (`Wallet backupabandon ability …
  aboutthanks`); at the edges of a run, a word that ends / starts with a BIP39 word is tried as that
  word too – the checksum decides
- runs longer than the seed: windows of 24 … 12 words at the start and end of the run are checked

`verified = yes` is strong for addresses and keys (32-bit checksum), weaker for seeds: the checksum of
a 12-word seed has 4 bits (1 in 16 random word sequences passes), 24 words 8 bits. `verified = no`:
the words are in a row but no checksum matches – a seed typed or copied wrongly, from another scheme,
or chance.

## What is not found

- seeds on **screenshots / photos** or handwritten (would need OCR)
- **encrypted** wallet data (MetaMask / Trust Wallet vault, Exodus …): the app is found and its folder
  exported with `-x`; plain text only with password / PIN (e.g. hashcat modes 26600 / 26610 for MetaMask)
- the Cellebrite keychain (`extra/KeychainDump`, encrypted) and encrypted iTunes backups
- other word lists (BIP39 Spanish, Japanese …), Monero 25-word seeds, raw hex private keys (ETH, 64 hex:
  far too many false hits)
- UTF-16 text (left out for speed; SQLite, plists and JSON on phones store seeds as UTF-8 / ASCII)
- compressed data other than gzip (zlib, LZ4, zstd, Snappy in LevelDB, ZIP files inside the extraction
  other than office documents)
- **PDF** (text in compressed streams, often encoded per font), **iWork** (`pages numbers key`: IWA
  with Snappy), password protected Office documents (encrypted OLE container)
- a mail part cut at a 16 MB chunk border is only searched up to that border
- files outside the user data (see above) and larger than `--max-size`

## Usage

```
python3 basil.py                           # GUI
python3 basil.py <zip|folder|keychain.plist> [...] [-r] [-d] [-o DIR] [-x] [-j N] [--max-size MB]

  -r, --recursive   search subfolders of given folders too
  -d, --dump        given folders are extracted file systems (scanned as such)
  -o, --out DIR     output folder (default: basil_<date>_<time>)
  -x, --export      copy the files of the wallet apps and the files with seeds / keys / xpubs /
                    wallet file names to DIR/files/<label>/ (original paths), SHA-256 in basil_files.csv
  -j, --jobs N      sources in parallel (default: CPU cores, max. 4; use 1 on a single HDD)
  --max-size MB     do not scan larger files (default 1024)
```

Exit code: 0 nothing found, 1 wallet apps or findings (ETH pattern-only addresses alone do not count),
2 errors (e.g. encrypted backup, damaged ZIP).

Output (`;` separated, UTF-8 with BOM, opens in Excel):

| File | Content |
|---|---|
| `basil_summary.csv` | one row per source: platform, files scanned, counts, errors, notes |
| `basil_findings.csv` | every hit: kind, type, verified, **value**, app, path, offset, count, context |
| `basil_apps.csv` | wallet apps: id, name, match (`known` / `name`), files, size, locations |
| `basil_files.csv` | with `-x`: exported files with size and SHA-256 |

Values (seeds, keys) are only written to `basil_findings.csv`, the screen only shows counts.
`offset` is the byte offset in the file; `<ofs>+gz:<n>`: inside a gzip blob at `<ofs>`;
`<ofs>+mime:<n>` / `<ofs>+header:<n>`: in the decoded mail part / encoded header at `<ofs>`;
`word/document.xml:<n>`: in that file of an office document (`<ofs>+mime:<attachment>/…` for an
attachment); `text:<n>`: in an HTML file without tags. `<n>` in decoded / tag-free text counts in that
text, not in the file.

## GUI

Start without arguments (or with `--gui`): drop ZIPs / folders onto the window (or add them via the
buttons), choose the options, press **Run**. Every run writes its CSVs into a new
`basil_<date>_<time>` folder inside the chosen output folder (default: the folder of the first
input); **Open output folder** opens it.

The table shows one row per source, in input order:

| Result | Meaning |
|---|---|
| 🔴 SEEDS/KEYS | seed with valid checksum or private key found |
| 🟡 HINTS | wallet apps, seeds without checksum, xpubs, addresses, wallet file names or keychain items |
| 🟢 NOTHING | nothing found |
| ⚪ ERROR | source not readable (e.g. encrypted backup) |

A click on a row shows the details: **Summary** and **Findings** (every hit with its value, app,
path, offset). After a run the most relevant source is selected, a red one opens on Findings.

**Findings** are grouped by source file (**Group by file**, on by default): one row per file with what
was found in it (e.g. `2 seed ✓ · 140 address`), app and path; open it (▸ or double-click) for the
single hits with their offsets. The most important files come first. Untick it for a flat list. The
CSVs are the same either way.

**Export after the scan** (also without `-x`): select findings or file groups (Ctrl / Shift + click:
several) and press **Export selected files**, or right-click: *Export file(s) (selection)*, *Export all
files of app …* (the app / container of that finding). The files are copied like with `-x` into
`files/<label>/` of the run's output folder, with size and SHA-256 appended to `basil_files.csv`;
files already exported are skipped.

Tables: click a heading to sort (again: reverse; inside the groups too), double-click a cell to copy
its full value (seeds and paths are not shortened), right-click for a copy menu (cell, row
tab-separated, context), Ctrl+C copies the row. Findings filter: text in any column, kind, checksum ✓
only.

Uses tkinter (part of Python; on Debian/Ubuntu `apt install python3-tk`). Drag & drop needs the optional
package `tkinterdnd2` (`pip install -r requirements.txt`); without it everything else works.

## Executables

Prebuilt executables are created by the GitHub Action `.github/workflows/basil.yml`:

- every push touching `crypto/` (or manual run): download from the workflow run's *Artifacts*
- tag `basil-v*` (e.g. `git tag basil-v1.0 && git push --tags`): GitHub release "BASIL v1.0" with the files

| File | Platform | |
|---|---|---|
| `basil_gui.exe` | Windows | GUI, no console window |
| `basil.exe` | Windows | CLI (starts the GUI without arguments) |
| `basil` / `basil-linux` | Linux | GUI without arguments, CLI with arguments |

The action tests every build against the synthetic test data (see Tests) before uploading it.

Version: BASIL and SAUCE are versioned independently, each with its own tag prefix (`basil-v…`,
`sauce-v…`) and workflow; a tag only builds and releases that tool. The workflow writes the version into
`VERSION` in `basil.py` before building – tag `basil-v1.0` gives `v1.0`, any other build `dev-<commit>`;
running from source or a local build shows `dev`. It is shown in the GUI title and header, `--version`,
the first output line and the `version` / `tool` columns of `basil_summary.csv`.

Local build (PyInstaller cannot cross-compile, build on the target OS):
`build_exe.bat` (Windows) or `./build_exe.sh` (Linux). Output in `dist/`.
The Linux binary needs a glibc at least as new as the build system's.

## Tests

`tests/make_test_data.py` creates synthetic extractions (Cellebrite Android `Dump/`, GrayKey Android
`/data/` with the `data/user/0` duplicate, GrayKey iOS `/private/var/` with container metadata, a GrayKey
keychain plist) with **real, valid, randomly generated** seed phrases (BIP39 12/15/18/24 words,
Electrum) - no wallet behind them - where they turn up in cases: Google Keep, WhatsApp (also a deleted
message in a free SQLite page), SMS (numbered), Gboard clipboard, `Download/recovery phrase.txt`, JSON
backup (upper case), Apple Notes (gzip blob in `NoteStore.sqlite`), iMessage, keychain, Word (words
cut into runs), Excel (one word per cell), LibreOffice Writer, `.eml` (quoted-printable with soft line
breaks inside words, docx attachment in base64), Apple Mail `.emlx` (encoded subject, base64 text,
quoted-printable HTML), an HTML note (one word per `<div>`); plus WIF, xprv, addresses, wallet apps, an
Ethereum keystore file, a seed with a wrong checksum, and negative samples that must give no seed (CSS,
JS, English text, a word list, repeated words, a Word document with prose, a mail with an image). `--seed N` gives other
seeds, the same N the same data.

```
python3 tests/make_test_data.py testdata                 # create (expected.json = what must be found)
python3 basil.py testdata -r -o testdata/out              # scan
python3 tests/make_test_data.py --check testdata/out     # compare: OK / FAIL per finding, ALL OK
```

## Extending

`KNOWN_APPS` (package / bundle id → name), `APP_WORDS` / `APP_IGNORE`, `WALLET_FILE_RE`,
`SKIP_EXT`, `SCAN_ROOTS` at the top of the script.

## Logo and version

GUI header and window icon: basil sprig (`ICON_PNG`); `basil.ico` is the icon for executables
(`pyinstaller --icon basil.ico`). `--version`, the first output line and the `tool` column of
`basil_summary.csv` show `BASIL <version>` - no author or link, the results are neutral.

## Wishlist

- **OCR of images** (seeds on screenshots / photos): optional stage (`--ocr`) with Tesseract (external
  program, called as a subprocess; HEIC needs `pillow-heif`). Only on likely images to keep the time
  down (screenshots - `DCIM/Screenshots`, `Pictures/Screenshots`, iOS `Photos.sqlite` screenshot flag -,
  messenger images, `Download`; no thumbnails / caches / icons), ~0.5–2 s per image and core. OCR
  errors corrected against the BIP39 list (words are unique by their first 4 letters), then the
  checksum decides. Handwriting is hardly readable for Tesseract. Seed grids (2–3 numbered columns)
  have to be put back in order by their numbers / word positions (Tesseract `tsv`). First check
  whether iOS Live Text already stores recognized text in the Photos search databases (`psi.sqlite`).
- **PDF**: unpack the `FlateDecode` streams (zlib) and search them (text with font-specific encoding
  stays unreadable).
- Text disguised by its extension (e.g. a text file named `.jpg`): sniff the first bytes of
  `SKIP_EXT` files and scan them when they are text.

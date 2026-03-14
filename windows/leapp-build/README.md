# LEAPP build scripts (Windows)

Small batch scripts to update ALEAPP/iLEAPP and build Windows executables with PyInstaller.

## Included scripts

- `start_update_ALEAPP.bat`: clone or pull ALEAPP and set up/update its venv
- `start_update_iLEAPP.bat`: clone or pull iLEAPP and set up/update its venv
- `create_exe_ALEAPP.bat`: build ALEAPP CLI+GUI exe; output in `ALEAPP\dist\`
- `create_exe_iLEAPP.bat`: build iLEAPP exe; output in `iLEAPP\dist\`

## Requirements

- Windows
- Git
- Python installed and on PATH
- For the create_exe* `ALEAPP` and/or `iLEAPP` folders plus their venvs present are required
  - The update scripts will create them if missing

## Typical usage

1. Run the update script for the project you want:

```bat
start_update_ALEAPP.bat
```

or

```bat
start_update_iLEAPP.bat
```

2. Build the executable:

```bat
create_exe_ALEAPP.bat
```

or

```bat
create_exe_iLEAPP.bat
```

## Notes

- The build scripts assume the repo folders are in the same directory as these scripts.
- Output paths are hard-coded to `ALEAPP\dist\` and `iLEAPP\dist\`.

# pdn2ora

This cross-platform CLI tool converts Paint.NET (.pdn) files to OpenRaster (.ora) format, preserving all layer properties, blend modes, opacity, and visibility.  
Paint.NET's native format is proprietary; this opens up your artwork for use in Krita, GIMP, and other open-source editors.  
Supports recursive batch conversion, dry-run previews, post-conversion validation, and standalone binaries for Linux and Windows.

- **Codeberg** (main): https://codeberg.org/marvin1099/pdn2ora
- **GitHub** (mirror): https://github.com/marvin1099/pdn2ora
- **PyPI**: https://pypi.org/project/pdn2ora/

## Install

```bash
# With uv (recommended)
uv tool install pdn2ora

# Or with pipx
pipx install pdn2ora

# Or with pip
pip install --user pdn2ora
```

Or install from git:

```bash
git clone https://codeberg.org/marvin1099/pdn2ora.git
cd pdn2ora

# With uv (recommended)
uv tool install .

# Or with pipx
pipx install .

# Or with pip
pip install --user .
```

## Binary downloads
Instead of installing from source, get pre-compiled binaries from the [releases](https://codeberg.org/marvin1099/pdn2ora/releases) page,
or build binaries using

```bash
# if not cloned yet
git clone https://codeberg.org/marvin1099/pdn2ora.git
cd pdn2ora

./build.sh linux     # Linux binary → dist/pdn2ora-linux-x64
./build.sh windows   # Windows binary via Wine → dist/pdn2ora-win-x64.exe
./build.sh all       # both
```

## Development

```bash
# if not cloned yet
git clone https://codeberg.org/marvin1099/pdn2ora.git
cd pdn2ora

./build.sh setup     # install all deps
./build.sh test      # run tests
./build.sh lint      # check code style
```

## Usage

```bash
pdn2ora [options] FILE_OR_DIR [FILE_OR_DIR ...]
```

### Examples

```bash
pdn2ora input.pdn                       # single file
pdn2ora ./artwork/ -r -D ./output/      # recursive batch to output dir
pdn2ora input.pdn --info                # show layer info
pdn2ora *.pdn -d -y                     # convert and delete sources
```

### Options

| Flag | Description |
|------|-------------|
| **Output** | |
| `-o, --output PATH` | Explicit output path (single file only) |
| `-D, --output-dir DIR` | Put all ORA files into DIR |
| `-s, --suffix EXT` | Output file extension (default: .ora) |
| `-w, --overwrite` | Overwrite existing output files |
| `-t, --no-thumbnail` | Skip thumbnail generation |
| **Conversion** | |
| `-r, --recursive` | Recursively search directories |
| `-d, --delete` | Delete source .pdn after successful conversion |
| `-x, --delete-only` | Delete .pdn if .ora already exists |
| `-A, --validate` | Validate the ORA file after writing |
| **Info** | |
| `-i, --info` | Show PDN file info and exit |
| `-S, --stats` | Show file size comparison |
| **General** | |
| `-v, --verbose` | Increase verbosity (-v info, -vv debug) |
| `-y, --yes` | Skip confirmation prompts |
| `-n, --dry-run` | Show what would be done without doing it |
| `-V, --version` | Show version |
| `-h, --help` | Show help |



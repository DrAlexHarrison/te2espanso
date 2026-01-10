# te2espanso

Convert TextExpander exports to Espanso YAML format.

> **Warning:** This tool is minimally tested. Use at your own risk! Always back up your snippets before converting.

## Features

- Supports CSV exports and native `.textexpander` (plist/XML) files
- Interactive mode with per-group prefix prompts
- Handles multiline snippets, links, and lists
- Saves prefix config for easy re-runs

## Installation

```bash
# Clone the repo
git clone https://github.com/DrAlexHarrison/te2espanso.git
cd te2espanso

# Make executable (optional)
chmod +x te2espanso.py

# Or install system-wide
sudo cp te2espanso.py /usr/local/bin/te2espanso
```

Requires Python 3.6+ (no external dependencies).

## Usage

### Interactive Mode (Recommended)

```bash
te2espanso ~/TextExpander/
```

Scans for all `.csv` and `.textexpander` files, prompts for each group's prefix.

### Single File Mode

```bash
te2espanso snippets.csv output.yml --prefix "rp"
```

### Re-run with Saved Config

```bash
te2espanso ~/TextExpander/ --use-config
```

### Options

| Flag | Description |
|------|-------------|
| `--prefix PREFIX` | Prepend PREFIX to every trigger |
| `--batch` | Non-interactive batch with uniform prefix |
| `--use-config` | Re-run using saved prefixes.conf |
| `--dry-run` | Preview without writing files |

## How Prefixes Work

Prefixes prevent short triggers from firing during normal typing.

Example: If prefix is `rp` and trigger is `fyi`, the Espanso trigger becomes `rpfyi`.

## Output Location

- **Ready snippets:** `~/.config/espanso/match/te-imports/`
- **Staging (skipped):** `~/.config/espanso/te-imports-staging/`

## Support

**Note:** This is a side project. I'm the founder of [Saturday Inc](https://saturdaymorning.fit), building the app that fuels your next marathon, century ride, or Ironman. Issues and PRs welcome, but response times may vary.

## License

MIT

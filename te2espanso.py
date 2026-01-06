#!/usr/bin/env python3
"""
te2espanso.py - Convert TextExpander exports to Espanso YAML

Supports both CSV exports and native .textexpander (plist/XML) files.

Usage:
  te2espanso <input_dir>                    # Interactive mode (recommended)
  te2espanso <input> <output.yml> --prefix PREFIX  # Single file mode
  te2espanso --batch <input_dir> --prefix PREFIX   # Non-interactive batch

Interactive Mode (default for directories):
  Scans for all .csv and .textexpander files, then prompts for each group's
  prefix. Type a prefix, press ENTER for none, or type BLANK to skip.

Options:
  --prefix PREFIX   Prepend PREFIX to every trigger (single-file mode)
  --batch           Non-interactive batch with uniform prefix
  --use-config      Re-run using saved prefixes.conf (no prompts)
  --dry-run         Preview without writing files

Examples:
  # Interactive - prompts for each group's prefix
  te2espanso ~/TextExpander/

  # Re-run with saved config (no prompts)
  te2espanso ~/TextExpander/ --use-config

  # Single file with explicit prefix
  te2espanso "snippets.csv" output.yml --prefix "rp"
"""

import sys
import csv
import re
import plistlib
import json
import argparse
from pathlib import Path


csv.field_size_limit(sys.maxsize)


def needs_quoting(s: str) -> bool:
    """Check if a string needs quoting in YAML."""
    if not s:
        return False

    problematic_patterns = [
        r': ',           # colon-space
        r':\t',          # colon-tab
        r':$',           # trailing colon
        r'^\s',          # leading whitespace
        r'\s$',          # trailing whitespace
        r'^[\[\]{}&*!|>\'"%@`#,?-]',  # leading special chars
        r'^(true|false|yes|no|on|off|null|~)$',  # YAML keywords
    ]

    for pattern in problematic_patterns:
        if re.search(pattern, s, re.IGNORECASE):
            return True

    if s.count('"') % 2 != 0 or s.count("'") % 2 != 0:
        return True

    return False


def escape_yaml_string(s: str) -> str:
    """Escape a string for YAML double-quoted output."""
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    s = s.replace('\n', '\\n')
    s = s.replace('\t', '\\t')
    return s


def format_yaml_value(content: str) -> tuple[str, bool]:
    """Format content for YAML. Returns (formatted_value, is_multiline)."""
    if not content:
        return '""', False

    if '\n' in content:
        if content.endswith('\n\n'):
            indicator = '|+'
        elif content.endswith('\n'):
            indicator = '|'
        else:
            indicator = '|-'
        return indicator, True
    else:
        if needs_quoting(content):
            return f'"{escape_yaml_string(content)}"', False
        else:
            return content, False


def parse_textexpander_json(json_str: str) -> str:
    """Parse TextExpander's JSON rich text format to plain text."""
    try:
        data = json.loads(json_str)
        return parse_te_nodes(data.get('nodes', []))
    except (json.JSONDecodeError, KeyError):
        return ""


def parse_te_nodes(nodes: list) -> str:
    """Recursively parse TextExpander JSON nodes to plain text."""
    result = []

    for node in nodes:
        node_type = node.get('e', '')

        if node_type == 'tx':
            result.append(node.get('tx', ''))
        elif node_type == 'ln':
            result.append('\n')
        elif node_type == 'link':
            url = node.get('url', '')
            text = parse_te_nodes(node.get('nodes', []))
            if text and url:
                result.append(f'[{text}]({url})')
            elif url:
                result.append(url)
            else:
                result.append(text)
        elif node_type in ('numbered-list', 'bulleted-list'):
            items = node.get('list-items', [])
            for i, item in enumerate(items):
                item_text = parse_te_nodes(item.get('nodes', []))
                if node_type == 'numbered-list':
                    result.append(f'\n{i+1}. {item_text}')
                else:
                    result.append(f'\n• {item_text}')
        elif node_type == 'list-item':
            result.append(parse_te_nodes(node.get('nodes', [])))
        elif node_type == 'p':
            result.append(parse_te_nodes(node.get('nodes', [])))
            result.append('\n')
        elif node_type == 'br':
            result.append('\n')
        elif 'nodes' in node:
            result.append(parse_te_nodes(node['nodes']))

    return ''.join(result)


def parse_csv(csv_path: str) -> list:
    """Parse CSV into list of (trigger, content) tuples."""
    matches = []

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            trigger = row[0].strip().strip('"').strip("'")
            content = row[1]
            if trigger:
                matches.append((trigger, content))

    return matches


def parse_textexpander_file(te_path: str) -> tuple[list, str]:
    """Parse .textexpander file. Returns (matches, group_name)."""
    matches = []
    group_name = ""

    with open(te_path, 'rb') as f:
        try:
            plist = plistlib.load(f)
        except Exception as e:
            print(f"Error parsing plist: {e}")
            return [], ""

    group_info = plist.get('groupInfo', {})
    group_name = group_info.get('groupName', '')

    # TE3 format (newer)
    snippets = plist.get('snippetsTE3', [])
    for snippet in snippets:
        trigger = snippet.get('abbreviation', '').strip()
        if not trigger:
            continue

        content = snippet.get('plainText', '')
        extra_info = snippet.get('extraInfo', {})
        json_str = extra_info.get('jsonStr', '')

        if json_str and not content:
            content = parse_textexpander_json(json_str)

        if trigger and content:
            matches.append((trigger, content))

    # TE2 format fallback
    if not matches:
        snippets = plist.get('snippetsTE2', [])
        for snippet in snippets:
            trigger = snippet.get('abbreviation', '').strip()
            content = snippet.get('plainText', '')
            if trigger and content:
                matches.append((trigger, content))

    return matches, group_name


def write_espanso_yaml(matches: list, yml_path: str, prefix: str = "",
                       group_name: str = "", dry_run: bool = False) -> int:
    """Write matches to Espanso YAML file."""

    if dry_run:
        print(f"\n--- {yml_path} ---")
        if group_name:
            print(f"# Source: {group_name}")
        print(f"# Prefix: '{prefix}' (applied to all triggers)")
        print(f"# Sample triggers with prefix:")
        for trigger, _ in matches[:5]:
            print(f"#   {prefix}{trigger}")
        if len(matches) > 5:
            print(f"#   ... and {len(matches) - 5} more")
        return len(matches)

    with open(yml_path, 'w', encoding='utf-8') as f:
        if group_name:
            f.write(f"# Source: {group_name}\n")
        if prefix:
            f.write(f"# Prefix '{prefix}' applied to all triggers\n")
        f.write("\nmatches:\n")

        for trigger, content in matches:
            full_trigger = f"{prefix}{trigger}" if prefix else trigger

            if needs_quoting(full_trigger):
                trigger_yaml = f'"{escape_yaml_string(full_trigger)}"'
            else:
                trigger_yaml = full_trigger

            f.write(f"  - trigger: {trigger_yaml}\n")

            formatted, is_multiline = format_yaml_value(content)

            if is_multiline:
                f.write(f"    replace: {formatted}\n")
                for line in content.split('\n'):
                    if line:
                        f.write(f"      {line}\n")
                    else:
                        f.write("\n")
            else:
                f.write(f"    replace: {formatted}\n")

    return len(matches)


def convert_file(input_path: str, output_path: str, prefix: str = "",
                 dry_run: bool = False) -> int:
    """Convert a single file."""
    path = Path(input_path)
    group_name = ""

    if path.suffix.lower() == '.textexpander':
        matches, group_name = parse_textexpander_file(input_path)
    elif path.suffix.lower() == '.csv':
        matches = parse_csv(input_path)
    else:
        print(f"Unknown file type: {path.suffix}")
        return 0

    if not matches:
        print(f"No snippets found in {input_path}")
        return 0

    return write_espanso_yaml(matches, output_path, prefix, group_name, dry_run)


def discover_te_files(input_dir: str) -> list:
    """Scan directory for TE files. Returns list of (filepath, group_name, count, samples)."""
    input_path = Path(input_dir)
    discovered = []

    files = list(input_path.glob('*.textexpander')) + \
            list(input_path.glob('*.csv')) + \
            list(input_path.glob('**/*.textexpander')) + \
            list(input_path.glob('**/*.csv'))

    files = sorted(set(f for f in files if not f.name.startswith('._')))

    for f in files:
        if f.suffix.lower() == '.textexpander':
            matches, group_name = parse_textexpander_file(str(f))
            if not group_name:
                group_name = f.stem
        elif f.suffix.lower() == '.csv':
            matches = parse_csv(str(f))
            group_name = f.stem
        else:
            continue

        if matches:
            samples = [t for t, _ in matches[:5]]
            discovered.append((f, group_name, len(matches), samples))

    return discovered


def load_prefixes_config(config_path: Path) -> dict:
    """Load prefix mappings from config file."""
    prefixes = {}
    if not config_path.exists():
        return prefixes

    with open(config_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                prefixes[key.strip()] = val.strip()
    return prefixes


def save_prefixes_config(config_path: Path, prefixes: dict) -> None:
    """Save prefix mappings to config file."""
    with open(config_path, 'w') as f:
        f.write("# Auto-generated by te2espanso\n")
        f.write("# Re-run with --use-config to skip prompts\n\n")
        for filename, prefix in sorted(prefixes.items()):
            f.write(f"{filename} = {prefix}\n")


def print_intro_banner(count: int) -> None:
    """Print verbose intro explaining the interactive process."""
    print("═" * 67)
    print("TextExpander → Espanso Converter")
    print("═" * 67)
    print()
    print(f"Found {count} snippet group(s) to convert.")
    print()
    print("For each group, you'll be asked to enter a PREFIX. The prefix is")
    print("prepended to every trigger in that group.")
    print()
    print("Example: If prefix is 'rp' and trigger is 'fyi', the Espanso")
    print("         trigger becomes 'rpfyi'")
    print()
    print("OPTIONS FOR EACH PROMPT:")
    print("  • Type a prefix (e.g., rp, fyi, `, /, ..)  → Applied to all triggers")
    print("  • Press ENTER (blank)                      → No prefix, triggers unchanged")
    print("  • Type BLANK                               → Skip this group (staging folder)")
    print()
    print("═" * 67)
    print()


def prompt_for_prefix(index: int, total: int, group_name: str,
                      count: int, samples: list) -> str:
    """Prompt user for prefix. Returns prefix string or 'BLANK' to skip."""
    print(f"[{index}/{total}] Group: \"{group_name}\" ({count} snippets)")
    print(f"      Sample triggers: {', '.join(samples)}")
    try:
        response = input("      Enter prefix: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(1)
    return response


def interactive_convert(input_dir: str, dry_run: bool = False,
                        use_config: bool = False) -> None:
    """Interactive conversion with per-group prefix prompts."""
    input_path = Path(input_dir)
    output_base = Path.home() / ".config" / "espanso" / "match" / "te-imports"
    staging_base = Path.home() / ".config" / "espanso" / "te-imports-staging"
    config_path = input_path / "prefixes.conf"

    discovered = discover_te_files(input_dir)
    if not discovered:
        print(f"No .textexpander or .csv files found in {input_dir}")
        return

    saved_prefixes = load_prefixes_config(config_path) if use_config else {}
    new_prefixes = {}

    if not use_config:
        print_intro_banner(len(discovered))

    results_ready = {}
    results_staging = {}

    for i, (filepath, group_name, count, samples) in enumerate(discovered, 1):
        filename = filepath.name

        if use_config and filename in saved_prefixes:
            prefix = saved_prefixes[filename]
            print(f"[{i}/{len(discovered)}] {group_name}: using saved prefix '{prefix}'")
        else:
            prefix = prompt_for_prefix(i, len(discovered), group_name, count, samples)

        new_prefixes[filename] = prefix

        # Determine output location
        if prefix.upper() == 'BLANK':
            out_dir = staging_base
            actual_prefix = ""
            is_staging = True
        else:
            out_dir = output_base
            actual_prefix = prefix
            is_staging = False

        out_name = filepath.stem.lower().replace(' ', '-') + '.yml'
        out_file = out_dir / out_name

        if not dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)

        converted = convert_file(str(filepath), str(out_file), actual_prefix, dry_run)

        if converted > 0:
            if is_staging:
                results_staging[filename] = converted
            else:
                results_ready[filename] = converted

        print()

    # Save config
    if not dry_run and new_prefixes:
        save_prefixes_config(config_path, new_prefixes)
        print(f"Saved prefix config to {config_path}")

    # Summary
    print("\n" + "─" * 50)
    if results_ready:
        total = sum(results_ready.values())
        print(f"Ready ({output_base}):")
        for name, cnt in sorted(results_ready.items()):
            print(f"  {name}: {cnt} snippets")
        print(f"  Total: {total} snippets")

    if results_staging:
        total = sum(results_staging.values())
        print(f"\nStaging ({staging_base}):")
        for name, cnt in sorted(results_staging.items()):
            print(f"  {name}: {cnt} snippets")
        print(f"  Total: {total} snippets")


def batch_convert(input_dir: str, output_dir: str, prefix: str = "",
                  dry_run: bool = False) -> dict:
    """Convert all TE files in a directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not dry_run:
        output_path.mkdir(parents=True, exist_ok=True)

    results = {}

    # Find all convertible files
    files = list(input_path.glob('*.textexpander')) + \
            list(input_path.glob('*.csv')) + \
            list(input_path.glob('**/*.textexpander')) + \
            list(input_path.glob('**/*.csv'))

    # Dedupe and filter hidden files
    files = sorted(set(f for f in files if not f.name.startswith('._')))

    for f in files:
        out_name = f.stem.lower().replace(' ', '-') + '.yml'
        out_file = output_path / out_name

        count = convert_file(str(f), str(out_file), prefix, dry_run)
        if count > 0:
            results[f.name] = count

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Convert TextExpander exports to Espanso YAML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ~/TextExpander/                    # Interactive mode
  %(prog)s ~/TextExpander/ --use-config       # Use saved prefixes
  %(prog)s file.csv out.yml --prefix "rp"     # Single file mode
        """
    )

    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('output', nargs='?', help='Output file (single-file mode only)')
    parser.add_argument('--prefix', '-p', default='',
                        help='Prefix for all triggers (single-file/batch mode)')
    parser.add_argument('--batch', '-b', action='store_true',
                        help='Non-interactive batch with uniform prefix')
    parser.add_argument('--use-config', '-c', action='store_true',
                        help='Use saved prefixes.conf (skip prompts)')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Preview without writing files')

    args = parser.parse_args()
    input_path = Path(args.input)

    # Interactive mode: directory without --batch
    if input_path.is_dir() and not args.batch:
        interactive_convert(args.input, args.dry_run, args.use_config)
        return

    # Batch mode with uniform prefix
    if args.batch:
        if not args.output:
            print("Error: --batch requires output directory")
            sys.exit(1)
        if not args.prefix:
            print("WARNING: No prefix specified. Short triggers may fire during typing!")
            print("         Consider using --prefix or interactive mode (no --batch)")
            print()
        results = batch_convert(args.input, args.output, args.prefix, args.dry_run)
        total = sum(results.values())
        print(f"\nConverted {len(results)} files, {total} total snippets")
        for name, count in sorted(results.items()):
            print(f"  {name}: {count} snippets")
        return

    # Single-file mode
    if not args.output:
        print("Error: Single-file mode requires output file")
        print("Usage: te2espanso <input.csv> <output.yml> --prefix PREFIX")
        sys.exit(1)

    if not args.prefix:
        print("WARNING: No prefix specified. Short triggers may fire during typing!")
        print()

    count = convert_file(args.input, args.output, args.prefix, args.dry_run)
    if not args.dry_run:
        print(f"Generated {count} snippets → {args.output}")


if __name__ == "__main__":
    main()

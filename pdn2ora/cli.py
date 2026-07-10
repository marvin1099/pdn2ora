"""CLI entry point for pdn2ora."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pdn2ora import __version__
from pdn2ora.converter import convert_pdn_to_ora, read_pdn_info

logger = logging.getLogger("pdn2ora")

# Blend mode names for display
_BLEND_NAMES = {
    0: "Normal",
    1: "Multiply",
    2: "Additive",
    3: "ColorBurn",
    4: "ColorDodge",
    5: "Reflect",
    6: "Glow",
    7: "Overlay",
    8: "Difference",
    9: "Negation",
    10: "Lighten",
    11: "Darken",
    12: "Screen",
    13: "XOR",
}


def _collect_pdn_files(paths: list[Path], *, recursive: bool) -> list[Path]:
    """Gather all .pdn files from the given paths.

    If a path is a file, it is included directly (extension check optional
    when the user explicitly names it).  If a path is a directory, all
    *.pdn files inside it are collected — recursively when requested.
    """
    results: list[Path] = []
    for p in paths:
        if p.is_file():
            results.append(p)
        elif p.is_dir():
            pattern = "**/*.pdn" if recursive else "*.pdn"
            results.extend(sorted(p.glob(pattern)))
        else:
            logger.warning("Skipping (not found): %s", p)
    return results


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdn2ora",
        description="Convert Paint.NET (.pdn) files to OpenRaster (.ora).",
        epilog=(
            "Examples:\n"
            "  pdn2ora input.pdn                          single file → input.ora\n"
            "  pdn2ora input.pdn -o output.ora            explicit output path\n"
            "  pdn2ora ./schemas/ -r                      all .pdn in dir (recursive)\n"
            "  pdn2ora *.pdn -r --overwrite               batch convert, overwrite\n"
            "  pdn2ora input.pdn --delete                  convert then delete source\n"
            "  pdn2ora input.pdn --info                    show file info only\n"
            "  pdn2ora ./schemas/ -r -D ./output/          all into one output dir\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ── Positional ─────────────────────────────────────────────────
    parser.add_argument(
        "input",
        nargs="+",
        metavar="FILE_OR_DIR",
        help="PDN file(s) or directory/directories to convert",
    )

    # ── Output control ─────────────────────────────────────────────
    out_group = parser.add_argument_group("output control")
    out_group.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        default=None,
        help=("Output path (single file only).  Default: same name with .ora extension."),
    )
    out_group.add_argument(
        "-D",
        "--output-dir",
        metavar="DIR",
        default=None,
        help="Put all ORA files into DIR (preserves filenames)",
    )
    out_group.add_argument(
        "-s",
        "--suffix",
        metavar="EXT",
        default=".ora",
        help="Output file extension (default: .ora)",
    )
    out_group.add_argument(
        "-w",
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing output files",
    )
    out_group.add_argument(
        "-t",
        "--no-thumbnail",
        action="store_true",
        default=False,
        help="Skip thumbnail generation (smaller ORA files)",
    )

    # ── Conversion behaviour ───────────────────────────────────────
    conv_group = parser.add_argument_group("conversion behaviour")
    conv_group.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        default=False,
        help="Recursively search directories for .pdn files",
    )
    conv_group.add_argument(
        "-d",
        "--delete",
        action="store_true",
        default=False,
        help="Delete source .pdn after successful conversion",
    )
    conv_group.add_argument(
        "-x",
        "--delete-only",
        action="store_true",
        default=False,
        help="Delete source .pdn if an .ora already exists (skip conversion)",
    )
    conv_group.add_argument(
        "-A",
        "--validate",
        action="store_true",
        default=False,
        help="Validate the ORA file after writing",
    )

    # ── Informational ──────────────────────────────────────────────
    info_group = parser.add_argument_group("informational")
    info_group.add_argument(
        "-i",
        "--info",
        action="store_true",
        default=False,
        help="Show PDN file info (layers, dimensions, blend modes) and exit",
    )
    info_group.add_argument(
        "-S",
        "--stats",
        action="store_true",
        default=False,
        help="Show file size comparison after conversion",
    )

    # ── General ────────────────────────────────────────────────────
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v info, -vv debug)",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="Skip confirmation prompts (e.g. for --delete)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be done without doing it",
    )

    return parser


def _print_info(pdn_path: Path) -> None:
    """Print detailed PDN file info."""
    try:
        info = read_pdn_info(pdn_path)
    except Exception as exc:
        logger.error("Cannot read %s: %s", pdn_path, exc)
        return

    size_kb = pdn_path.stat().st_size / 1024
    print(f"\n  File:          {pdn_path}")
    print(f"  Size:          {size_kb:.1f} KB")
    print(f"  Dimensions:    {info['width']}×{info['height']}")
    print(f"  Layers:        {info['layer_count']}")
    print(f"  Paint.NET:     {info['version']}")
    print(f"  {'─' * 60}")
    print(f"  {'#':>3}  {'Name':<30} {'Opacity':>7}  {'Visible':>7}  {'Blend Mode'}")
    print(f"  {'─' * 60}")
    for idx, layer in enumerate(info["layers"]):
        vis = "yes" if layer["visible"] else "NO"
        blend = _BLEND_NAMES.get(layer["blend_id"], "?")
        print(f"  {idx + 1:>3}  {layer['name']:<30} {layer['opacity']:>5}/255  {vis:>7}  {blend}")
    print()


def _confirm(prompt: str) -> bool:
    """Ask for y/n confirmation. Returns True for yes."""
    try:
        answer = input(f"{prompt} [y/N] ").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # ── logging setup ──────────────────────────────────────────────
    level = logging.WARNING
    if args.verbose >= 2:
        level = logging.DEBUG
    elif args.verbose >= 1:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)-8s %(message)s",
    )

    # ── resolve input files ────────────────────────────────────────
    inputs = [Path(p) for p in args.input]
    pdn_files = _collect_pdn_files(inputs, recursive=args.recursive)

    if not pdn_files:
        logger.error("No .pdn files found.")
        return 1

    # ── info mode: just print info and exit ────────────────────────
    if args.info:
        for pdn_path in pdn_files:
            _print_info(pdn_path)
        return 0

    # ── validate conflicting options ───────────────────────────────
    if args.output and len(pdn_files) > 1:
        logger.error(
            "Cannot use -o/--output with multiple input files. "
            "Use -D/--output-dir to collect outputs in one directory."
        )
        return 1

    if args.output_dir and args.output:
        logger.error("Cannot use -o/--output and -D/--output-dir together.")
        return 1

    if args.delete and args.delete_only:
        logger.error("Cannot use --delete and --delete-only together.")
        return 1

    # ── --delete confirmation ──────────────────────────────────────
    if (args.delete or args.delete_only) and not args.yes and not args.dry_run:
        count = len(pdn_files)
        if args.delete_only:
            prompt = f"Delete {count} source .pdn file(s) (only if .ora exists)?"
        else:
            prompt = f"Delete {count} source .pdn file(s) after conversion?"
        if not _confirm(prompt):
            logger.info("Aborted.")
            return 0

    # ── convert ────────────────────────────────────────────────────
    successes = 0
    failures = 0
    deleted = 0
    skipped = 0

    for pdn_path in pdn_files:
        # Determine output path
        if args.output:
            ora_path = Path(args.output)
        elif args.output_dir:
            ora_path = Path(args.output_dir) / pdn_path.with_suffix(args.suffix).name
        else:
            ora_path = pdn_path.with_suffix(args.suffix)

        # --delete-only: skip if .ora already exists, just delete source
        if args.delete_only:
            if ora_path.exists():
                if args.dry_run:
                    logger.info("[dry-run] Would delete %s (ora exists)", pdn_path)
                else:
                    pdn_path.unlink()
                    deleted += 1
                    logger.info("Deleted %s (ora exists: %s)", pdn_path, ora_path)
            else:
                logger.info("Skipping %s (no .ora found)", pdn_path)
                skipped += 1
            continue

        # Dry run: just show what would happen
        if args.dry_run:
            action = "overwrite" if ora_path.exists() else "create"
            logger.info("[dry-run] Would %s %s → %s", action, pdn_path, ora_path)
            if args.delete:
                logger.info("[dry-run] Would delete %s", pdn_path)
            successes += 1
            continue

        # Actual conversion
        try:
            convert_pdn_to_ora(
                pdn_path,
                ora_path,
                overwrite=args.overwrite,
                no_thumbnail=args.no_thumbnail,
                validate=args.validate,
            )
            successes += 1
        except FileExistsError as exc:
            logger.error("%s (use --overwrite to replace)", exc)
            failures += 1
            continue
        except Exception as exc:
            logger.error("Failed %s: %s", pdn_path, exc)
            failures += 1
            continue

        # --stats: show size comparison
        if args.stats:
            pdn_size = pdn_path.stat().st_size
            ora_size = ora_path.stat().st_size
            ratio = ora_size / pdn_size if pdn_size else 0
            logger.info(
                "  %s: %d KB → %s: %d KB  (%.1fx)",
                pdn_path.name,
                pdn_size // 1024,
                ora_path.name,
                ora_size // 1024,
                ratio,
            )

        # --delete: remove source after success
        if args.delete:
            pdn_path.unlink()
            deleted += 1
            logger.info("Deleted %s", pdn_path)

    # ── summary ────────────────────────────────────────────────────
    if args.dry_run:
        logger.info("[dry-run] Would convert %d file(s).", successes)
    else:
        parts = [f"{successes} converted"]
        if deleted:
            parts.append(f"{deleted} deleted")
        if skipped:
            parts.append(f"{skipped} skipped")
        if failures:
            parts.append(f"{failures} failed")
        logger.info("Done: %s.", ", ".join(parts))

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

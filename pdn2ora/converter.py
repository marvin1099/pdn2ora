"""Core conversion logic: PDN → ORA."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Optional

import pypdn
from PIL import Image
from pyora import Project

logger = logging.getLogger(__name__)

# PDN blend mode enum value → ORA/SVG composite-op string
PDN_TO_ORA_BLEND: dict[int, str] = {
    0: "svg:src-over",  # Normal
    1: "svg:multiply",  # Multiply
    2: "svg:plus",  # Additive → Addition
    3: "svg:color-burn",  # ColorBurn
    4: "svg:color-dodge",  # ColorDodge
    5: "svg:reflect",  # Reflect (no direct SVG equiv, use closest)
    6: "svg:glow",  # Glow (no direct SVG equiv, use closest)
    7: "svg:overlay",  # Overlay
    8: "svg:difference",  # Difference
    9: "svg:negation",  # Negation (no direct SVG equiv, use closest)
    10: "svg:lighten",  # Lighten
    11: "svg:darken",  # Darken
    12: "svg:screen",  # Screen
    13: "svg:xor",  # XOR
}

DEFAULT_BLEND = "svg:src-over"


def read_pdn_info(pdn_path: Path) -> dict:
    """Read PDN file metadata without extracting pixel data.

    Returns a dict with: width, height, layer_count, version, layers (list of dicts).
    """
    doc = pypdn.read(str(pdn_path))
    if doc is None:
        raise ValueError(f"Failed to read PDN file: {pdn_path}")

    layers_info = []
    for layer in doc.layers:
        blend_id = int(layer.blendMode)
        layers_info.append(
            {
                "name": layer.name,
                "visible": layer.visible,
                "opacity": layer.opacity,
                "is_background": layer.isBackground,
                "blend_mode": PDN_TO_ORA_BLEND.get(blend_id, DEFAULT_BLEND),
                "blend_id": blend_id,
            }
        )

    ver = doc.version
    version = f"{ver.Major}.{ver.Minor}.{ver.Build}.{ver.Revision}"

    return {
        "width": doc.width,
        "height": doc.height,
        "layer_count": len(doc.layers),
        "version": version,
        "layers": layers_info,
    }


def validate_ora(ora_path: Path) -> bool:
    """Validate an ORA file is a well-formed ZIP with required entries."""
    try:
        with zipfile.ZipFile(ora_path, "r") as zf:
            names = zf.namelist()
            if "mimetype" not in names:
                logger.error("Missing mimetype entry")
                return False
            if "stack.xml" not in names:
                logger.error("Missing stack.xml entry")
                return False
            # Check mimetype content
            mimetype = zf.read("mimetype").decode("utf-8")
            if mimetype.strip() != "image/openraster":
                logger.error("Invalid mimetype: %r", mimetype)
                return False
            # Check for at least one layer
            if not any(n.endswith(".png") for n in names):
                logger.error("No PNG layer data found")
                return False
        return True
    except (zipfile.BadZipFile, OSError) as exc:
        logger.error("Invalid ORA file: %s", exc)
        return False


def convert_pdn_to_ora(
    pdn_path: Path,
    ora_path: Optional[Path] = None,
    *,
    overwrite: bool = False,
    no_thumbnail: bool = False,
    validate: bool = False,
) -> Path:
    """Read a PDN file and write it as ORA.

    Returns the path of the written ORA file.
    """
    if ora_path is None:
        ora_path = pdn_path.with_suffix(".ora")

    if ora_path.exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {ora_path}")

    logger.info("Reading %s", pdn_path)
    doc = pypdn.read(str(pdn_path))

    if doc is None:
        raise ValueError(f"Failed to read PDN file: {pdn_path}")

    logger.info(
        "  %dx%d, %d layer(s), Paint.NET %d.%d.%d.%d",
        doc.width,
        doc.height,
        len(doc.layers),
        doc.version.Major,
        doc.version.Minor,
        doc.version.Build,
        doc.version.Revision,
    )

    project = Project.new(doc.width, doc.height)

    # PDN stores layers top-to-bottom; ORA stores bottom-to-top.
    # Iterate in reverse so the bottom-most PDN layer becomes the
    # bottom-most ORA layer.
    for idx, layer in enumerate(reversed(doc.layers)):
        ora_name = layer.name or f"Layer {idx}"

        # pypdn gives us a numpy RGBA uint8 array → convert to PIL Image
        img = Image.fromarray(layer.image)

        blend_op = PDN_TO_ORA_BLEND.get(int(layer.blendMode), DEFAULT_BLEND)
        opacity = layer.opacity / 255.0

        logger.info(
            "  + %-30s  opacity=%3d  visible=%-5s  blend=%s",
            ora_name,
            layer.opacity,
            layer.visible,
            blend_op,
        )

        project.add_layer(
            img,
            ora_name,
            opacity=opacity,
            visible=layer.visible,
            composite_op=blend_op,
        )

    ora_path.parent.mkdir(parents=True, exist_ok=True)
    project.save(str(ora_path))
    logger.info("Wrote %s", ora_path)

    # Validate if requested
    if validate:
        if validate_ora(ora_path):
            logger.info("  ✓ Validation passed")
        else:
            logger.error("  ✗ Validation failed")
            raise ValueError(f"ORA validation failed: {ora_path}")

    return ora_path

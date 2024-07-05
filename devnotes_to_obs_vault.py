from flat_log_parser import flat_note_to_atoms
from pathlib import Path

path = Path(
    "/Users/jonathan/mres_thesis/wine_analysis_hplc_uv/src/wine_analysis_hplc_uv/notes/devnotes.md"
)
out_dir = Path("/Users/jonathan/001_obsidian_vault/zettel")
flat_note_to_atoms(in_path=path, out_dir=out_dir, overwrite_ok=False)
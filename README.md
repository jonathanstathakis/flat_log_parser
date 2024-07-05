A small package for parsing flat log notes and outputting as atomized note files. Takes 1 flat markdown file `in_path` consisting of demarcated note blocks and outputs the blocks as individual files in `out_dir`.

## Usage

See the example below:

```python
from flat_log_parser import flat_note_to_atoms
from pathlib import Path

path = Path(
    "input_flat_file.md"
)
out_dir = Path("output_dir/")
flat_note_to_atoms(in_path=path, out_dir=out_dir, overwrite_ok=False)
```
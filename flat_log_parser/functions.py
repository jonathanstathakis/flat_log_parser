from flat_log_parser import definitions
from pathlib import Path
import regex
from pprint import pformat
from dateutil.parser import parse, ParserError


def flat_note_to_atoms(
    in_path: Path, out_dir: Path, overwrite_ok: bool = False
) -> list[str]:
    notes = get_notes_from_path(path=in_path)

    decomp_notes = decompose_notes(notes=notes)

    validate_datetimes(notes=decomp_notes)

    add_filenames(notes=decomp_notes)

    parse_tags(notes=decomp_notes)

    written_files = output_notes(
        notes=decomp_notes, out_dir_path=out_dir, overwrite_ok=overwrite_ok
    )

    return written_files


def get_notes_from_path(path) -> list[str]:
    with open(path, "r") as f:
        string = f.read()

    pattern = r"(?<=\])\n\n(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    notes = regex.split(pattern=pattern, string=string)

    # simple validation of the regex split. All notes should start with a '2' and end with a ']'
    for note in notes:
        if note[0] != "2":
            raise ValueError("note doesnt start with a 2")
        if note[-1] != "]":
            raise ValueError("note doesnt end with a ']'")

    return notes


def extract_note_fields(note: str) -> dict[str, str] | None:
    regexps = dict(
        datetime=r"(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
        separator=r" - ",
        title=r"(?P<title>.+?(?=\.|\?))",
        content=r"(?<=\2)\. (?P<content>.+?)(?= tag)",
        tags=r"(?<=\3) tags: (?P<tags>.*)$",
    )

    regexp = ""
    for patt in regexps.values():
        regexp += patt

    match = regex.match(regexp, note)

    if match:
        fields = match.groupdict()
    else:
        fields = None

    return fields


def check_notes_without_matches(notes, decomposed_notes):
    # number of notes that didnt match
    n_no_match = len(notes) - len([note for note in decomposed_notes if note])

    # index of each that didnt match
    no_match_indexes = [idx for idx, note in enumerate(decomposed_notes) if not note]
    # the notes themselves
    no_match_notes = [notes[i] for i in no_match_indexes]

    if no_match_indexes:
        with ValueError as e:
            e.add_note(f"number of notes without match: {n_no_match}")
            e.add_note(f"no match notes indexes: {no_match_indexes}")
            e.add_note(
                f"notes that didnt match:\n\n{pformat(dict(zip(no_match_indexes, no_match_notes)))}"
            )


def decompose_notes(notes) -> list[dict[str, str]]:
    """
    Decompose note strings in `notes` into a list of dicts of prespecified fields: 'datetime', 'title', 'content', 'tags'
    """
    decomposed_notes = [extract_note_fields(note) for note in notes]
    check_notes_without_matches(decomposed_notes=decomposed_notes, notes=notes)

    if not any(decomposed_notes):
        raise ValueError("a match was not found in a note")

    return decomposed_notes


def validate_datetimes(notes: list[dict[str, str]]):
    no_parse_date_notes = []

    for note in notes:
        old_dt = note["datetime"]
        try:
            new_dt = parse(old_dt).isoformat()
        except ParserError:
            new_dt = old_dt
            no_parse_date_notes.append(note)
        note["datetime"] = new_dt

    if no_parse_date_notes:
        n_no_parse = len(no_parse_date_notes)
        date_titles = [
            {k: v for k, v in note.items() if k in ["title", "datetime"]}
            for note in no_parse_date_notes
        ]
        err_str = f"Some note datetimes were unable to be parsed. {n_no_parse} were not parsed. They are as follows:\n\n{pformat(date_titles)}"
        raise ValueError(err_str)


def add_filenames(notes: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    add a 'file_name' pair whose value is created from the 'title' string, cleaned for use as a file name. It is validated by testing whether the new file can be written.
    """
    try:
        temp_dir: Path = Path(definitions.ROOT).parent / "test_valid_names"

        temp_dir.mkdir()

        for note in notes:
            title = note["title"]

            # clean
            name = title.lower().strip()

            # remove any trailing punctuation if present
            if name[-1] in ["?", ",", "."]:
                name = name[:-1]

            # replace spaces
            name = name.replace(" ", "_")

            # add ".md"
            name = name + ".md"

            # remove quotation marks

            for char in ['"', ",", "-", "'", "?", "^"]:
                name = name.replace(char, "")

            # test the new file
            temp_outpath = temp_dir / name

            try:
                temp_outpath.touch(exist_ok=False)
            except OSError as e:
                e.add_note(f"file name potentially  invalid: {name}")
                raise e
            finally:
                temp_outpath.unlink()
                note["filename"] = name

    except Exception as e:
        raise e
    finally:
        temp_dir.rmdir()

    return notes


def parse_tags(notes):
    """
    Convert the tags from strings to lists of strings.
    """

    # get the tags

    for note in notes:
        tags = note["tags"].strip()
        # remove brackets
        tags_without_brackets = tags[1:-1].strip()

        # if trailing comma, remove

        if tags_without_brackets[-1] == ",":
            tags_without_brackets = tags_without_brackets[:-1]

        cleaned_tags = [tag.strip() for tag in tags_without_brackets.rsplit(",")]

        for tag in cleaned_tags:
            if " " in tag:
                raise ValueError(
                    f"something went wrong when parsing {note['title']}, space detected.."
                )

        note["cleaned_tags"] = cleaned_tags


import frontmatter
from datetime import datetime
import io


def validate_dir(out_dir_path: Path) -> None:
    """
    validate existance and character of `out_dir_path`
    """

    if not out_dir_path.exists():
        raise ValueError("out_dir_path must exist")
    if not out_dir_path.is_dir():
        raise ValueError("out_dir_path must be a directory")


def add_title_as_markdown(note: dict[str, str]) -> None:
    """
    add the 'title' value to the 'content' string as a capitalized markdown header
    """
    title = note["title"]
    content = note["content"]
    formatted_title = f"# {title.title()}"
    note["content"] = f"{formatted_title}\n\n{content}"


def add_new_line_after_content(note: dict[str, str]) -> None:
    """
    Adds a new line after the last line of content to bring it into line with standards
    """

    note["content"] = note["content"] + "\n"


def add_mres_tag(note):
    """
    add mres tag
    """

    note["cleaned_tags"].append("mres")


def dropping_duplicates_and_sorting_tags(note):
    note["cleaned_tags"] = sorted(list(set(note["cleaned_tags"])))


def form_posts(
    notes: list[dict[str, str]], out_dir_path: Path
) -> list[dict[str, frontmatter.Post | str]]:
    """
    iterate over the notes and pass the information to Post objects. Add modification date
    field 'mdt' at the time of Post object creation.
    """

    frontmatter_objs = []

    for note in notes:
        add_mres_tag(note=note)
        dropping_duplicates_and_sorting_tags(note=note)
        add_title_as_markdown(note=note)
        add_new_line_after_content(note=note)

        post = frontmatter.Post(content=note["content"])
        post["tags"] = note["cleaned_tags"]
        post["cdt"] = note["datetime"]
        post["mdt"] = datetime.now().isoformat()

        filepath = out_dir_path / note["filename"]

        post_dict = {"post": post, "path": filepath}
        frontmatter_objs.append(post_dict)

    return frontmatter_objs


def write_notes(
    posts: list[dict[str, frontmatter.Post | str]], overwrite_ok: bool = False
) -> list[str]:
    """
    write the posts to their internally stored path
    """

    written_files = []

    for post in posts:
        path = str(post["path"])

        if Path(path).exists() and not overwrite_ok:
            raise RuntimeError(
                f"{path} already exists. To overwrite set `overwite_ok` to True"
            )
        else:
            print(f"writing to {path}")
            written_files.append(path)
            frontmatter.dump(post=post["post"], fd=path)

    return written_files


def output_notes(notes, out_dir_path, overwrite_ok: bool = False) -> list[str]:
    posts = form_posts(notes=notes, out_dir_path=out_dir_path)
    written_files = write_notes(posts=posts, overwrite_ok=overwrite_ok)

    return written_files

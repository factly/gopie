from __future__ import annotations

import ast
import hashlib
import itertools
import json
import re
from operator import itemgetter
from pathlib import Path
from typing import Any

from tests.e2e.viz_utils.examples_arguments_syntax import (
    iter_examples_arguments_syntax,
)


def populate_examples(**kwds: Any) -> list[dict[str, Any]]:
    examples = sorted(iter_examples_arguments_syntax(), key=itemgetter("name"))

    for example in examples:
        docstring, category, code, lineno = get_docstring_and_rest(example["filename"])
        method_code = code
        code += (
            "# No channel encoding options are specified in this chart\n"
            "# so the code is the same as for the method-based syntax.\n"
        )
        example.update(kwds)
        if category is None:
            msg = f"The example {example['name']} is not assigned to a category"
            raise Exception(msg)
        example.update(
            {
                "docstring": docstring,
                "title": docstring.strip().split("\n")[0],
                "code": code,
                "method_code": method_code,
                "category": category.title(),
                "lineno": lineno,
            }
        )

    return examples


SYNTAX_ERROR_DOCSTRING = """
SyntaxError
===========
Example script with invalid Python syntax
"""


def _parse_source_file(filename: str | Path) -> tuple[ast.Module | None, str]:
    """
    Parse source file into AST node.

    Parameters
    ----------
    filename : str
        File path

    Returns
    -------
    node : AST node
    content : utf-8 encoded string

    Notes
    -----
    This function adapted from the sphinx-gallery project; license: BSD-3
    https://github.com/sphinx-gallery/sphinx-gallery/
    """
    content = Path(filename).read_text(encoding="utf-8")
    # change from Windows format to UNIX for uniformity
    content = content.replace("\r\n", "\n")

    try:
        node = ast.parse(content)
    except SyntaxError:
        node = None
    return node, content


def get_docstring_and_rest(filename: str | Path) -> tuple[str, str | None, str, int]:
    """
    Separate ``filename`` content between docstring and the rest.

    Strongly inspired from ast.get_docstring.

    Parameters
    ----------
    filename: str
        The path to the file containing the code to be read

    Returns
    -------
    docstring: str
        docstring of ``filename``
    category: list
        list of categories specified by the "# category:" comment
    rest: str
        ``filename`` content without the docstring
    lineno: int
         the line number on which the code starts

    Notes
    -----
    This function adapted from the sphinx-gallery project; license: BSD-3
    https://github.com/sphinx-gallery/sphinx-gallery/
    """
    node, content = _parse_source_file(filename)

    # Find the category comment
    find_category = re.compile(r"^#\s*category:\s*(.*)$", re.MULTILINE)
    match = find_category.search(content)
    if match is not None:
        category = match.groups()[0]
        # remove this comment from the content
        content = find_category.sub("", content)
    else:
        category = None

    lineno = 1

    if node is None:
        return SYNTAX_ERROR_DOCSTRING, category, content, lineno

    if not isinstance(node, ast.Module):
        msg = f"This function only supports modules. You provided {node.__class__.__name__}"
        raise TypeError(msg)
    try:
        # In python 3.7 module knows its docstring.
        # Everything else will raise an attribute error
        docstring = node.docstring  # pyright: ignore[reportAttributeAccessIssue]

        import tokenize
        from io import BytesIO

        ts = tokenize.tokenize(BytesIO(content).readline)  # pyright: ignore[reportArgumentType]
        ds_lines = 0
        # find the first string according to the tokenizer and get
        # it's end row
        for tk in ts:
            if tk.exact_type == 3:
                ds_lines, _ = tk.end
                break
        # grab the rest of the file
        rest = "\n".join(content.split("\n")[ds_lines:])
        lineno = ds_lines + 1

    except AttributeError:
        # this block can be removed when python 3.6 support is dropped
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            docstring_node = node.body[0]
            docstring = docstring_node.value.s  # pyright: ignore[reportAttributeAccessIssue]
            # python2.7: Code was read in bytes needs decoding to utf-8
            # unless future unicode_literals is imported in source which
            # make ast output unicode strings
            if hasattr(docstring, "decode") and not isinstance(docstring, str):
                docstring = docstring.decode("utf-8")
            # python3.8: has end_lineno
            lineno = getattr(
                docstring_node, "end_lineno", docstring_node.lineno
            )  # The last line of the string.
            # This get the content of the file after the docstring last line
            # Note: 'maxsplit' argument is not a keyword argument in python2
            rest = content.split("\n", lineno)[-1]
            lineno += 1
        else:
            docstring, rest = "", ""

    if not docstring:
        msg = (
            f'Could not find docstring in file "{filename}". '
            "A docstring is required for the example gallery."
        )
        raise ValueError(msg)
    return docstring, category, rest, lineno


def prev_this_next(
    it: list[dict[str, Any]], sentinel: None = None
) -> zip[tuple[dict[str, Any] | None, dict[str, Any], dict[str, Any] | None]]:
    """Utility to return (prev, this, next) tuples from an iterator."""
    i1, i2, i3 = itertools.tee(it, 3)
    next(i3, None)
    return zip(itertools.chain([sentinel], i1), i2, itertools.chain(i3, [sentinel]))


def dict_hash(dct: dict[Any, Any]) -> Any:
    """Return a hash of the contents of a dictionary."""
    serialized = json.dumps(dct, sort_keys=True)

    try:
        m = hashlib.sha256(serialized)[:32]  # pyright: ignore[reportArgumentType,reportIndexIssue]
    except TypeError:
        m = hashlib.sha256(serialized.encode())[:32]  # pyright: ignore[reportIndexIssue]

    return m.hexdigest()

import ast
import inspect
import tokenize
from functools import partial
from textwrap import dedent

#############################
# Extracting the docstrings #
#############################


def scrape_comments(src: str):
    """Use the tokenizer module to fetch comments from source.

    Arguments:
        src: The source code.

    Returns:
        List of (line, column, "COMMENT", comment_string)
    """
    lines = bytes(src, encoding="utf8").splitlines(keepends=True)
    return [
        (*tok.start, "COMMENT", tok.string[1:].strip())
        for tok in tokenize.tokenize(partial(next, iter(lines)))
        if tok.type == tokenize.COMMENT
    ]


class AttributeVisitor(ast.NodeVisitor):
    """Walk an AST to gather variable and docstring tokens and their lines/columns."""

    def __init__(self):
        self.data = []
        self.prefix = None

    def add_data(self, node, kind, content):
        self.data.append((node.lineno, node.col_offset, kind, content))

    def visit_body(self, name, stmts):
        old_prefix = self.prefix
        if self.prefix is None:
            self.prefix = ""
        else:
            self.prefix += f"{name}."
        for stmt in stmts:
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                self.add_data(stmt, "DOC", stmt.value.value)
            else:
                self.visit(stmt)
        self.prefix = old_prefix

    def visit_ClassDef(self, node):
        if self.prefix is not None:
            self.add_data(node, "VARIABLE", f"{self.prefix}{node.name}")
        self.visit_body(node.name, node.body)

    def visit_FunctionDef(self, node):
        if self.prefix is not None:
            self.add_data(node, "VARIABLE", f"{self.prefix}{node.name}")
        self.visit_body(node.name, node.body)

    def visit_Assign(self, node):
        self.generic_visit(node, may_assign=True)

    def visit_AnnAssign(self, node):
        self.generic_visit(node, may_assign=True)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.add_data(node, "VARIABLE", f"{self.prefix}{node.id}")

    def generic_visit(self, node, may_assign=False):
        if isinstance(node, ast.stmt) and not may_assign:
            self.add_data(node, "OTHER", None)
        super().generic_visit(node)


def scrape_variables_and_docstrings(src: str):
    """Scrape the variables and docstrings from source code.

    Arguments:
        src: The source code.

    Returns:
        List of (line, column, "VARIABLE"|"DOC"|"OTHER", name_or_content)
    """
    visitor = AttributeVisitor()
    visitor.visit(ast.parse(src))
    return visitor.data


_cached_docstrings = {}


def _get_attribute_docstrings(cls):
    """Get the docstrings for individual attributes of a class.

    Arguments:
        cls: The class for which we want to get attribute documentation.

    Returns:
        A dict from variable name to its associated docstring (after itself) and/or
        comment (above itself).
    """
    if cls in _cached_docstrings:
        return _cached_docstrings[cls]
    docs = {}
    current = None
    current_line = None
    for_next = []
    try:
        src = dedent(inspect.getsource(cls))
    except (OSError, TypeError):
        return {}
    # We concatenate comment tokens from the tokenizer with
    # variable/docstring tokens extracted using the ast module
    data = sorted(scrape_comments(src) + scrape_variables_and_docstrings(src))
    for line, _, kind, content in data:
        if kind == "COMMENT":
            if current is not None and current_line == line:
                docs[current].append(content)
            else:
                for_next.append(content)
        elif kind == "DOC" and current:
            docs[current].append(content)
        elif kind == "VARIABLE":
            docs[content] = for_next
            for_next = []
            current = content
            current_line = line
        elif kind == "OTHER":
            current = current_line = None
            for_next = []
    rval = _cached_docstrings[cls] = {k: "\n".join(lines) for k, lines in docs.items()}
    return rval


def get_attribute_docstrings(cls):
    results = {}
    for subcls in cls.mro():
        results.update(_get_attribute_docstrings(subcls))
    return results

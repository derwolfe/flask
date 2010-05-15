import re
import creoleparser
from genshi import builder
from functools import wraps
from creoleparser.elements import PreBlock
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound
from flask import g, url_for, flash, abort, request, redirect, Markup
from flask_website.flaskystyle import FlaskyStyle # same as docs

from flask_website.database import User

pygments_formatter = HtmlFormatter(style=FlaskyStyle)

_ws_split_re = re.compile(r'(\s+)')


class CodeBlock(PreBlock):

    def __init__(self):
        super(CodeBlock, self).__init__('pre', ['{{{', '}}}'])

    def _build(self, mo, element_store, environ):
        lines = self.regexp2.sub(r'\1', mo.group(1)).splitlines()
        if lines and lines[0].startswith('#!'):
            try:
                lexer = get_lexer_by_name(lines.pop(0)[2:].strip())
            except ClassNotFound:
                pass
            else:
                return Markup(highlight(u'\n'.join(lines), lexer,
                                        pygments_formatter))
        return builder.tag.pre(u'\n'.join(lines))


custom_dialect = creoleparser.create_dialect(creoleparser.creole10_base)
custom_dialect.pre = CodeBlock()


_parser = creoleparser.Parser(
    dialect=custom_dialect,
    method='html'
)


def format_creole(text):
    return Markup(_parser.render(text, encoding=None))


def split_lines_wrapping(text, width=74, threshold=82):
    lines = text.splitlines()
    if all(len(line) <= threshold for line in lines):
        return lines
    result = []
    for line in lines:
        if len(line) <= threshold:
            result.append(line)
            continue
        line_width = 0
        line_buffer = []
        for piece in _ws_split_re.split(line):
            line_width += len(piece)
            if line_width > width:
                result.append(u''.join(line_buffer))
                line_buffer = []
                if not piece.isspace():
                    line_buffer.append(piece)
                    line_width = len(piece)
                else:
                    line_width = 0
            else:
                line_buffer.append(piece)
        if line_buffer:
            result.append(u''.join(line_buffer))
    return result


def requires_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash(u'You need to be signed in for this page.')
            return redirect(url_for('general.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def requires_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user.is_admin:
            abort(401)
        return f(*args, **kwargs)
    return requires_login(decorated_function)

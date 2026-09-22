import re
from html.parser import HTMLParser

import markdown
import nh3

TAGS = {'p', 'br', 'em', 'strong', 'blockquote', 'h2', 'h3', 'h4', 'hr', 'ul', 'ol', 'li', 'a', 'sup', 'sub'}


def render_content(body, body_format='markdown'):
    html = markdown.markdown(body, extensions=['sane_lists']) if body_format == 'markdown' else body
    html = nh3.clean(html, tags=TAGS, attributes={'a': {'href', 'title'}},
                     url_schemes={'https', 'http'}, strip_comments=True,
                     clean_content_tags={'script', 'style', 'iframe', 'object', 'svg', 'math'})
    # IDs come from the server, never from author-supplied HTML attributes.
    counter = iter(range(1, 1000000))
    return re.sub(r'<(p|h2|h3|h4|blockquote)(?=>)',
                  lambda m: f'<{m[1]} id="p-{next(counter)}"', html)


def valid_slug(value):
    return bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value or '')) and len(value) <= 120


def valid_cover(value):
    return not value or bool(re.fullmatch(r'/images/[A-Za-z0-9_-]+\.(?:png|jpg|jpeg|webp|svg)', value))


def count_words(body, body_format='markdown'):
    class Text(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
        def handle_data(self, data):
            self.parts.append(data)
        def handle_starttag(self, tag, attrs):
            if tag in {'p', 'br', 'h2', 'h3', 'h4', 'li', 'blockquote'}:
                self.parts.append(' ')
        def handle_endtag(self, tag):
            self.handle_starttag(tag, [])
    text = Text()
    text.feed(render_content(body, body_format))
    return len(re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", ''.join(text.parts), re.UNICODE))

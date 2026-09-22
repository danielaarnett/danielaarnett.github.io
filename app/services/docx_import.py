from html import escape
from pathlib import Path
from zipfile import ZipFile

from docx import Document


def import_prologue(path):
    """Read visible DOCX paragraphs, preserving run emphasis and text verbatim.

    The first two paragraphs are the work title and subtitle; material before
    the Prologue heading is a dedication. Unsupported structures are rejected
    rather than silently dropping author content.
    """
    path = Path(path)
    with ZipFile(path) as archive:
        if sum(item.file_size for item in archive.infolist()) > 20 * 1024 * 1024:
            raise ValueError('Документ слишком большой для импорта.')
    doc = Document(path)
    if doc.tables or doc.inline_shapes:
        raise ValueError('Этот импорт поддерживает текст и выделения; таблицы и рисунки требуют отдельного переноса.')
    if doc.element.xpath('.//w:ins | .//w:del | .//w:footnoteReference | .//w:endnoteReference'):
        raise ValueError('Сначала примите правки и перенесите сноски в основной текст.')
    paragraphs = [p for p in doc.paragraphs if p.text.strip()]
    if len(paragraphs) < 4:
        raise ValueError('Не найден текст произведения.')
    heading = next((i for i, p in enumerate(paragraphs) if p.text.strip().lower() == 'пролог'), None)
    if heading is None or heading < 2:
        raise ValueError('В документе не найден заголовок «Пролог».')

    def paragraph_html(paragraph):
        chunks = []
        for run in paragraph.runs:
            value = escape(run.text).replace('\n', '<br>').replace('\t', '    ')
            if run.italic:
                value = '<em>' + value + '</em>'
            if run.bold:
                value = '<strong>' + value + '</strong>'
            chunks.append(value)
        # Hyperlinks are uncommon in fiction, but losing their text is unacceptable.
        if ''.join(r.text for r in paragraph.runs) != paragraph.text:
            raise ValueError('Абзац содержит вложенные элементы. Нужна ручная проверка импорта.')
        return '<p>' + ''.join(chunks) + '</p>'

    dedication = ''.join(paragraph_html(p) for p in paragraphs[2:heading])
    prose = ''.join(paragraph_html(p) for p in paragraphs[heading+1:])
    body = ('<blockquote>' + dedication + '</blockquote>' if dedication else '') + prose
    return dict(title=paragraphs[0].text.strip('«»“”" '), subtitle=paragraphs[1].text,
                chapter_title=paragraphs[heading].text, body=body,
                source_paragraphs=len(paragraphs), prose_paragraphs=len(paragraphs)-heading-1)

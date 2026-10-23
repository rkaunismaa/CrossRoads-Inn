"""Build tiny .ods files for tests without LibreOffice."""
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

_HEAD = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<office:document-content'
    ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
    ' office:version="1.2"><office:body><office:spreadsheet>'
)
_TAIL = "</office:spreadsheet></office:body></office:document-content>"


def _cell(value) -> str:
    if isinstance(value, tuple):  # (text, repeat)
        text, repeat = value
        return (f'<table:table-cell table:number-columns-repeated="{repeat}">'
                f"<text:p>{escape(str(text))}</text:p></table:table-cell>")
    if value == "":
        return "<table:table-cell/>"
    return f"<table:table-cell><text:p>{escape(str(value))}</text:p></table:table-cell>"


def make_ods(path: Path, sheets: dict[str, list[list]]) -> Path:
    body = ""
    for name, rows in sheets.items():
        body += f'<table:table table:name="{escape(name)}">'
        for row in rows:
            body += "<table:table-row>" + "".join(_cell(c) for c in row) + "</table:table-row>"
        body += "</table:table>"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/vnd.oasis.opendocument.spreadsheet")
        z.writestr("content.xml", _HEAD + body + _TAIL, compress_type=zipfile.ZIP_DEFLATED)
    return path

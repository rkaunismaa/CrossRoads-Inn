"""Write sheets of balance.ods through a private headless LibreOffice over UNO.

Each call starts its own soffice with a throwaway user profile, so it never
clashes with a Calc window the user has open on other files. A write replaces
only the named sheet; every other sheet is left as it was.
"""
import contextlib
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import uno
from com.sun.star.beans import PropertyValue

from inn_sim.params import DEFAULT_PARAMS, ParamError, WorkbookLocked, read_sheet

# com.sun.star.sheet.CellFlags: VALUE | DATETIME | STRING | ANNOTATION | FORMULA
_CLEAR_FLAGS = 1 | 2 | 4 | 8 | 16
_PARAMS_HEADER = ["name", "value", "notes"]
_CONNECT_TIMEOUT = 30.0


def _prop(name: str, value: object) -> PropertyValue:
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def _check_unlocked(ods_path: Path) -> None:
    lock = ods_path.parent / f".~lock.{ods_path.name}#"
    if lock.exists():
        raise WorkbookLocked(f"{ods_path.name} is open in LibreOffice ({lock.name} exists); "
                             "close the workbook in Calc first")


@contextlib.contextmanager
def _office() -> Iterator[object]:
    """Start a private headless soffice and yield its Desktop."""
    port = _free_port()
    with tempfile.TemporaryDirectory(prefix="inn_sim_lo_") as profile:
        proc = subprocess.Popen(
            ["soffice", f"-env:UserInstallation={Path(profile).as_uri()}", "--headless", "--invisible",
             "--norestore", "--nologo", "--nodefault",
             f"--accept=socket,host=localhost,port={port};urp;StarOffice.ComponentContext"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            local = uno.getComponentContext()
            resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
            deadline = time.monotonic() + _CONNECT_TIMEOUT
            while True:
                try:
                    ctx = resolver.resolve(f"uno:socket,host=localhost,port={port};urp;StarOffice.ComponentContext")
                    break
                except Exception:
                    if time.monotonic() > deadline or proc.poll() is not None:
                        raise RuntimeError("could not start headless LibreOffice (soffice)") from None
                    time.sleep(0.2)
            desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
            try:
                yield desktop
            finally:
                with contextlib.suppress(Exception):
                    desktop.terminate()
        finally:
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


@contextlib.contextmanager
def _document(ods_path: Path, create: bool = False) -> Iterator[object]:
    """Open (or create) a spreadsheet, yield it, then save it as .ods and close it."""
    if not create:
        _check_unlocked(ods_path)
    with _office() as desktop:
        url = "private:factory/scalc" if create else uno.systemPathToFileUrl(str(ods_path.resolve()))
        doc = desktop.loadComponentFromURL(url, "_blank", 0, (_prop("Hidden", True),))
        try:
            yield doc
            doc.storeToURL(uno.systemPathToFileUrl(str(ods_path.resolve())), (_prop("FilterName", "calc8"),))
        finally:
            doc.close(True)


def _fill(doc: object, sheet_name: str, rows: list[list[str | float]]) -> None:
    sheets = doc.Sheets
    if not sheets.hasByName(sheet_name):
        sheets.insertNewByName(sheet_name, sheets.getCount())
    sheet = sheets.getByName(sheet_name)
    used = sheet.createCursor()
    used.gotoEndOfUsedArea(False)
    sheet.getCellRangeByPosition(0, 0, used.RangeAddress.EndColumn, used.RangeAddress.EndRow).clearContents(_CLEAR_FLAGS)
    if not rows:
        return
    width = max(len(r) for r in rows) or 1
    data = tuple(
        tuple(float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v) for v in r)
        + ("",) * (width - len(r))
        for r in rows)
    sheet.getCellRangeByPosition(0, 0, width - 1, len(rows) - 1).setDataArray(data)


def _params_rows(values: dict[str, float]) -> list[list[str | float]]:
    return [_PARAMS_HEADER] + [[name, values[name], note] for name, (_v, note) in DEFAULT_PARAMS.items()]


def write_sheet(ods_path: Path, sheet: str, rows: list[list[str | float]]) -> None:
    with _document(ods_path) as doc:
        _fill(doc, sheet, rows)


def write_sheets(ods_path: Path, sheets: dict[str, list[list[str | float]]]) -> None:
    """Several sheets in one LibreOffice session."""
    with _document(ods_path) as doc:
        for name, rows in sheets.items():
            _fill(doc, name, rows)


def create_workbook(ods_path: Path) -> None:
    from inn_sim.handplay import HANDPLAY_HEADER, REVEAL_HEADER

    if ods_path.exists():
        raise FileExistsError(f"{ods_path} already exists; not overwriting it")
    with _document(ods_path, create=True) as doc:
        doc.Sheets.getByIndex(0).setName("Params")
        _fill(doc, "Params", _params_rows({k: v for k, (v, _n) in DEFAULT_PARAMS.items()}))
        _fill(doc, "HandPlay", [HANDPLAY_HEADER])
        _fill(doc, "Reveal", [REVEAL_HEADER])


def set_params(ods_path: Path, updates: dict[str, float]) -> None:
    """Change only the given values on the Params sheet, keeping names and notes."""
    unknown = [name for name in updates if name not in DEFAULT_PARAMS]
    if unknown:
        raise ParamError(f"unknown param(s): {', '.join(unknown)}")
    rows = read_sheet(ods_path, "Params")
    new_rows: list[list[str | float]] = [list(rows[0])] if rows else [_PARAMS_HEADER]
    for row in rows[1:]:
        row: list[str | float] = list(row)
        if row and str(row[0]).strip() in updates:
            row[1:2] = [updates[str(row[0]).strip()]]
        elif len(row) > 1:
            with contextlib.suppress(ValueError):
                row[1] = float(row[1])  # keep untouched values as numbers, not text
        new_rows.append(row)
    write_sheet(ods_path, "Params", new_rows)

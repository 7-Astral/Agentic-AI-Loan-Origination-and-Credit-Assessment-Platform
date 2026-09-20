import io
import logging
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

import pdfplumber

logger = logging.getLogger(__name__)

MAX_PAGES = 100
MIN_WORDS = 20
LINE_TOLERANCE = 3.0

MONEY = re.compile(r"^-?\$?-?[\d,]+\.\d{2}$")
MONTHS = {name: number for number, name in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
RANGE_JOINERS = {"to", "-", "–", "—"}

OPENING_LABELS = [["opening", "balance"], ["balance", "brought", "forward"], ["previous", "balance"]]
CLOSING_LABELS = [["closing", "balance"], ["balance", "carried", "forward"], ["new", "balance"]]
HOLDER_LABELS = [["account", "holder", "name"], ["account", "holder"], ["account", "name"]]


@dataclass
class Word:
    page: int
    text: str
    x0: float
    x1: float
    top: float
    bottom: float


@dataclass
class Line:
    page: int
    words: list[Word]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass
class PdfDoc:
    pages: list[tuple[float, float]]
    lines: list[Line]


def _clean(text: str) -> str:
    return text.strip().strip(":").lower()


def _money(text: str) -> Decimal | None:
    if not MONEY.match(text):
        return None
    try:
        return Decimal(text.replace("$", "").replace(",", ""))
    except InvalidOperation:
        return None


def parse_date(text: str) -> str | None:
    """ISO, D/M/YYYY (day first) or 'D Mon YYYY' to an ISO date string."""
    text = text.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return date.fromisoformat(text).isoformat()
        found = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if found:
            return date(int(found[3]), int(found[2]), int(found[1])).isoformat()
        found = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})", text)
        if found and found[2][:3].lower() in MONTHS:
            return date(int(found[3]), MONTHS[found[2][:3].lower()], int(found[1])).isoformat()
    except ValueError:
        return None
    return None


def _date_at(words: list[Word], index: int) -> tuple[str, int] | None:
    """A date starting at words[index], as (iso, number of words it spans)."""
    if index >= len(words):
        return None
    single = parse_date(words[index].text)
    if single:
        return single, 1
    if index + 2 < len(words):
        triple = parse_date(" ".join(w.text for w in words[index:index + 3]))
        if triple:
            return triple, 3
    return None


def _box(words: list[Word]) -> dict:
    return {
        "page": words[0].page,
        "x": min(w.x0 for w in words),
        "y": min(w.top for w in words),
        "w": max(w.x1 for w in words) - min(w.x0 for w in words),
        "h": max(w.bottom for w in words) - min(w.top for w in words),
    }


def read_pdf(content: bytes) -> PdfDoc | None:
    """Words grouped into lines, or None if this is not a PDF with a usable text layer."""
    if not content.startswith(b"%PDF"):
        return None
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                return None
            sizes, lines, total = [], [], 0
            for number, page in enumerate(pdf.pages):
                sizes.append((float(page.width), float(page.height)))
                words = sorted(
                    (Word(number, w["text"], w["x0"], w["x1"], w["top"], w["bottom"]) for w in page.extract_words()),
                    key=lambda w: (w.top, w.x0),
                )
                total += len(words)
                current: list[Word] = []
                for word in words:
                    if current and abs(word.top - current[0].top) > LINE_TOLERANCE:
                        lines.append(Line(number, sorted(current, key=lambda w: w.x0)))
                        current = []
                    current.append(word)
                if current:
                    lines.append(Line(number, sorted(current, key=lambda w: w.x0)))
    except Exception:
        logger.warning("Could not read PDF text layer", exc_info=True)
        return None
    return PdfDoc(sizes, lines) if total >= MIN_WORDS else None


def _find_phrase(words: list[Word], phrases: list[list[str]]) -> tuple[int, int] | None:
    """Index range of the first phrase found in the words, ignoring case and colons."""
    cleaned = [_clean(w.text) for w in words]
    for phrase in phrases:
        for start in range(len(cleaned) - len(phrase) + 1):
            if cleaned[start:start + len(phrase)] == phrase:
                return start, start + len(phrase)
    return None


def _transaction_rows(doc: PdfDoc) -> list[dict] | None:
    rows = []
    for line in doc.lines:
        found = _date_at(line.words, 0)
        if not found:
            continue
        iso, span = found
        tail = line.words[span:]
        money_at = len(tail)
        while money_at > 0 and _money(tail[money_at - 1].text) is not None:
            money_at -= 1
        figures = tail[money_at:]
        if len(figures) < 2 or money_at == 0:
            continue
        if len(figures) > 2:
            return None  # a layout with more columns than we understand
        rows.append({
            "date": iso,
            "description": " ".join(w.text for w in tail[:money_at]),
            "amount": abs(_money(figures[0].text)),
            "balance": _money(figures[1].text),
            "words": line.words,
        })
    return rows


def _labelled_amount(doc: PdfDoc, phrases: list[list[str]]) -> tuple[Decimal, Word] | None:
    """The amount printed next to (or directly under) a label such as 'Closing balance'."""
    for index, line in enumerate(doc.lines):
        label = _find_phrase(line.words, phrases)
        if not label:
            continue
        after = [w for w in line.words[label[1]:] if _money(w.text) is not None]
        if after:
            return _money(after[0].text), after[0]
        below = doc.lines[index + 1] if index + 1 < len(doc.lines) else None
        if below and below.page == line.page:
            anchor = line.words[label[0]].x0
            candidates = [w for w in below.words if _money(w.text) is not None]
            if candidates:
                nearest = min(candidates, key=lambda w: abs(w.x0 - anchor))
                return _money(nearest.text), nearest
    return None


def _account_holder(doc: PdfDoc) -> tuple[str, list[Word]] | None:
    for index, line in enumerate(doc.lines[:60]):
        label = _find_phrase(line.words, HOLDER_LABELS)
        if not label:
            continue
        rest = line.words[label[1]:]
        named: list[Word] = []
        if line.words[label[1] - 1].text.endswith(":") or (rest and rest[0].text == ":"):
            named = [w for w in rest if w.text != ":"]
        else:
            below = doc.lines[index + 1] if index + 1 < len(doc.lines) else None
            if below and below.page == line.page:
                left = line.words[label[0]].x0 - 4
                right = rest[0].x0 - 4 if rest else float("inf")
                named = [w for w in below.words if left <= w.x0 < right]
        words = []
        for word in named:
            if any(ch.isdigit() for ch in word.text):
                break
            words.append(word)
        if len(words) >= 2:
            return " ".join(w.text for w in words), words
    return None


def _period(doc: PdfDoc) -> tuple[str, str, list[Word]] | None:
    for line in doc.lines[:40]:
        words = line.words
        for start in range(len(words)):
            first = _date_at(words, start)
            if not first:
                continue
            joiner = start + first[1]
            if joiner < len(words) and words[joiner].text in RANGE_JOINERS:
                second = _date_at(words, joiner + 1)
                if second:
                    return first[0], second[0], words[start:joiner + 1 + second[1]]
    return None


def parse_bank_statement(doc: PdfDoc) -> dict | None:
    rows = _transaction_rows(doc)
    holder = _account_holder(doc)
    period = _period(doc)
    opening = _labelled_amount(doc, OPENING_LABELS)
    closing = _labelled_amount(doc, CLOSING_LABELS)
    if not rows or not (holder and period and opening and closing):
        return None

    running = opening[0]
    transactions = []
    for row in rows:
        change = row["balance"] - running
        if change == row["amount"]:
            direction = "credit"
        elif change == -row["amount"]:
            direction = "debit"
        else:
            return None  # this row does not follow from the balance before it
        transactions.append({
            "date": row["date"], "description": row["description"],
            "amount": float(row["amount"]), "direction": direction,
        })
        running = row["balance"]
    if running != closing[0]:
        return None

    total_in = sum(Decimal(str(t["amount"])) for t in transactions if t["direction"] == "credit")
    total_out = sum(Decimal(str(t["amount"])) for t in transactions if t["direction"] == "debit")
    period_box = _box(period[2])
    return {
        "fields": {
            "account_holder_name": holder[0],
            "statement_period_start": period[0],
            "statement_period_end": period[1],
            "closing_balance": float(closing[0]),
            "transactions": transactions,
        },
        "checks": {
            "opening_balance": float(opening[0]), "closing_balance": float(closing[0]),
            "total_in": float(total_in), "total_out": float(total_out),
            "rows": len(transactions), "reconciled": True,
        },
        "boxes": {
            "fields": {
                "account_holder_name": _box(holder[1]),
                "statement_period_start": period_box,
                "statement_period_end": period_box,
                "closing_balance": _box([closing[1]]),
            },
            "rows": [_box(row["words"]) for row in rows],
        },
        "pages": [{"width": w, "height": h} for w, h in doc.pages],
    }


def read_bank_statement_pdf(content: bytes) -> dict | None:
    """The whole fast path in one call. None means: use the AI instead."""
    doc = read_pdf(content)
    return parse_bank_statement(doc) if doc else None


def render_pages(content: bytes, max_pages: int = 8, resolution: int = 110) -> list[bytes]:
    """PNG images of the first pages, so the browser can draw boxes over them."""
    images = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages[:max_pages]:
            buffer = io.BytesIO()
            page.to_image(resolution=resolution).original.save(buffer, format="PNG")
            images.append(buffer.getvalue())
    return images

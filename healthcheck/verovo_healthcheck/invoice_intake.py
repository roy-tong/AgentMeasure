"""Optional invoice2data adapter: extract an *unreviewed draft*, never book costs.

Financial accuracy and billability need the original document, contract,
task assignment and human confirmation. This module does not import amounts
into the economics ledger and does not perform network requests.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


class InvoiceIntakeError(ValueError):
    pass


def _amount(value):
    if isinstance(value, bool) or value is None:
        raise InvoiceIntakeError("invoice amount is missing or not numeric")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise InvoiceIntakeError("invoice amount is not numeric") from exc
    if not amount.is_finite() or amount < 0:
        raise InvoiceIntakeError("invoice amount must be finite and nonnegative")
    return str(amount)


def extract_invoice(path):
    """Parse local invoice to a source-linked, unreviewed draft.

    The caller needs to install invoice2data and appropriate vendor templates.
    No guessed tax/credit/FX and no automatic accounting entry are produced.
    """
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise InvoiceIntakeError("invoice must be an existing local file")
    if source.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".txt"}:
        raise InvoiceIntakeError("unsupported invoice file type")
    raw = source.read_bytes()
    if not raw:
        raise InvoiceIntakeError("invoice file is empty")
    try:
        from invoice2data import extract_data
    except ImportError as exc:
        raise InvoiceIntakeError(
            "invoice2data is optional. Install: pip install invoice2data; "
            "a matching vendor template may also be required."
        ) from exc
    try:
        data = extract_data(str(source))
    except Exception as exc:
        raise InvoiceIntakeError("invoice2data extraction failed: " + str(exc)) from exc
    if not isinstance(data, dict):
        raise InvoiceIntakeError("no matching invoice template or empty extraction")
    for key in ("issuer", "invoice_number", "currency"):
        if not str(data.get(key) or "").strip():
            raise InvoiceIntakeError("extracted invoice needs a reviewed " + key)
    currency = str(data["currency"]).upper().strip()
    if len(currency) != 3 or not currency.isalpha():
        raise InvoiceIntakeError("currency must be a three-letter ISO code")
    when = data.get("date")
    if isinstance(when, (datetime, date)):
        when = when.isoformat()
    elif when is not None:
        when = str(when)
    return {
        "schema_version": "1.0",
        "kind": "verovo.invoice-extraction-draft",
        "source_filename": source.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "extraction_engine": "invoice2data",
        "template_name": str(data.get("template_name") or ""),
        "issuer": str(data["issuer"]),
        "invoice_number": str(data["invoice_number"]),
        "date": when,
        "currency": currency,
        "gross_amount": _amount(data.get("amount")),
        "tax": None,
        "credits": None,
        "refunds": None,
        "task_allocation": None,
        "review_status": "unreviewed",
        "cost_ledger_status": "not_imported",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "Source text and extraction need review against original invoice",
            "Gross amount may include tax; no tax/credit/refund/FX assumptions",
            "No task allocation or invoice deduplication is implied",
            "Do not count this draft as a booked cost or verified charge",
        ],
    }

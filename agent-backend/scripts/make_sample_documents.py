import html
import json
import re
import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

SAMPLES = Path(__file__).resolve().parent.parent / "app" / "agents" / "document" / "samples"

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

STYLE = """
<style>
  * { box-sizing: border-box; }
  body { font-family: Arial, Helvetica, sans-serif; color: #1f2933; margin: 0; padding: 36px 44px; font-size: 13px; background: #fff; width: 820px; }
  h1 { font-size: 22px; margin: 0; }
  .bar { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #1d4ed8; padding-bottom: 14px; margin-bottom: 18px; }
  .muted { color: #6b7280; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  th { text-align: left; background: #eef2ff; padding: 7px 8px; font-size: 12px; }
  td { padding: 6px 8px; border-bottom: 1px solid #e5e7eb; }
  .r { text-align: right; font-variant-numeric: tabular-nums; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 30px; margin: 10px 0 16px; }
  .k { color: #6b7280; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
  .v { font-weight: 600; }
  .total td { font-weight: 700; border-top: 2px solid #1f2933; }
  .foot { margin-top: 26px; font-size: 10px; color: #9ca3af; border-top: 1px dashed #d1d5db; padding-top: 8px; }
</style>
"""

BOX_SCRIPT = """
<script>
if (location.hash === '#boxes') window.addEventListener('load', () => {
  const box = (el) => { const r = el.getBoundingClientRect(); return {x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height}; };
  const out = {fields: {}, rows: []};
  document.querySelectorAll('[data-field]').forEach((el) => el.dataset.field.split(' ').forEach((f) => { out.fields[f] = box(el); }));
  document.querySelectorAll('[data-row]').forEach((el) => { out.rows[Number(el.dataset.row)] = box(el); });
  const pre = document.createElement('pre'); pre.id = '__boxes'; pre.textContent = JSON.stringify(out);
  document.body.appendChild(pre);
});
</script>
"""

FOOTER = '<div class="foot">SAMPLE DOCUMENT. Fictional names and figures generated for software demonstration only.</div>'


def money(value: Decimal | float) -> str:
    return f"{Decimal(str(value)):,.2f}"


def page(title: str, body: str) -> str:
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>{STYLE}</head><body>{body}{FOOTER}{BOX_SCRIPT}</body></html>"


def payslip() -> tuple[str, int]:
    gross, tax = Decimal("3653.85"), Decimal("1203.85")
    net = gross - tax
    body = f"""
    <div class="bar"><div><h1><span data-field="employer_name">Harbourview Logistics Pty Ltd</span></h1><div class="muted">Level 4, 220 Dock Road, Port Melbourne VIC 3207</div></div>
      <div style="text-align:right"><h1>PAYSLIP</h1><div class="muted">Pay date 17 Sep 2026</div></div></div>
    <div class="grid">
      <div><div class="k">Employee</div><div class="v"><span data-field="employee_name">Jane Citizen</span></div></div>
      <div><div class="k">Employee ID</div><div class="v">HL-20418</div></div>
      <div><div class="k">Pay period</div><div class="v"><span data-field="pay_period_start pay_period_end">31 Aug 2026 to 13 Sep 2026</span></div></div>
      <div><div class="k">Pay frequency</div><div class="v"><span data-field="pay_frequency">Fortnightly</span></div></div>
      <div><div class="k">Position</div><div class="v">Operations Coordinator (Full time)</div></div>
      <div><div class="k">Annual salary</div><div class="v">$95,000.00</div></div>
    </div>
    <table><tr><th>Earnings</th><th class="r">Hours</th><th class="r">This period</th><th class="r">Year to date</th></tr>
      <tr><td>Ordinary hours</td><td class="r">76.00</td><td class="r">{money(gross)}</td><td class="r">{money(gross * 38)}</td></tr>
      <tr class="total"><td>Gross pay</td><td></td><td class="r"><span data-field="gross_pay_this_period">{money(gross)}</span></td><td class="r">{money(gross * 38)}</td></tr></table>
    <table><tr><th>Deductions</th><th class="r">This period</th><th class="r">Year to date</th></tr>
      <tr><td>PAYG withholding tax</td><td class="r">{money(tax)}</td><td class="r">{money(tax * 38)}</td></tr>
      <tr class="total"><td>Net pay</td><td class="r">{money(net)}</td><td class="r">{money(net * 38)}</td></tr></table>
    <table><tr><th>Employer contributions</th><th class="r">This period</th></tr>
      <tr><td>Superannuation guarantee (12%)</td><td class="r">{money(gross * Decimal('0.12'))}</td></tr></table>
    <p class="muted">Net pay deposited to account ending 4471.</p>"""
    return page("Payslip", body), 600


def utility_bill() -> tuple[str, int]:
    body = """
    <div class="bar"><div><h1>Example Energy</h1><div class="muted">Electricity and gas retailer</div></div>
      <div style="text-align:right"><h1>TAX INVOICE</h1><div class="muted">Bill date <span data-field="document_date">5 Sep 2026</span></div></div></div>
    <div class="grid">
      <div><div class="k">Account holder</div><div class="v"><span data-field="name_on_document">Jane Citizen</span></div></div>
      <div><div class="k">Account number</div><div class="v">EE 4820 1177</div></div>
      <div><div class="k">Supply address</div><div class="v"><span data-field="address">12 Wattle Street, Brunswick VIC 3056</span></div></div>
      <div><div class="k">Billing period</div><div class="v">1 Jun 2026 to 31 Aug 2026</div></div>
    </div>
    <table><tr><th>Charges</th><th class="r">Amount</th></tr>
      <tr><td>Electricity usage (812 kWh)</td><td class="r">$243.60</td></tr>
      <tr><td>Gas usage (2,140 MJ)</td><td class="r">$71.10</td></tr>
      <tr><td>Supply charges (92 days)</td><td class="r">$126.50</td></tr>
      <tr class="total"><td>Total due by 26 Sep 2026</td><td class="r">$441.20</td></tr></table>
    <p class="muted">Pay by direct debit or online using your account number.</p>"""
    return page("Utility bill", body), 500


def bank_statement() -> tuple[str, int]:
    opening = Decimal("24120.55")
    rows = [
        ("2026-08-19", "WOOLWORTHS METRO BRUNSWICK", "debit", "87.45"),
        ("2026-08-20", "RENT PORTER REALTY", "debit", "1400.00"),
        ("2026-08-20", "SALARY HARBOURVIEW LOGISTICS", "credit", "2450.00"),
        ("2026-08-22", "COLES EXPRESS 3056", "debit", "54.20"),
        ("2026-08-24", "FUEL SHELL COLES EXPRESS", "debit", "76.10"),
        ("2026-08-26", "EXAMPLE ENERGY DIRECT DEBIT", "debit", "142.30"),
        ("2026-08-28", "VIVIDTEL MOBILE PLAN", "debit", "65.00"),
        ("2026-08-29", "WOOLWORTHS BRUNSWICK", "debit", "123.80"),
        ("2026-09-01", "CARE HEALTH FUND PREMIUM", "debit", "180.00"),
        ("2026-09-02", "TRANSFER FROM M CITIZEN GIFT", "credit", "9000.00"),
        ("2026-09-03", "SALARY HARBOURVIEW LOGISTICS", "credit", "2450.00"),
        ("2026-09-04", "MARIOS PIZZERIA BRUNSWICK", "debit", "38.90"),
        ("2026-09-05", "CITY GYM MEMBERSHIP", "debit", "49.00"),
        ("2026-09-07", "WOOLWORTHS BRUNSWICK", "debit", "96.35"),
        ("2026-09-09", "MYKI TOP UP", "debit", "40.00"),
        ("2026-09-10", "CHEMIST WAREHOUSE BRUNSWICK", "debit", "34.50"),
        ("2026-09-11", "NETFLIX SUBSCRIPTION", "debit", "16.99"),
        ("2026-09-12", "COLES BRUNSWICK", "debit", "71.05"),
        ("2026-09-14", "KMART BRUNSWICK", "debit", "68.00"),
        ("2026-09-15", "TRANSFER TO SAVINGS", "debit", "500.00"),
        ("2026-09-17", "SALARY HARBOURVIEW LOGISTICS", "credit", "2450.00"),
    ]
    balance = opening
    lines = []
    for index, (date, description, direction, amount) in enumerate(rows):
        value = Decimal(amount)
        balance += value if direction == "credit" else -value
        debit = money(value) if direction == "debit" else ""
        credit = money(value) if direction == "credit" else ""
        lines.append(
            f"<tr data-row='{index}'><td>{date}</td><td>{html.escape(description)}</td>"
            f"<td class='r'>{debit}</td><td class='r'>{credit}</td><td class='r'>{money(balance)}</td></tr>"
        )
    body = f"""
    <div class="bar"><div><h1>Northern Cross Bank</h1><div class="muted">Everyday Transaction Account</div></div>
      <div style="text-align:right"><h1>ACCOUNT STATEMENT</h1><div class="muted">Statement 18 Aug 2026 to 17 Sep 2026</div></div></div>
    <div class="grid">
      <div><div class="k">Account holder</div><div class="v"><span data-field="account_holder_name">Jane Citizen</span></div></div>
      <div><div class="k">BSB / Account</div><div class="v">000-000 / 1234 4471</div></div>
      <div><div class="k">Statement period</div><div class="v"><span data-field="statement_period_start statement_period_end">2026-08-18 to 2026-09-17</span></div></div>
      <div><div class="k">Opening balance</div><div class="v">${money(opening)}</div></div>
    </div>
    <table><tr><th>Date</th><th>Description</th><th class="r">Debit</th><th class="r">Credit</th><th class="r">Balance</th></tr>
      {''.join(lines)}
      <tr class="total"><td></td><td>Closing balance</td><td></td><td></td><td class="r"><span data-field="closing_balance">${money(balance)}</span></td></tr></table>"""
    return page("Bank statement", body), 940


VIEWPORT_WIDTH = 820


def measure_boxes(browser: str, source: Path, height: int) -> dict:
    """Ask the browser where each tagged value sits on the page. Positions are CSS pixels."""
    dump = subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
         f"--window-size={VIEWPORT_WIDTH},{height}",
         "--virtual-time-budget=4000", "--dump-dom", source.as_uri() + "#boxes"],
        check=True, capture_output=True, timeout=120,
    ).stdout.decode("utf-8", errors="replace")
    found = re.search(r'<pre id="__boxes">(.*?)</pre>', dump, re.S)
    if not found:
        sys.exit(f"Could not measure {source.name}")
    layout = json.loads(html.unescape(found.group(1)))
    return {"width": VIEWPORT_WIDTH, "height": height, **layout}


DOCUMENTS = {"payslip": payslip, "bank_statement": bank_statement, "utility_bill": utility_bill}


def find_browser() -> str:
    for path in BROWSERS:
        if Path(path).exists():
            return path
    found = shutil.which("msedge") or shutil.which("chrome") or shutil.which("google-chrome")
    if found:
        return found
    sys.exit("No Edge or Chrome found to render the documents.")


def main() -> None:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    browser = find_browser()
    for name, build in DOCUMENTS.items():
        markup, height = build()
        source = SAMPLES / f"{name}.html"
        source.write_text(markup, encoding="utf-8")
        target = SAMPLES / f"{name}.png"
        subprocess.run(
            [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
             f"--window-size={VIEWPORT_WIDTH},{height}", f"--screenshot={target}", source.as_uri()],
            check=True, capture_output=True, timeout=120,
        )
        layout = measure_boxes(browser, source, height)
        (SAMPLES / f"{name}.boxes.json").write_text(json.dumps(layout, indent=1), encoding="utf-8")
        if name == "bank_statement":
            pdf = SAMPLES / "bank_statement.pdf"
            subprocess.run(
                [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", source.as_uri()],
                check=True, capture_output=True, timeout=120,
            )
            print(f"wrote {pdf.name} ({pdf.stat().st_size // 1024} KB), a digital PDF with a text layer")
        print(f"wrote {target.name} ({target.stat().st_size // 1024} KB), {len(layout['fields'])} field boxes, {len(layout['rows'])} row boxes")


if __name__ == "__main__":
    main()

"""
Mortgage Document Generator
Generates all required mortgage broker documents as PDFs and Word documents
"""

import os
import io
from datetime import datetime
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


class MortgageDocumentGenerator:
    """Generates all required mortgage broker documents"""

    def __init__(self, output_dir: str = "/app/generated_docs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_all_documents(self, app_data) -> list:
        """Generate all required documents and return list of file info"""
        documents = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = app_data.borrower_name.replace(" ", "_")
        prefix = f"{safe_name}_{timestamp}"

        doc_generators = [
            ("urla_1003", "Uniform Residential Loan Application (1003)", self._generate_urla_1003),
            ("good_faith_estimate", "Loan Estimate / Good Faith Estimate", self._generate_good_faith_estimate),
            ("borrower_authorization", "Borrower Authorization Form", self._generate_borrower_authorization),
            ("privacy_notice", "Privacy Notice", self._generate_privacy_notice),
            ("credit_authorization", "Credit Authorization", self._generate_credit_authorization),
            ("income_verification", "Income & Asset Summary", self._generate_income_verification),
        ]

        for doc_id, doc_name, generator_fn in doc_generators:
            filename = f"{prefix}_{doc_id}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            try:
                generator_fn(app_data, filepath)
                documents.append({
                    "id": doc_id,
                    "name": doc_name,
                    "filename": filename,
                    "filepath": filepath,
                    "generated": True
                })
            except Exception as e:
                documents.append({
                    "id": doc_id,
                    "name": doc_name,
                    "filename": filename,
                    "generated": False,
                    "error": str(e)
                })

        return documents

    def _get_styles(self):
        """Create document styles"""
        styles = getSampleStyleSheet()
        custom = {
            "title": ParagraphStyle("DocTitle", parent=styles["Normal"],
                fontSize=16, fontName="Helvetica-Bold",
                alignment=TA_CENTER, spaceAfter=6),
            "subtitle": ParagraphStyle("DocSubtitle", parent=styles["Normal"],
                fontSize=11, fontName="Helvetica",
                alignment=TA_CENTER, spaceAfter=12, textColor=colors.HexColor("#555555")),
            "section_header": ParagraphStyle("SectionHeader", parent=styles["Normal"],
                fontSize=11, fontName="Helvetica-Bold",
                textColor=colors.HexColor("#1a3a5c"),
                spaceBefore=12, spaceAfter=4,
                borderPadding=(4, 0, 4, 0)),
            "field_label": ParagraphStyle("FieldLabel", parent=styles["Normal"],
                fontSize=8, fontName="Helvetica-Bold",
                textColor=colors.HexColor("#666666"), spaceAfter=0),
            "field_value": ParagraphStyle("FieldValue", parent=styles["Normal"],
                fontSize=10, fontName="Helvetica", spaceAfter=6),
            "body": ParagraphStyle("Body", parent=styles["Normal"],
                fontSize=9, fontName="Helvetica",
                leading=14, spaceAfter=6),
            "footer": ParagraphStyle("Footer", parent=styles["Normal"],
                fontSize=7, fontName="Helvetica",
                textColor=colors.HexColor("#888888"),
                alignment=TA_CENTER),
        }
        return custom

    def _header_table(self, doc_name: str, doc_number: str = ""):
        """Create standardized header for all documents"""
        header_data = [
            [Paragraph(f"<b>MORTGAGE BROKER SERVICES</b>", ParagraphStyle("h",
                fontSize=14, fontName="Helvetica-Bold",
                textColor=colors.HexColor("#1a3a5c"))),
             Paragraph(f"<b>{doc_name}</b>", ParagraphStyle("h2",
                fontSize=12, fontName="Helvetica-Bold",
                alignment=TA_RIGHT, textColor=colors.HexColor("#1a3a5c")))],
            [Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", ParagraphStyle("sub",
                fontSize=9, fontName="Helvetica", textColor=colors.grey)),
             Paragraph(f"Form {doc_number}" if doc_number else "", ParagraphStyle("sub",
                fontSize=9, fontName="Helvetica",
                alignment=TA_RIGHT, textColor=colors.grey))]
        ]
        t = Table(header_data, colWidths=[3.75*inch, 3.75*inch])
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 1), (-1, 1), 1.5, colors.HexColor("#1a3a5c")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return t

    def _field_row(self, fields: list, col_widths: list = None) -> Table:
        """Create a row of labeled fields"""
        styles = self._get_styles()
        num_cols = len(fields)
        if not col_widths:
            col_widths = [7.5*inch / num_cols] * num_cols

        data = [[Paragraph(f[0], styles["field_label"]) for f in fields],
                [Paragraph(str(f[1]) if f[1] else "___________________", styles["field_value"]) for f in fields]]

        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 1), (-1, 1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    def _section_header(self, title: str, number: str = "") -> list:
        """Return flowables for a section header"""
        style = ParagraphStyle("sh", fontSize=10, fontName="Helvetica-Bold",
            textColor=colors.white, backColor=colors.HexColor("#1a3a5c"),
            leftIndent=6, rightIndent=6, spaceBefore=10, spaceAfter=4,
            borderPadding=(4, 6, 4, 6))
        label = f"SECTION {number}: {title.upper()}" if number else title.upper()
        return [Paragraph(label, style), Spacer(1, 4)]

    def _fmt_currency(self, value) -> str:
        """Format a value as currency"""
        try:
            return f"${float(value):,.2f}" if value else "N/A"
        except (ValueError, TypeError):
            return str(value) if value else "N/A"

    def _fmt(self, value, default="N/A") -> str:
        return str(value) if value else default

    # -------------------------------------------------------------------------
    # DOCUMENT 1: Uniform Residential Loan Application (1003)
    # -------------------------------------------------------------------------
    def _generate_urla_1003(self, app_data, filepath: str):
        doc = SimpleDocTemplate(filepath, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []
        p = app_data.personal
        e = app_data.employment
        a = app_data.assets
        l = app_data.liabilities
        prop = app_data.property_info
        lp = app_data.loan_preferences

        story.append(self._header_table("Uniform Residential Loan Application", "1003"))
        story.append(Spacer(1, 8))

        # Section I - Loan Type
        story.extend(self._section_header("Type of Mortgage and Terms of Loan", "I"))
        story.append(self._field_row([
            ("MORTGAGE APPLIED FOR", lp.get("loan_type", "")),
            ("LOAN AMOUNT", self._fmt_currency(prop.get("loan_amount"))),
            ("INTEREST RATE", lp.get("rate_type", "Fixed")),
            ("LOAN TERM (YEARS)", lp.get("loan_term", "")),
        ]))
        story.append(self._field_row([
            ("AMORTIZATION TYPE", lp.get("rate_type", "Fixed Rate")),
            ("LOAN PURPOSE", prop.get("loan_purpose", "")),
            ("PROPERTY USE", prop.get("property_use", "")),
        ]))
        story.append(Spacer(1, 6))

        # Section II - Property
        story.extend(self._section_header("Property Information and Purpose of Loan", "II"))
        story.append(self._field_row([
            ("PROPERTY ADDRESS", prop.get("property_address", "")),
            ("NO. OF UNITS", "1"),
        ], [5.5*inch, 2*inch]))
        story.append(self._field_row([
            ("PROPERTY TYPE", prop.get("property_type", "")),
            ("YEAR BUILT", prop.get("year_built", "")),
            ("PURCHASE PRICE", self._fmt_currency(prop.get("purchase_price"))),
        ]))
        story.append(Spacer(1, 6))

        # Section III - Borrower Info
        story.extend(self._section_header("Borrower Information", "III"))
        story.append(self._field_row([
            ("BORROWER'S NAME (FIRST/MI/LAST)", app_data.borrower_name),
            ("SOCIAL SECURITY NUMBER", p.get("ssn", "")),
            ("DATE OF BIRTH", p.get("dob", "")),
        ]))
        story.append(self._field_row([
            ("HOME PHONE", p.get("phone", "")),
            ("WORK PHONE", p.get("work_phone", "")),
            ("EMAIL", p.get("email", "")),
        ]))
        story.append(self._field_row([
            ("MARITAL STATUS", p.get("marital_status", "")),
            ("DEPENDENTS (NUMBER)", str(p.get("dependents", 0))),
            ("CITIZENSHIP", "US Citizen" if p.get("us_citizen") else p.get("visa_type", "")),
        ]))
        story.append(self._field_row([
            ("PRESENT ADDRESS (STREET, CITY, STATE, ZIP)", p.get("current_address", "")),
            ("OWN / RENT", p.get("own_or_rent", "")),
            ("NO. OF YEARS", str(p.get("years_at_address", ""))),
        ], [4.5*inch, 1.5*inch, 1.5*inch]))

        if p.get("previous_address"):
            story.append(self._field_row([
                ("FORMER ADDRESS (IF LESS THAN 2 YEARS)", p.get("previous_address", "")),
            ]))
        story.append(Spacer(1, 6))

        # Section IV - Employment
        story.extend(self._section_header("Employment Information", "IV"))
        story.append(self._field_row([
            ("NAME & ADDRESS OF EMPLOYER", e.get("employer_name", "") + " | " + e.get("employer_address", "")),
            ("SELF-EMPLOYED", "Yes" if e.get("self_employed") else "No"),
            ("DATES (FROM-TO)", e.get("employment_start", "") + " - Present"),
        ], [4*inch, 1.5*inch, 2*inch]))
        story.append(self._field_row([
            ("POSITION / TITLE", e.get("job_title", "")),
            ("YRS IN PROFESSION", str(e.get("years_in_profession", ""))),
            ("BASE MONTHLY INCOME", self._fmt_currency(e.get("base_monthly_income"))),
        ]))
        story.append(Spacer(1, 6))

        # Section V - Monthly Income
        story.extend(self._section_header("Monthly Income and Combined Housing Expense Information", "V"))
        income_data = [
            ["INCOME", "BORROWER", "COMBINED"],
            ["Base Employment Income*", self._fmt_currency(e.get("base_monthly_income")), self._fmt_currency(e.get("base_monthly_income"))],
            ["Overtime", self._fmt_currency(e.get("overtime_monthly", 0)), self._fmt_currency(e.get("overtime_monthly", 0))],
            ["Bonuses", self._fmt_currency(e.get("bonus_monthly", 0)), self._fmt_currency(e.get("bonus_monthly", 0))],
            ["Commissions", self._fmt_currency(e.get("commission_monthly", 0)), ""],
            ["Dividends/Interest", self._fmt_currency(a.get("investment_income", 0)), ""],
            ["Net Rental Income", self._fmt_currency(e.get("rental_income", 0)), ""],
            ["Other", self._fmt_currency(e.get("other_income", 0)), ""],
            ["TOTAL", self._fmt_currency(app_data.monthly_income), self._fmt_currency(app_data.monthly_income)],
        ]
        income_table = Table(income_data, colWidths=[3.5*inch, 2*inch, 2*inch])
        income_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0f8")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(income_table)
        story.append(Spacer(1, 6))

        # Section VI - Assets
        story.extend(self._section_header("Assets and Liabilities", "VI"))
        assets_data = [
            ["ASSETS", "CASH/MARKET VALUE"],
            ["Checking Account(s)", self._fmt_currency(a.get("checking_balance"))],
            ["Savings Account(s)", self._fmt_currency(a.get("savings_balance"))],
            ["Retirement Accounts (401k/IRA)", self._fmt_currency(a.get("retirement_balance"))],
            ["Stocks / Bonds", self._fmt_currency(a.get("investments"))],
            ["Real Estate Owned", self._fmt_currency(a.get("real_estate_value"))],
            ["Other Assets", self._fmt_currency(a.get("other_assets"))],
            ["TOTAL ASSETS", self._fmt_currency(
                sum(filter(None, [
                    _try_float(a.get("checking_balance")),
                    _try_float(a.get("savings_balance")),
                    _try_float(a.get("retirement_balance")),
                    _try_float(a.get("investments")),
                    _try_float(a.get("real_estate_value")),
                    _try_float(a.get("other_assets")),
                ]))
            )],
        ]
        liabilities_data = [
            ["LIABILITIES", "MONTHLY PAYMENT", "UNPAID BALANCE"],
            ["Rent Payment", self._fmt_currency(l.get("monthly_rent")), "N/A"],
            ["Auto Loan(s)", self._fmt_currency(l.get("car_payment")), self._fmt_currency(l.get("car_balance"))],
            ["Student Loans", self._fmt_currency(l.get("student_loan_payment")), self._fmt_currency(l.get("student_loan_balance"))],
            ["Credit Cards", self._fmt_currency(l.get("credit_card_minimum")), self._fmt_currency(l.get("credit_card_balance"))],
            ["Other Obligations", self._fmt_currency(l.get("other_monthly_debt")), ""],
            ["TOTAL MONTHLY DEBTS", self._fmt_currency(app_data.total_monthly_debt), ""],
        ]

        a_table = Table(assets_data, colWidths=[3.5*inch, 3.75*inch])
        a_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5f8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0f8")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))

        l_table = Table(liabilities_data, colWidths=[2.5*inch, 1.75*inch, 1.75*inch])
        l_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5f8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0f8")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))

        story.append(a_table)
        story.append(Spacer(1, 6))
        story.append(l_table)
        story.append(Spacer(1, 6))

        # Section VII - Details
        story.extend(self._section_header("Details of Transaction", "VII"))
        dti = f"{app_data.dti_ratio:.1f}%"
        ltv = f"{app_data.ltv_ratio:.1f}%"
        trans_data = [
            ["Purchase Price", self._fmt_currency(prop.get("purchase_price")),
             "Down Payment", self._fmt_currency(prop.get("down_payment"))],
            ["Loan Amount", self._fmt_currency(prop.get("loan_amount")),
             "LTV Ratio", ltv],
            ["Estimated Closing Costs", "TBD", "DTI Ratio", dti],
        ]
        trans_table = Table(trans_data, colWidths=[2*inch, 2*inch, 2*inch, 1.5*inch])
        trans_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f5fa")),
        ]))
        story.append(trans_table)
        story.append(Spacer(1, 6))

        # Section VIII - Declarations
        story.extend(self._section_header("Declarations", "VIII"))
        declarations = [
            ("a.", "Are there any outstanding judgments against you?", l.get("judgments", "No")),
            ("b.", "Have you been declared bankrupt within the past 7 years?", l.get("bankruptcy", "No")),
            ("c.", "Have you had property foreclosed upon in the past 7 years?", l.get("foreclosure", "No")),
            ("d.", "Are you a party to a lawsuit?", l.get("lawsuit", "No")),
            ("e.", "Have you directly or indirectly been obligated on any loan which resulted in foreclosure or judgment?", "No"),
            ("f.", "Are you presently delinquent or in default on any Federal debt or any other loan?", l.get("federal_debt_delinquent", "No")),
        ]
        decl_data = [[item[0], item[1], item[2]] for item in declarations]
        decl_table = Table(decl_data, colWidths=[0.4*inch, 6.1*inch, 1*inch])
        decl_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
        ]))
        story.append(decl_table)
        story.append(Spacer(1, 12))

        # Signature Block
        sig_style = ParagraphStyle("sig", fontSize=8, fontName="Helvetica")
        sig_data = [
            [Paragraph("X ___________________________________________", sig_style),
             Paragraph("X ___________________________________________", sig_style)],
            [Paragraph("Borrower Signature", sig_style),
             Paragraph("Date", sig_style)],
        ]
        sig_table = Table(sig_data, colWidths=[5*inch, 2.5*inch])
        sig_table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(sig_table)

        story.append(Spacer(1, 8))
        footer_style = ParagraphStyle("footer", fontSize=7, fontName="Helvetica",
            textColor=colors.grey, alignment=TA_CENTER)
        story.append(Paragraph(
            "Fannie Mae Form 1003 | This application is designed to be completed by the applicant with the lender's assistance.",
            footer_style))

        doc.build(story)

    # -------------------------------------------------------------------------
    # DOCUMENT 2: Good Faith Estimate / Loan Estimate
    # -------------------------------------------------------------------------
    def _generate_good_faith_estimate(self, app_data, filepath: str):
        doc = SimpleDocTemplate(filepath, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []
        prop = app_data.property_info
        lp = app_data.loan_preferences
        loan_amount = app_data.loan_amount

        story.append(self._header_table("Loan Estimate / Good Faith Estimate"))
        story.append(Spacer(1, 8))

        # Loan Terms Box
        story.extend(self._section_header("Loan Terms"))
        story.append(self._field_row([
            ("LOAN AMOUNT", self._fmt_currency(loan_amount)),
            ("INTEREST RATE", "Est. " + str(lp.get("rate_type", "Fixed"))),
            ("LOAN TERM", str(lp.get("loan_term", "30")) + " Years"),
            ("LOAN TYPE", lp.get("loan_type", "")),
        ]))
        story.append(Spacer(1, 6))

        # Projected Payments
        story.extend(self._section_header("Projected Payments"))
        # Rough estimate calculations
        rate = 0.07  # 7% assumed rate
        term = int(lp.get("loan_term", 30)) * 12
        if loan_amount > 0 and term > 0:
            monthly_rate = rate / 12
            pi = loan_amount * (monthly_rate * (1 + monthly_rate)**term) / ((1 + monthly_rate)**term - 1)
            taxes_insurance = loan_amount * 0.015 / 12  # rough estimate
            total_payment = pi + taxes_insurance
        else:
            pi = taxes_insurance = total_payment = 0

        payments_data = [
            ["", "YEAR 1 - 30"],
            ["Principal & Interest", self._fmt_currency(pi)],
            ["Estimated Escrow (Taxes & Insurance)", self._fmt_currency(taxes_insurance)],
            ["Estimated Total Monthly Payment", self._fmt_currency(total_payment)],
        ]
        pay_table = Table(payments_data, colWidths=[4.5*inch, 3*inch])
        pay_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0f8")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(pay_table)
        story.append(Spacer(1, 6))

        # Closing Cost Details
        story.extend(self._section_header("Closing Cost Details"))

        # Section A - Origination Charges
        closing_sections = [
            ("A. ORIGINATION CHARGES", [
                ("Origination Fee (1%)", loan_amount * 0.01),
                ("Underwriting Fee", 995),
                ("Processing Fee", 495),
            ]),
            ("B. SERVICES YOU CANNOT SHOP FOR", [
                ("Appraisal Fee", 550),
                ("Credit Report", 35),
                ("Flood Certification", 12),
                ("Tax Monitoring", 65),
                ("Title – Lender's Title Insurance", loan_amount * 0.005),
            ]),
            ("C. SERVICES YOU CAN SHOP FOR", [
                ("Settlement / Closing Fee", 495),
                ("Title – Owner's Title Insurance (optional)", loan_amount * 0.003),
            ]),
            ("E. TAXES AND OTHER GOVERNMENT FEES", [
                ("Recording Fees", 150),
                ("Transfer Taxes", loan_amount * 0.002),
            ]),
            ("F. PREPAIDS", [
                ("Homeowner's Insurance (12 mo.)", loan_amount * 0.006),
                ("Mortgage Insurance Premium", 0),
                ("Prepaid Interest (15 days est.)", loan_amount * rate / 365 * 15),
                ("Property Taxes (6 mo. escrow)", loan_amount * 0.012 / 2),
            ]),
        ]

        total_closing = 0
        for section_name, items in closing_sections:
            sec_data = [[section_name, ""]]
            sec_total = sum(v for _, v in items)
            total_closing += sec_total
            for name, val in items:
                sec_data.append([f"  {name}", self._fmt_currency(val)])
            sec_data.append([f"  {section_name.split('.')[0]} Subtotal", self._fmt_currency(sec_total)])

            sec_table = Table(sec_data, colWidths=[5.5*inch, 2*inch])
            sec_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3d7ab5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f0f5fa")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(sec_table)
            story.append(Spacer(1, 3))

        # Total Closing Costs
        total_data = [["TOTAL ESTIMATED CLOSING COSTS", self._fmt_currency(total_closing)]]
        total_table = Table(total_data, colWidths=[5.5*inch, 2*inch])
        total_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(Spacer(1, 4))
        story.append(total_table)
        story.append(Spacer(1, 8))

        # Closing Disclosure Summary
        story.extend(self._section_header("Cash to Close Summary"))
        cash_data = [
            ["Down Payment / Funds from Borrower", self._fmt_currency(prop.get("down_payment"))],
            ["Deposit (earnest money)", "TBD"],
            ["Funds for Borrower", "$0.00"],
            ["Seller Credits", "$0.00"],
            ["Adjustments and Other Credits", "$0.00"],
            ["ESTIMATED CASH TO CLOSE", self._fmt_currency(
                _try_float(prop.get("down_payment")) + total_closing
            )],
        ]
        cash_table = Table(cash_data, colWidths=[5.5*inch, 2*inch])
        cash_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0f8")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(cash_table)

        story.append(Spacer(1, 12))
        disclaimer_style = ParagraphStyle("disc", fontSize=7, fontName="Helvetica",
            textColor=colors.grey, leading=10)
        story.append(Paragraph(
            "* This is an estimate only. Actual costs may vary. Interest rates and fees are estimates based on current market conditions. "
            "This Loan Estimate expires 10 business days from the date shown above. All estimates are subject to change until a Closing Disclosure is issued.",
            disclaimer_style))

        doc.build(story)

    # -------------------------------------------------------------------------
    # DOCUMENT 3: Borrower Authorization
    # -------------------------------------------------------------------------
    def _generate_borrower_authorization(self, app_data, filepath: str):
        doc = SimpleDocTemplate(filepath, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []

        story.append(self._header_table("Borrower Authorization Form"))
        story.append(Spacer(1, 12))

        body_style = ParagraphStyle("body", fontSize=10, fontName="Helvetica",
            leading=16, spaceAfter=10)
        bold_style = ParagraphStyle("bold", fontSize=10, fontName="Helvetica-Bold",
            leading=16, spaceAfter=10)

        story.append(Paragraph("AUTHORIZATION TO RELEASE INFORMATION", bold_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"I/We, <b>{app_data.borrower_name}</b>, hereby authorize Mortgage Broker Services and its agents, "
            "successors, and assigns to obtain any information they may require in connection with a mortgage loan "
            "application for the property described in this application.", body_style))

        story.append(Paragraph(
            "I/We authorize you to release information about my/our mortgage application to:",
            body_style))

        items = [
            "Credit Bureaus and Credit Reporting Agencies",
            "Employers (for income/employment verification)",
            "Accountants or Tax Return Preparers",
            "Depository Institutions (Banks, Credit Unions, etc.)",
            "Investment Account Custodians",
            "Other mortgage lenders or investors",
            "Federal, state, and local governments or agencies",
        ]
        for item in items:
            story.append(Paragraph(f"  • {item}", body_style))

        story.append(Spacer(1, 8))
        story.append(Paragraph(
            "This authorization is valid for 120 days from the date signed and may be revoked at any time by "
            "written notification to Mortgage Broker Services. A photocopy or fax of this authorization shall be "
            "as valid as the original.", body_style))

        story.append(Spacer(1, 8))
        story.append(Paragraph("BORROWER INFORMATION:", bold_style))
        story.append(self._field_row([
            ("FULL NAME", app_data.borrower_name),
            ("DATE OF BIRTH", app_data.personal.get("dob", "")),
            ("SOCIAL SECURITY #", app_data.personal.get("ssn", "")),
        ]))
        story.append(self._field_row([
            ("CURRENT ADDRESS", app_data.personal.get("current_address", "")),
        ]))

        story.append(Spacer(1, 20))
        sig_style = ParagraphStyle("sig", fontSize=9, fontName="Helvetica")
        sig_data = [
            ["X _______________________________________________", "________________"],
            ["Borrower Signature", "Date"],
            ["", ""],
            ["X _______________________________________________", "________________"],
            ["Print Name", ""],
        ]
        sig_table = Table(sig_data, colWidths=[5.5*inch, 2*inch])
        sig_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(sig_table)

        doc.build(story)

    # -------------------------------------------------------------------------
    # DOCUMENT 4: Privacy Notice
    # -------------------------------------------------------------------------
    def _generate_privacy_notice(self, app_data, filepath: str):
        doc = SimpleDocTemplate(filepath, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []

        story.append(self._header_table("Privacy Notice (GLBA)"))
        story.append(Spacer(1, 12))

        body = ParagraphStyle("body", fontSize=9, fontName="Helvetica",
            leading=14, spaceAfter=8)
        header = ParagraphStyle("header", fontSize=11, fontName="Helvetica-Bold",
            spaceAfter=6, spaceBefore=10, textColor=colors.HexColor("#1a3a5c"))

        story.append(Paragraph("WHAT DOES MORTGAGE BROKER SERVICES DO WITH YOUR PERSONAL INFORMATION?", header))

        # Facts table
        facts_data = [
            ["WHY?", "Financial companies choose how they share your personal information. Federal law gives consumers the right to limit some but not all sharing. Federal law also requires us to tell you how we collect, share, and protect your personal information. Please read this notice carefully to understand what we do."],
            ["WHAT?", "The types of personal information we collect and share depend on the product or service you have with us. This information can include: Social Security number and income, Account balances and payment history, Credit history and credit scores."],
            ["HOW?", "All financial companies need to share customers' personal information to run their everyday business. In the section below, we list the reasons financial companies can share their customers' personal information; the reasons Mortgage Broker Services chooses to share; and whether you can limit this sharing."],
        ]
        facts_table = Table(facts_data, colWidths=[1.2*inch, 6.3*inch])
        facts_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(facts_table)
        story.append(Spacer(1, 10))

        story.append(Paragraph("REASONS WE CAN SHARE YOUR PERSONAL INFORMATION", header))
        sharing_data = [
            ["REASONS WE CAN SHARE YOUR PERSONAL INFORMATION", "DOES MORTGAGE BROKER SERVICES SHARE?", "CAN YOU LIMIT THIS SHARING?"],
            ["For our everyday business purposes — such as to process your transactions, maintain your account(s), respond to court orders and legal investigations, or report to credit bureaus", "Yes", "No"],
            ["For our marketing purposes — to offer our products and services to you", "Yes", "No"],
            ["For joint marketing with other financial companies", "No", "We don't share"],
            ["For our affiliates' everyday business purposes — information about your transactions and experiences", "No", "We don't share"],
            ["For our affiliates' everyday business purposes — information about your creditworthiness", "No", "We don't share"],
            ["For nonaffiliates to market to you", "No", "We don't share"],
        ]
        sharing_table = Table(sharing_data, colWidths=[3.5*inch, 2*inch, 2*inch])
        sharing_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fc")]),
        ]))
        story.append(sharing_table)
        story.append(Spacer(1, 10))

        story.append(Paragraph("WHO WE ARE", header))
        story.append(Paragraph("<b>Who is providing this notice?</b> Mortgage Broker Services, a licensed mortgage broker.", body))

        story.append(Paragraph("WHAT WE DO", header))
        protect_data = [
            ["How does Mortgage Broker Services protect my personal information?",
             "To protect your personal information from unauthorized access and use, we use security measures that comply with federal law. These measures include computer safeguards and secured files and buildings."],
            ["How does Mortgage Broker Services collect my personal information?",
             "We collect your personal information, for example, when you apply for a loan, give us your income information, provide employment information, show your driver's license, give us your contact information."],
            ["Why can't I limit all sharing?",
             "Federal law gives you the right to limit only sharing for affiliates' everyday business purposes, affiliates from using your information to market to you, sharing for nonaffiliates to market to you."],
        ]
        protect_table = Table(protect_data, colWidths=[3*inch, 4.5*inch])
        protect_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f5f8fc"), colors.white]),
        ]))
        story.append(protect_table)

        story.append(Spacer(1, 12))
        story.append(Paragraph(
            f"Prepared for: <b>{app_data.borrower_name}</b> | Date: {datetime.now().strftime('%B %d, %Y')}",
            body))

        doc.build(story)

    # -------------------------------------------------------------------------
    # DOCUMENT 5: Credit Authorization
    # -------------------------------------------------------------------------
    def _generate_credit_authorization(self, app_data, filepath: str):
        doc = SimpleDocTemplate(filepath, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []

        story.append(self._header_table("Credit Authorization"))
        story.append(Spacer(1, 12))

        body = ParagraphStyle("body", fontSize=10, fontName="Helvetica", leading=16, spaceAfter=10)
        bold = ParagraphStyle("bold", fontSize=10, fontName="Helvetica-Bold", spaceAfter=6)

        story.append(Paragraph("CREDIT PULL AUTHORIZATION AND CONSENT", bold))
        story.append(Spacer(1, 6))

        story.append(Paragraph(
            f'I/We, <b>{app_data.borrower_name}</b> ("Applicant"), hereby authorize Mortgage Broker Services '
            "and its lending partners to access my/our consumer credit report(s) from one or more of the "
            "three major credit bureaus (Equifax, Experian, and TransUnion) for the purpose of evaluating "
            "my/our mortgage loan application.", body))

        story.append(Paragraph("I/We understand and agree that:", body))

        consents = [
            "1. This authorization is for a HARD credit inquiry, which may affect my credit score.",
            "2. The credit report will be used solely for evaluating my mortgage loan application.",
            "3. This authorization is valid for 120 days from the date signed.",
            "4. I may revoke this authorization in writing, but doing so will halt processing of my application.",
            "5. The credit report information will be protected in accordance with applicable law.",
            "6. My credit information may be shared with potential investors and secondary market purchasers.",
        ]
        for consent in consents:
            story.append(Paragraph(consent, body))

        story.append(Spacer(1, 10))
        story.append(Paragraph("APPLICANT INFORMATION:", bold))
        story.append(self._field_row([
            ("FULL LEGAL NAME", app_data.borrower_name),
            ("DATE OF BIRTH", app_data.personal.get("dob", "")),
        ]))
        story.append(self._field_row([
            ("SOCIAL SECURITY NUMBER", app_data.personal.get("ssn", "")),
            ("CURRENT PHONE", app_data.personal.get("phone", "")),
        ]))
        story.append(self._field_row([
            ("CURRENT ADDRESS", app_data.personal.get("current_address", "")),
        ]))

        story.append(Spacer(1, 20))
        story.append(Paragraph(
            "By signing below, I certify that the above information is true and correct, and I authorize the credit "
            "inquiry described above.", body))

        story.append(Spacer(1, 16))
        sig_data = [
            ["X _______________________________________________", "________________"],
            ["Applicant Signature", "Date"],
        ]
        sig_table = Table(sig_data, colWidths=[5.5*inch, 2*inch])
        sig_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(sig_table)

        doc.build(story)

    # -------------------------------------------------------------------------
    # DOCUMENT 6: Income & Asset Verification Summary
    # -------------------------------------------------------------------------
    def _generate_income_verification(self, app_data, filepath: str):
        doc = SimpleDocTemplate(filepath, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []
        e = app_data.employment
        a = app_data.assets
        l = app_data.liabilities

        story.append(self._header_table("Income & Asset Verification Summary"))
        story.append(Spacer(1, 8))

        # Income Summary
        story.extend(self._section_header("Income Summary"))
        income_data = [
            ["INCOME SOURCE", "MONTHLY AMOUNT", "ANNUAL AMOUNT"],
            ["Base Employment Income", self._fmt_currency(e.get("base_monthly_income")),
             self._fmt_currency(_try_float(e.get("base_monthly_income")) * 12)],
            ["Overtime Income", self._fmt_currency(e.get("overtime_monthly", 0)),
             self._fmt_currency(_try_float(e.get("overtime_monthly", 0)) * 12)],
            ["Bonus/Commission Income", self._fmt_currency(e.get("bonus_monthly", 0)),
             self._fmt_currency(_try_float(e.get("bonus_monthly", 0)) * 12)],
            ["Rental Income", self._fmt_currency(e.get("rental_income", 0)),
             self._fmt_currency(_try_float(e.get("rental_income", 0)) * 12)],
            ["Other Income", self._fmt_currency(e.get("other_income", 0)),
             self._fmt_currency(_try_float(e.get("other_income", 0)) * 12)],
            ["TOTAL GROSS INCOME", self._fmt_currency(app_data.monthly_income),
             self._fmt_currency(app_data.monthly_income * 12)],
        ]
        inc_table = Table(income_data, colWidths=[3.5*inch, 2*inch, 2*inch])
        inc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0f8")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(inc_table)
        story.append(Spacer(1, 8))

        # Asset Summary
        story.extend(self._section_header("Asset Summary"))
        checking = _try_float(a.get("checking_balance"))
        savings = _try_float(a.get("savings_balance"))
        retirement = _try_float(a.get("retirement_balance"))
        investments = _try_float(a.get("investments"))
        real_estate = _try_float(a.get("real_estate_value"))
        other = _try_float(a.get("other_assets"))
        total_assets = checking + savings + retirement + investments + real_estate + other

        asset_data = [
            ["ASSET TYPE", "INSTITUTION / DESCRIPTION", "CURRENT VALUE"],
            ["Checking Account(s)", a.get("checking_institution", ""), self._fmt_currency(checking)],
            ["Savings Account(s)", a.get("savings_institution", ""), self._fmt_currency(savings)],
            ["Retirement (401k/IRA)", a.get("retirement_institution", ""), self._fmt_currency(retirement)],
            ["Stocks / Bonds", a.get("investment_broker", ""), self._fmt_currency(investments)],
            ["Real Estate", a.get("real_estate_address", ""), self._fmt_currency(real_estate)],
            ["Other Assets", a.get("other_asset_description", ""), self._fmt_currency(other)],
            ["TOTAL ASSETS", "", self._fmt_currency(total_assets)],
        ]
        asset_table = Table(asset_data, colWidths=[2.2*inch, 3.2*inch, 2.1*inch])
        asset_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0f8")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(asset_table)
        story.append(Spacer(1, 8))

        # DTI Analysis
        story.extend(self._section_header("Debt-to-Income (DTI) Analysis"))
        dti_data = [
            ["METRIC", "VALUE", "GUIDELINE", "STATUS"],
            ["Total Monthly Income", self._fmt_currency(app_data.monthly_income), "", ""],
            ["Total Monthly Debt", self._fmt_currency(app_data.total_monthly_debt), "", ""],
            ["Front-End DTI (housing only)", f"{((_try_float(l.get('proposed_mortgage', 0)) / max(app_data.monthly_income, 1)) * 100):.1f}%", "≤ 28%", ""],
            ["Back-End DTI (all debts)", f"{app_data.dti_ratio:.1f}%", "≤ 43%",
             "✓ PASS" if app_data.dti_ratio <= 43 else "✗ HIGH"],
            ["Loan-to-Value (LTV)", f"{app_data.ltv_ratio:.1f}%", "≤ 80% (no PMI)", ""],
        ]
        dti_table = Table(dti_data, colWidths=[2.5*inch, 1.75*inch, 1.75*inch, 1.5*inch])
        dti_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(dti_table)
        story.append(Spacer(1, 8))

        # Document Checklist
        story.extend(self._section_header("Required Documentation Checklist"))
        docs_needed = [
            ("Government-issued photo ID", True),
            ("Most recent 2 years W-2s", True),
            ("Most recent 30 days pay stubs (2)", True),
            ("Most recent 2 years Federal tax returns (all pages)", True),
            ("Most recent 2 months bank statements (all pages)", True),
            ("Most recent retirement/investment account statements", True),
            ("Self-employed: Business tax returns (2 years)", e.get("self_employed", False)),
            ("Self-employed: YTD Profit & Loss statement", e.get("self_employed", False)),
            ("Purchase agreement / sales contract", True),
            ("VA Certificate of Eligibility", app_data.loan_preferences.get("veteran", False)),
        ]
        checklist_data = [["DOCUMENT REQUIRED", "NEEDED"]]
        for doc_name, needed in docs_needed:
            if needed:
                checklist_data.append([doc_name, "☐ Pending"])
        docs_table = Table(checklist_data, colWidths=[6*inch, 1.5*inch])
        docs_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fc")]),
        ]))
        story.append(docs_table)

        doc.build(story)


def _try_float(value, default=0.0) -> float:
    """Safely convert a value to float"""
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default

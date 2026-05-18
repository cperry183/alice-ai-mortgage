"""
Rules engine compiling operational form sets for Federal, State (MA/NH),
Program-specific, Employment tracking, and Compliance/QC packages.
"""

FEDERAL_CORE_FORMS = [
    # 1. Borrower Intake & Initial Application Forms (Core Origination Package)
    {"form_id": "URLA_1003", "name": "Uniform Residential Loan Application (Form 1003)"},
    {"form_id": "DEMO_ADDENDUM", "name": "Demographic Information Addendum"},
    {"form_id": "CONTINUATION_SHEETS", "name": "URLA Continuation Sheets"},
    {"form_id": "CREDIT_AUTH", "name": "Initial Credit Report Authorization Form"},
    {"form_id": "EMP_VERIF_AUTH", "name": "Employment Verification Authorization"},
    {"form_id": "ASSET_VERIF_AUTH", "name": "Asset Verification Authorization"},
    {"form_id": "IRS_4506_C", "name": "Tax Return Authorization (IRS Form 4506-C)"},
    {"form_id": "SSA_CONSENT", "name": "Social Security Administration (SSA) Verification Consent"},
    {"form_id": "ESIGN_CONSENT", "name": "Borrower Consent to Electronic Communications & E-Sign"},
    {"form_id": "COUNSELING_DISC", "name": "Homeownership Counseling Disclosure & Local Provider List"},
    {"form_id": "IDENTITY_VERIF_FORM", "name": "Identity Verification Form (Photo ID Log)"},

    # 2. Federal TRID / CFPB Disclosures
    {"form_id": "LOAN_ESTIMATE", "name": "Loan Estimate (LE) Package"},
    {"form_id": "SERVICE_PROVIDER_LIST", "name": "Written List of Service Providers"},
    {"form_id": "INTENT_TO_PROCEED", "name": "Intent to Proceed Documentation & Acknowledgment"},
    {"form_id": "CLOSING_DISCLOSURE", "name": "Closing Disclosure (CD)"},
    {"form_id": "CD_RECEIPT_ACK", "name": "Closing Disclosure Receipt Acknowledgment"},
    {"form_id": "CASH_TO_CLOSE_WS", "name": "Cash-to-Close Balance Worksheet"},

    # 3. RESPA / Federal Mortgage Disclosures
    {"form_id": "AFBA_DISCLOSURE", "name": "Affiliated Business Arrangement Disclosure (AfBA)"},
    {"form_id": "RESPA_SERVICING", "name": "RESPA Servicing Disclosure & Transfer Statement"},
    {"form_id": "INITIAL_ESCROW_STMT", "name": "Initial Escrow Account Statement"},
    {"form_id": "PARTIAL_PAYMENT_POLICY", "name": "Partial Payment Policy Disclosure"},

    # 4. ECOA / Fair Lending Forms
    {"form_id": "ECOA_NOTICE", "name": "Equal Credit Opportunity Act (ECOA) Notice"},
    {"form_id": "ADVERSE_ACTION", "name": "Adverse Action Notice Framework"},
    {"form_id": "INCOMPLETE_APP_NOTICE", "name": "Notice of Incomplete Application (10-Day Letter)"},
    {"form_id": "FAIR_LENDING_NOTICE", "name": "Fair Lending Notice & HMDA Monitoring Addendum"},

    # 5. Privacy & Data Security Forms
    {"form_id": "GLBA_PRIVACY", "name": "Privacy Policy Notice (Gramm-Leach-Bliley Act)"},
    {"form_id": "INFO_SHARE_OPTOUT", "name": "Information Sharing Opt-Out Election Form"},
    {"form_id": "CYBER_SECURITY_DISC", "name": "Cybersecurity & Business Email Compromise Disclosure"},
    {"form_id": "WIRE_FRAUD_WARNING", "name": "Wire Fraud Warning & Verification Instructions"},

    # 6. Anti-Money Laundering / Fraud Forms
    {"form_id": "OFAC_SCREENING", "name": "OFAC Screening Certification"},
    {"form_id": "PATRIOT_ACT_CIP", "name": "Patriot Act / CIP Identity Verification Log"},
    {"form_id": "RED_FLAGS_CHECKLIST", "name": "Red Flags Compliance Review Checklist"},
    {"form_id": "FRAUD_ALERT_ACK", "name": "Fraud Alert Acknowledgment"},
    {"form_id": "IDENTITY_THEFT_PREV", "name": "Identity Theft Prevention Acknowledgment"},
    {"form_id": "OCCUPANCY_AFFIDAVIT", "name": "Occupancy Affidavit and Financial Status Certification"}
]

PROGRAM_SPECIFIC_FORMS = {
    "FHA": [
        # 11. Loan Program-Specific Forms — FHA
        {"form_id": "FHA_AMENDATORY", "name": "FHA Amendatory Clause"},
        {"form_id": "FHA_BORR_CERT", "name": "FHA Borrower Certification"},
        {"form_id": "CAIVRS_AUTHORIZATION", "name": "CAIVRS Authorization and Report"},
        {"form_id": "IDENTITY_OF_INTEREST", "name": "Identity of Interest Certification"}
    ],
    "VA": [
        # 11. Loan Program-Specific Forms — VA
        {"form_id": "VA_LOAN_COMPARISON", "name": "VA Loan Comparison Statement"},
        {"form_id": "VA_OCCUPANCY_CERT", "name": "VA Occupancy Certification"},
        {"form_id": "VA_COE_LOG", "name": "Certificate of Eligibility (COE) Verification"},
        {"form_id": "VA_RELATIVE_FORM", "name": "Nearest Living Relative Form"}
    ],
    "USDA": [
        # 11. Loan Program-Specific Forms — USDA
        {"form_id": "USDA_ELIGIBILITY", "name": "USDA Rural Housing Eligibility Forms"},
        {"form_id": "RURAL_HOUSING_CERT", "name": "Rural Housing Certification"}
    ],
    "JUMBO": [
        # 11. Loan Program-Specific Forms — Jumbo / Non-QM
        {"form_id": "ASSET_DEPLETION_WS", "name": "Asset Depletion Underwriting Worksheet"},
        {"form_id": "NON_QM_BANK_ANALYSIS", "name": "Non-QM Bank Statement Analysis Profile"},
        {"form_id": "DSCR_WORKSHEET", "name": "Debt Service Coverage Ratio (DSCR) Worksheet"},
        {"form_id": "INVESTOR_SPECIFIC_DISC", "name": "Investor-Specific Program Disclosures"}
    ],
    "CONVENTIONAL": [] # Relies entirely on Federal Core / Fannie / Freddie portfolios
}

STATE_SPECIFIC_FORMS = {
    "MA": [
        # 12. State-Specific Mortgage Broker Forms — Massachusetts (Division of Banks)
        {"form_id": "MA_BROKER_LIC_APP", "name": "Massachusetts Mortgage Broker License Application Reference"},
        {"form_id": "MA_BRANCH_REG", "name": "Massachusetts Division of Banks Branch Registration"},
        {"form_id": "MA_CALL_REPORTS", "name": "Massachusetts Mortgage Call Report Alignment Record"},
        {"form_id": "MA_SURETY_BOND", "name": "Massachusetts Surety Bond Status Verification Form"},
        {"form_id": "MA_LO_COMP_DISC", "name": "Massachusetts Disclosure of Loan Originator Compensation"},
        {"form_id": "MA_RIGHT_TO_CURE", "name": "Massachusetts Right to Cure Statutory Notices Framework"},
        {"form_id": "MA_FORECLOSURE_PREV", "name": "Massachusetts Foreclosure Prevention Notice"}
    ],
    "NH": [
        # 13. State-Specific Mortgage Broker Forms — New Hampshire (Banking Department)
        {"form_id": "NH_BANKER_BROKER_LIC", "name": "New Hampshire Mortgage Banker/Broker Licensing Validation"},
        {"form_id": "NH_BRANCH_LICENSE", "name": "New Hampshire Branch License Tracking Sheet"},
        {"form_id": "NH_LO_SPONSORSHIP", "name": "New Hampshire Loan Originator Sponsorship Verification Form"},
        {"form_id": "NH_SURETY_BOND_FILING", "name": "New Hampshire Surety Bond Filing Evidence"},
        {"form_id": "NH_STATE_ADDENDA", "name": "New Hampshire Banking Department State Disclosure Addenda"},
        {"form_id": "NH_CONSUMER_CREDIT", "name": "New Hampshire Consumer Credit Disclosures"}
    ],
    "NY": [
        # 13. State-Specific Mortgage Broker Forms — New York (Department of Financial Services)
        {"form_id": "NY_DFS_BROKER_DISC", "name": "New York Section 38(3) Mortgage Broker Fee Disclosure"},
        {"form_id": "NY_SUBPRIME_NOTICE", "name": "New York Banking Law Section 6-m Subprime Loan Notice"},
        {"form_id": "NY_HELOC_DISC", "name": "New York HELOC Terms & Right to Cancel Addendum"},
        {"form_id": "NY_PREPAYMENT_DISC", "name": "New York Prepayment Penalty Disclosure Statement"},
        {"form_id": "NY_ATTORNEY_SELECTION", "name": "New York Choice of Attorney Statutory Notice"}
    ],
    "CT": [
        # 13. State-Specific Mortgage Broker Forms — Connecticut (Department of Banking)
        {"form_id": "CT_BROKER_AGREEMENT", "name": "Connecticut Mortgage Broker Agreement & Fee Disclosure"},
        {"form_id": "CT_NMLS_DISPLAY", "name": "Connecticut NMLS Licensing Verification & ULI Log"},
        {"form_id": "CT_ABUSIVE_LOAN_NOTICE", "name": "Connecticut Abusive Home Loan Lending Practices Act Notice"},
        {"form_id": "CT_TILA_ADDENDUM", "name": "Connecticut Consumer Credit Cost Disclosure Addendum"}
    ]
}

EMPLOYMENT_SPECIFIC_FORMS = {
    "W2": [
        # 7. Income Verification Forms — Employed Borrowers
        {"form_id": "VOE_STANDARD", "name": "Verification of Employment (VOE) Request"},
        {"form_id": "PAYSTUB_CERT", "name": "Paystub Integrity & Continuity Certification"},
        {"form_id": "W2_COLLECTION_CHKLST", "name": "W-2 Collection Checklist"}
    ],
    "SELF_EMPLOYED": [
        # 7. Income Verification Forms — Self-Employed Borrowers
        {"form_id": "SE_PL_STATEMENT", "name": "Self-Employed Profit & Loss Statement Matrix"},
        {"form_id": "CPA_LETTER", "name": "Certified Public Accountant (CPA) Verification Letter"},
        {"form_id": "BUS_LICENSE_VERIF", "name": "Business License & Entity Status Verification"},
        {"form_id": "YTD_INCOME_STMT", "name": "Year-to-Date (YTD) Income Statement Summary"},
        {"form_id": "BUS_BANK_ANALYSIS", "name": "Business Bank Statement Analysis Worksheet"}
    ]
}

UNIVERSAL_PROCESSING_FORMS = [
    # 8. Asset Verification Forms
    {"form_id": "VOD_STANDARD", "name": "Verification of Deposit (VOD)"},
    {"form_id": "GIFT_LETTER", "name": "Executed Gift Letter Form"},
    {"form_id": "GIFT_FUND_DOCS", "name": "Gift Fund Trailing Documentation Checklist"},
    {"form_id": "LARGE_DEPOSIT_EXP", "name": "Large Deposit Written Explanation Letter"},
    {"form_id": "EARNEST_MONEY_VERIF", "name": "Earnest Money Deposit (EMD) Verification Form"},
    {"form_id": "ASSET_SOURCING_WS", "name": "Asset Sourcing Worksheet"},

    # 9. Credit & Liability Forms
    {"form_id": "CREDIT_EXP_LETTER", "name": "Credit Explanation Letter (General)"},
    {"form_id": "DEROGATORY_CREDIT_EXP", "name": "Derogatory Credit / Late Payment Explanation"},
    {"form_id": "BK_FORECLOSURE_EXP", "name": "Bankruptcy / Foreclosure Explanation & Discharge Tracking"},
    {"form_id": "STUDENT_LOAN_CERT", "name": "Student Loan Payment Plan Certification"},
    {"form_id": "UNDISCLOSED_DEBT_CERT", "name": "Undisclosed Debt Acknowledgment & Certification"},

    # 10. Property & Appraisal Forms
    {"form_id": "APPRAISAL_ORDER", "name": "Appraisal Order Form"},
    {"form_id": "APPRAISAL_DISCLOSURE", "name": "Appraisal Delivery Disclosure (Right to Receive Copy)"},
    {"form_id": "PROP_COND_CERT", "name": "Property Condition Certification Summary"},
    {"form_id": "HOI_VERIFICATION", "name": "Homeowners Insurance Verification & Binder Request"},
    {"form_id": "CONDO_QUESTIONNAIRE", "name": "HOA Condo Questionnaire (Full/Limited)"},
    {"form_id": "FLOOD_CERT_NOTICE", "name": "Flood Certification & Special Flood Hazard Area Notice"},

    # 14. Compliance & QC Forms (Internal Brokerage Compliance Package)
    {"form_id": "QC_AUDIT_CHECKLIST", "name": "Quality Control (QC) Pre-Submission Audit Checklist"},
    {"form_id": "PRE_FUNDING_REVIEW", "name": "Pre-Funding Regulatory Compliance Review"},
    {"form_id": "POST_CLOSING_AUDIT", "name": "Post-Closing Audit Tracking Form"},
    {"form_id": "ANTI_STEERING_CERT", "name": "Anti-Steering Loan Product Certification"},
    {"form_id": "LO_COMP_CERT", "name": "Loan Originator Compensation Attestation"},
    {"form_id": "COMPLIANCE_EXCEPTION_LOG", "name": "Compliance Exception Log Entry"},
    {"form_id": "RECORD_RETENTION_CHKLST", "name": "Federal/State Record Retention Checklist"},

    # 15. Closing & Funding Forms
    {"form_id": "CLOSING_INSTRUCTIONS", "name": "Closing Instructions to Escrow/Settlement Agent"},
    {"form_id": "FUNDING_AUTHORIZATION", "name": "Funding Authorization Criteria Matrix"},
    {"form_id": "WIRE_INSTRUCTIONS", "name": "Broker Wire Instructions Profile"},
    {"form_id": "NOTE_MORTGAGE_RIDERS", "name": "Closing Execution Forms Checklist (Note, Mortgage/Deed, Riders)"},
    {"form_id": "EO_AGREEMENT", "name": "Errors & Omissions (E&O) Compliance Agreement"},

    # 16. Secondary Market / Investor Forms
    {"form_id": "UNDERWRITING_SUM_1008", "name": "Fannie Mae/Freddie Mac Form 1008 Underwriting Summary"},
    {"form_id": "ULDD_DELIVERY_DATA", "name": "Uniform Loan Delivery Dataset (ULDD) Specification Log"},
    {"form_id": "AUS_FINDINGS_SUMMARY", "name": "Automated Underwriting System (AUS) Findings Log (DU/LPA)"},
    {"form_id": "INVESTOR_CERT_FORMS", "name": "Non-Agency Investor Certification Statements"},
    {"form_id": "CORRESPONDENT_PACKAGES", "name": "Delegated Correspondent Package QC Attestations"}
]


def generate_manifest(state_jurisdiction: str, loan_type: str, is_self_employed: bool) -> list:
    """
    Compiles a highly localized regulatory form inventory layout dynamically.
    Combines Federal, Regional State Laws, Investor Programs, Income Tracks, 
    Asset Underwriting, and Closing Verification logs into an indexable manifest.
    """
    # 1. Start with initial application, TRID, privacy, and federal core frameworks
    manifest = list(FEDERAL_CORE_FORMS)
    
    # 2. Inject State Jurisdiction Separation Framework
    normalized_state = str(state_jurisdiction).upper().strip()
    if normalized_state in STATE_SPECIFIC_FORMS:
        manifest.extend(STATE_SPECIFIC_FORMS[normalized_state])
        
    # 3. Inject Investor Programmatic Requirements
    normalized_loan = str(loan_type).upper().strip()
    if normalized_loan in PROGRAM_SPECIFIC_FORMS:
        manifest.extend(PROGRAM_SPECIFIC_FORMS[normalized_loan])
    else:
        # Fallback to Conventional tracking structural rules
        manifest.extend(PROGRAM_SPECIFIC_FORMS["CONVENTIONAL"])
        
    # 4. Inject Targeted Income-Verification Matrix Tracks
    if is_self_employed:
        manifest.extend(EMPLOYMENT_SPECIFIC_FORMS["SELF_EMPLOYED"])
    else:
        manifest.extend(EMPLOYMENT_SPECIFIC_FORMS["W2"])
        
    # 5. Append Universal Asset, Liability, Closing, and Secondary Market Log Bundles
    manifest.extend(UNIVERSAL_PROCESSING_FORMS)
    
    return manifest

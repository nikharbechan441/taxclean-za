#!/usr/bin/env python3
"""
TaxClean Automated SEO & AEO Guide Engine
Generates high-converting, AEO-structured South African accounting guides,
updates sitemap.xml, and triggers instant IndexNow pings.
Fully hardened per Senior Critic Audit (Nov 9, 2026).
"""

import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "website", "guides")
SITEMAP_PATH = os.path.join(os.path.dirname(__file__), "website", "sitemap.xml")
INDEXNOW_KEY = "e4c8f2b19a7d4e5f8b6a3c2d1e0f9a8b"
BASE_URL = "https://taxcleanza.com"

# Shared CSS and Layout Template
PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="{page_lang}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{meta_title}</title>
  <meta name="description" content="{meta_desc}" />
  <meta name="keywords" content="{meta_keywords}" />
  <meta name="robots" content="index, follow" />
  <meta name="geo.region" content="{geo_region}" />
  <meta name="geo.placename" content="{geo_placename}" />
  <link rel="canonical" href="{canonical_url}" />
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23061326'/%3E%3Ctext x='5' y='22' font-family='Inter,Arial,sans-serif' font-weight='800' font-size='15' fill='%23ffffff'%3ETC%3Ctspan fill='%2310b981'%3E.%3C/tspan%3E%3C/text%3E%3C/svg%3E" />
  <link rel="icon" href="/favicon.ico" sizes="any" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
  <link rel="help" type="text/plain" title="LLMs.txt AI Answer Engine Manifest" href="https://taxcleanza.com/llms.txt" />
  <link rel="help" type="text/plain" title="LLMs-Full.txt Complete AI Citation Reference" href="https://taxcleanza.com/llms-full.txt" />

  <!-- OpenGraph Metadata -->
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="TaxClean" />
  <meta property="og:locale" content="{og_locale}" />
  <meta property="og:url" content="{canonical_url}" />
  <meta property="og:title" content="{meta_title}" />
  <meta property="og:description" content="{meta_desc}" />
  <meta property="og:image" content="https://taxcleanza.com/og-banner.png" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{meta_title}" />
  <meta name="twitter:description" content="{meta_desc}" />
  <meta name="twitter:image" content="https://taxcleanza.com/og-banner.png" />

  <!-- AEO & JSON-LD Structured Data Schema -->
  <script type="application/ld+json">
{schema_json}
  </script>

  <style>
    :root {{
      --primary: #10b981;
      --primary-dark: #059669;
      --primary-light: #ecfdf5;
      --primary-border: #a7f3d0;
      --slate-950: #060c18;
      --slate-900: #090d16;
      --slate-800: #1e293b;
      --slate-700: #334155;
      --slate-600: #475569;
      --slate-500: #64748b;
      --slate-300: #cbd5e1;
      --slate-200: #e2e8f0;
      --slate-100: #f1f5f9;
      --slate-50: #f8fafc;
      --radius-sm: 8px;
      --radius-md: 12px;
      --radius-lg: 16px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      background: #f8fafc;
      line-height: 1.7;
      -webkit-font-smoothing: antialiased;
    }}
    nav {{
      background: var(--slate-900);
      padding: 16px 24px;
      border-bottom: 1px solid rgba(255,255,255,0.08);
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    nav .nav-wrap {{
      max-width: 960px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    nav .brand {{
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
      color: #fff;
      font-weight: 800;
      font-size: 18px;
    }}
    nav .brand span {{ color: var(--primary); }}
    nav .nav-cta {{
      background: var(--primary);
      color: #061326;
      font-weight: 700;
      font-size: 13.5px;
      padding: 8px 16px;
      border-radius: var(--radius-sm);
      text-decoration: none;
      transition: background 0.15s ease;
    }}
    nav .nav-cta:hover {{ background: #34d399; }}

    .breadcrumbs {{
      max-width: 960px;
      margin: 24px auto 0 auto;
      padding: 0 20px;
      font-size: 13px;
      color: var(--slate-500);
    }}
    .breadcrumbs a {{ color: var(--slate-600); text-decoration: none; }}
    .breadcrumbs a:hover {{ color: var(--primary-dark); }}
    .breadcrumbs span {{ margin: 0 6px; }}

    .main-container {{
      max-width: 960px;
      margin: 20px auto 60px auto;
      padding: 0 20px;
    }}
    .article-card {{
      background: #ffffff;
      border: 1px solid var(--slate-200);
      border-radius: var(--radius-lg);
      padding: 48px;
      box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
    }}
    .guide-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--primary-light);
      color: var(--primary-dark);
      font-weight: 800;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 5px 14px;
      border-radius: 9999px;
      border: 1px solid var(--primary-border);
      margin-bottom: 18px;
    }}
    h1 {{
      font-size: 32px;
      font-weight: 900;
      line-height: 1.25;
      color: var(--slate-950);
      letter-spacing: -0.02em;
      margin-bottom: 16px;
    }}
    .article-meta {{
      font-size: 13.5px;
      color: var(--slate-500);
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--slate-200);
      margin-bottom: 28px;
    }}
    .article-meta strong {{ color: var(--slate-700); }}

    /* Answer-First AEO Callout Box */
    .aeo-direct-answer {{
      background: #f0fdf4;
      border: 2px solid #86efac;
      border-left: 6px solid var(--primary-dark);
      border-radius: var(--radius-md);
      padding: 24px;
      margin-bottom: 36px;
    }}
    .aeo-direct-answer .aeo-label {{
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #166534;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .aeo-direct-answer p {{
      font-size: 16px;
      font-weight: 600;
      color: #14532d;
      line-height: 1.6;
      margin: 0;
    }}

    /* Action CTA Box */
    .cta-card {{
      background: linear-gradient(135deg, #090d16 0%, #1e293b 100%);
      color: #ffffff;
      border-radius: var(--radius-md);
      padding: 28px;
      margin: 36px 0;
      display: flex;
      flex-direction: column;
      gap: 16px;
      box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
    }}
    .cta-card h3 {{ font-size: 20px; font-weight: 800; color: #fff; margin: 0; }}
    .cta-card p {{ font-size: 14.5px; color: #cbd5e1; margin: 0; line-height: 1.6; }}
    .cta-btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      background: var(--primary);
      color: #061326;
      font-size: 15px;
      font-weight: 800;
      padding: 12px 24px;
      border-radius: var(--radius-sm);
      text-decoration: none;
      align-self: flex-start;
      transition: all 0.15s ease;
    }}
    .cta-btn:hover {{ background: #34d399; transform: translateY(-1px); }}
    .cta-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12.5px;
      color: #94a3b8;
    }}
    .cta-badge svg {{ fill: var(--primary); }}

    /* Body Typography */
    h2 {{
      font-size: 22px;
      font-weight: 800;
      color: var(--slate-900);
      margin-top: 40px;
      margin-bottom: 14px;
      letter-spacing: -0.01em;
    }}
    h3 {{
      font-size: 17px;
      font-weight: 700;
      color: var(--slate-800);
      margin-top: 24px;
      margin-bottom: 10px;
    }}
    p {{
      font-size: 15.5px;
      color: var(--slate-700);
      margin-bottom: 16px;
    }}
    ul, ol {{
      padding-left: 22px;
      margin-bottom: 20px;
    }}
    li {{
      font-size: 15px;
      color: var(--slate-700);
      margin-bottom: 8px;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13.5px;
      background: var(--slate-100);
      padding: 2px 6px;
      border-radius: 4px;
      color: #0f172a;
      border: 1px solid var(--slate-200);
    }}
    pre {{
      background: var(--slate-950);
      color: #f1f5f9;
      padding: 18px 20px;
      border-radius: var(--radius-sm);
      overflow-x: auto;
      font-size: 13px;
      line-height: 1.5;
      margin-bottom: 24px;
      border: 1px solid #1e293b;
    }}
    pre code {{
      background: transparent;
      padding: 0;
      color: inherit;
      border: none;
    }}

    /* Table styling */
    .table-container {{
      overflow-x: auto;
      margin: 24px 0;
      border: 1px solid var(--slate-200);
      border-radius: var(--radius-sm);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      text-align: left;
    }}
    th {{
      background: var(--slate-100);
      padding: 12px 16px;
      font-weight: 700;
      color: var(--slate-800);
      border-bottom: 1px solid var(--slate-200);
    }}
    td {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--slate-200);
      color: var(--slate-700);
    }}
    tr:last-child td {{ border-bottom: none; }}
    tr:nth-child(even) {{ background: #fafafa; }}

    /* POPIA Notice Box */
    .popia-box {{
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-left: 5px solid #2563eb;
      border-radius: var(--radius-sm);
      padding: 18px 20px;
      margin: 32px 0;
    }}
    .popia-box h4 {{
      color: #1e40af;
      font-size: 14.5px;
      font-weight: 800;
      margin-bottom: 6px;
    }}
    .popia-box p {{
      color: #1e3a8a;
      font-size: 13.5px;
      margin: 0;
      line-height: 1.5;
    }}

    /* FAQ Section */
    .faq-item {{
      border-top: 1px solid var(--slate-200);
      padding: 18px 0;
    }}
    .faq-item:last-child {{ border-bottom: 1px solid var(--slate-200); }}
    .faq-question {{
      font-size: 16px;
      font-weight: 800;
      color: var(--slate-900);
      margin-bottom: 8px;
    }}
    .faq-answer {{
      font-size: 14.5px;
      color: var(--slate-600);
      margin: 0;
    }}

    /* Related Guides Grid */
    .related-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-top: 24px;
    }}
    .related-card {{
      background: var(--slate-50);
      border: 1px solid var(--slate-200);
      border-radius: var(--radius-md);
      padding: 20px;
      text-decoration: none;
      transition: all 0.15s ease;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .related-card:hover {{
      border-color: var(--primary);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    .related-card h4 {{
      font-size: 15px;
      font-weight: 700;
      color: var(--slate-900);
      margin-bottom: 8px;
      line-height: 1.4;
    }}
    .related-card p {{
      font-size: 13px;
      color: var(--slate-500);
      margin: 0;
      line-height: 1.5;
    }}
    .related-card span {{
      margin-top: 12px;
      font-size: 12px;
      font-weight: 700;
      color: var(--primary-dark);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}

    /* Footer */
    footer {{
      background: var(--slate-950);
      color: #94a3b8;
      padding: 40px 20px;
      font-size: 13px;
      border-top: 1px solid #1e293b;
    }}
    footer .footer-wrap {{
      max-width: 960px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    footer .footer-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }}
    footer a {{ color: #cbd5e1; text-decoration: none; }}
    footer a:hover {{ color: var(--primary); }}
    footer .footer-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
    }}

    @media (max-width: 768px) {{
      .article-card {{ padding: 24px 20px; }}
      h1 {{ font-size: 24px; }}
      h2 {{ font-size: 19px; }}
      .cta-card {{ padding: 20px; }}
      .cta-btn {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <!-- Navigation -->
  <nav>
    <div class="nav-wrap">
      <a href="/" class="brand">
        TaxClean<span>.</span>
      </a>
      <a href="{cta_link}" class="nav-cta">Convert Statements Free &rarr;</a>
    </div>
  </nav>

  <!-- Breadcrumbs -->
  <div class="breadcrumbs">
    <a href="/">Home</a>
    <span>&rsaquo;</span>
    <a href="/guides/">Accounting Guides</a>
    <span>&rsaquo;</span>
    <span style="color:var(--slate-800); font-weight:600;">{breadcrumb_title}</span>
  </div>

  <!-- Main Article -->
  <main class="main-container">
    <article class="article-card">
      <div class="guide-badge">{guide_category}</div>
      <h1>{h1_title}</h1>
      <div class="article-meta">
        <span>Published by <strong>Nikhar Bechan</strong> (Founder, TaxClean)</span>
        <span>&bull;</span>
        <span>Updated: <strong>November 2026</strong></span>
        <span>&bull;</span>
        <span>Target: <strong>{target_audience}</strong></span>
      </div>

      <!-- AEO Answer-First Callout -->
      <div class="aeo-direct-answer">
        <div class="aeo-label">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
          Direct Answer / Quick Solution
        </div>
        <p>{direct_answer}</p>
      </div>

      <!-- Interactive 1-Click CTA -->
      <div class="cta-card">
        <div>
          <h3>Need to convert your statement right now?</h3>
          <p>{cta_sub}</p>
        </div>
        <a href="{cta_link}" class="cta-btn">
          {cta_text} &rarr;
        </a>
        <div class="cta-badge">
          <svg width="14" height="14" viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/></svg>
          {cta_badge}
        </div>
      </div>

      <!-- Detailed Technical Content -->
      <div class="article-body">
        {article_body_html}
      </div>

      <!-- Compliance Notice Box -->
      {compliance_box_html}

      <!-- Frequently Asked Questions -->
      <section style="margin-top: 40px;">
        <h2>Frequently Asked Questions</h2>
        <div class="faq-list">
          {faq_html}
        </div>
      </section>

      <!-- Related Guides Hub -->
      <section style="margin-top: 48px; border-top: 1px solid var(--slate-200); padding-top: 32px;">
        <h2>{related_heading}</h2>
        <div class="related-grid">
          {related_guides_html}
        </div>
      </section>
    </article>
  </main>

  <!-- Footer -->
  <footer>
    <div class="footer-wrap">
      <div class="footer-top">
        <div>
          {footer_brand_summary}
        </div>
        <div class="footer-links">
          <a href="/">Home</a>
          <a href="/guides/">All Guides</a>
          {footer_privacy_link}
          <a href="/terms.html">Terms &amp; EULA</a>
          <a href="mailto:sales@taxcleanza.com">Contact Support</a>
        </div>
      </div>
      <div style="border-top: 1px solid #1e293b; padding-top: 16px; font-size: 12px; color: #64748b;">
        {footer_trademark_note}
      </div>
    </div>
  </footer>
</body>
</html>
"""

# Guide Data Definitions with Strict <= 40 Word Direct Answers
GUIDES = [
    {
        "slug": "convert-capitec-pdf-to-sage-pastel",
        "breadcrumb_title": "Capitec to Sage Pastel",
        "guide_category": "Capitec Bank &bull; Sage Pastel Partner &bull; Xero",
        "h1_title": "How to Convert Capitec PDF Bank Statements to Sage Pastel Partner & Xero (Without CSV Errors)",
        "meta_title": "Convert Capitec PDF Statement to Sage Pastel Partner & Xero | TaxClean",
        "meta_desc": "Convert Capitec Global One & Business PDF statements into balanced Sage Pastel Cashbook CSV & Xero without column mismatches or broken multi-row descriptions.",
        "meta_keywords": "convert capitec pdf statement to csv sage pastel, capitec bank statement to xero, capitec statement to pastel partner, import capitec into pastel cashbook",
        "cta_text": "Convert Capitec PDF Statement (Free)",
        "cta_link": "/?bank=capitec&export=pastel#app",
        "direct_answer": "To import Capitec PDF statements into Sage Pastel or Xero, convert them into a headerless 3-column CSV: Date (DD/MM/YYYY), Description (max 30 characters), and Amount (negative for payments). Multi-line transaction text must be collapsed into a single row.",
        "howto_steps": [
            {
                "name": "Extract & Collapse Multi-Row Text",
                "text": "Parse Capitec PDF transactions, merging POS purchase descriptions across split lines into a single clean description."
            },
            {
                "name": "Format Dates to DD/MM/YYYY",
                "text": "Normalize all date tokens to DD/MM/YYYY and set payment amounts as negative numbers."
            },
            {
                "name": "Import into Pastel Cashbook",
                "text": "Navigate to Pastel Process > Cashbooks > Import, select CSV Comma Delimited, and map Date, Description, Amount."
            }
        ],
        "article_body_html": "\n<h2>Why Capitec Bank Statements Break in Sage Pastel &amp; Xero</h2>\n<p>Capitec Bank is one of the most widely used banks for South African small business owners, contractors, and individuals. However, Capitec's digital banking app and internet banking platform present two massive headaches for bookkeepers:</p>\n<ol>\n  <li><strong>No CSV or OFX Export Option:</strong> Unlike corporate banking portals, Capitec retail and small business accounts only provide official monthly statement downloads as <code>PDF</code> documents.</li>\n  <li><strong>Multi-Line Transaction Descriptions:</strong> In Capitec statements, a single debit card transaction is rendered across multiple lines (e.g., Row 1: <code>POS PURCHASE</code>, Row 2: <code>CHECKERS BALLITO</code>, Row 3: <code>15 NOV 14:22</code>). When copied into Excel or passed through generic PDF converters, this creates orphan rows without amounts or dates, triggering Sage Pastel's notorious <code>File contains invalid lines or column count mismatch</code> crash.</li>\n</ol>\n\n<h2>The Exact CSV Specification Required by Sage Pastel Cashbook</h2>\n<p>Sage Pastel Partner Cashbook import does not tolerate extra columns, blank lines, or header rows. Your CSV file must strictly adhere to the following 3-column format:</p>\n\n<div class=\"table-container\">\n  <table>\n    <thead>\n      <tr>\n        <th>Column #</th>\n        <th>Field Name</th>\n        <th>Format / Rule</th>\n        <th>Example</th>\n      </tr>\n    </thead>\n    <tbody>\n      <tr>\n        <td>Column 1</td>\n        <td><strong>Date</strong></td>\n        <td>Strictly <code>DD/MM/YYYY</code> (No hyphens, no ISO format)</td>\n        <td><code>15/11/2026</code></td>\n      </tr>\n      <tr>\n        <td>Column 2</td>\n        <td><strong>Description</strong></td>\n        <td>Alphanumeric string (Max 30 characters, no commas)</td>\n        <td><code>Checkers Ballito 4921</code></td>\n      </tr>\n      <tr>\n        <td>Column 3</td>\n        <td><strong>Amount</strong></td>\n        <td>Numeric with period decimal (Negative = Payment, Positive = Receipt)</td>\n        <td><code>-452.80</code></td>\n      </tr>\n    </tbody>\n  </table>\n</div>\n\n<p><strong>Crucial Rule:</strong> The CSV must contain <em>NO HEADER ROW</em>. Line 1 of the file must be the first actual transaction.</p>\n\n<pre><code>15/11/2026,Checkers Ballito,-452.80\n16/11/2026,Client Settlement INV102,12500.00\n17/11/2026,Vodacom Direct Debit,-299.00</code></pre>\n\n<h2>Step-by-Step: How to Import the Converted CSV into Sage Pastel</h2>\n<ol>\n  <li>Open Sage Pastel Partner and select your company database.</li>\n  <li>Navigate to <strong>Process &rarr; Cashbooks</strong> and select the relevant Bank account cashbook.</li>\n  <li>Click the <strong>Import</strong> button at the bottom of the cashbook window.</li>\n  <li>Under <em>File Format</em>, choose <strong>CSV (Comma Delimited)</strong>.</li>\n  <li>Ensure the mapping is set to <strong>Date, Description, Amount</strong>.</li>\n  <li>Select your cleaned <code>.csv</code> file and click <strong>Process</strong>. All transactions will populate the bank reconciliation screen with exact balances.</li>\n</ol>\n",
        "faqs": [
            {
                "q": "Can I export a CSV directly from the Capitec Banking App?",
                "a": "No. The Capitec personal banking app and web portal only generate PDF statements. To get an importable CSV for Sage Pastel or Xero, you must convert the PDF using a dedicated bank statement parser like TaxClean."
            },
            {
                "q": "What date format does Sage Pastel Partner require?",
                "a": "Sage Pastel Partner requires dates in DD/MM/YYYY format (e.g. 15/11/2026). Files with YYYY/MM/DD or YYYY-MM-DD will fail with an 'Invalid date' error."
            },
            {
                "q": "How does TaxClean handle Capitec multi-row descriptions?",
                "a": "TaxClean's deterministic parser recognizes Capitec transaction boundary markers, merging multi-line merchant text into a single clean 30-character description while eliminating fee summary lines."
            },
            {
                "q": "Is it safe to upload client Capitec statements to TaxClean?",
                "a": "TaxClean processes files 100% locally in your computer's browser memory (WebAssembly). No banking data, names, or account numbers are ever sent to a remote server, fully complying with South Africa's POPIA Act."
            }
        ],
        "country": "ZA"
    },
    {
        "slug": "fnb-csv-date-format-error-sage-pastel",
        "breadcrumb_title": "FNB CSV to Sage Pastel Fix",
        "guide_category": "FNB Banking &bull; Sage Pastel Partner &bull; Cashbook",
        "h1_title": "How to Fix FNB CSV Import Errors in Sage Pastel Partner (\"Invalid Date Format\" & Metadata Crashes)",
        "meta_title": "Fix FNB CSV Import Errors in Sage Pastel Partner (\"Invalid Date\") | TaxClean",
        "meta_desc": "Solve FNB CSV date format errors (YYYY/MM/DD to DD/MM/YYYY) and metadata header crashes when importing bank statements into Sage Pastel Cashbook.",
        "meta_keywords": "fnb csv date format error sage pastel, fnb bank statement to pastel partner, pastel cashbook fnb import crash, invalid date line 4 fnb pastel",
        "cta_text": "Clean FNB CSV Statement (Free)",
        "cta_link": "/?bank=fnb&export=pastel#app",
        "direct_answer": "FNB CSV import fails in Sage Pastel because exports contain 3 informational header rows and YYYY/MM/DD dates. Delete the top 3 metadata rows, format dates to DD/MM/YYYY starting on line 1, and sanitize commas in descriptions.",
        "howto_steps": [
            {
                "name": "Delete 3 Metadata Rows",
                "text": "Open FNB CSV and remove the top 3 lines containing Account Name, Account Number, and Balance."
            },
            {
                "name": "Reformat Dates to DD/MM/YYYY",
                "text": "Convert date column from YYYY/MM/DD to DD/MM/YYYY."
            },
            {
                "name": "Sanitize Description Commas",
                "text": "Remove or quote internal commas in store descriptions to prevent column shifting."
            }
        ],
        "article_body_html": "\n<h2>The Root Cause of FNB CSV Import Crashes in Pastel Cashbook</h2>\n<p>First National Bank (FNB) allows users to download transactions as a Comma Separated Value (<code>.csv</code>) file directly from Online Banking Enterprise or Personal Online Banking. However, attempting to import this file directly into Sage Pastel Partner Cashbook results in immediate failure:</p>\n\n<pre><code>Error: \"Invalid Date at line 4\" or \"Column count mismatch at line 1\"</code></pre>\n\n<p>This happens because FNB's default CSV structure violates three core requirements of Sage Pastel Partner:</p>\n<ol>\n  <li><strong>3 Top Metadata Lines:</strong> FNB prepends the file with account details (Account Name, Number, Balance). Pastel expects line 1 to be the first transaction.</li>\n  <li><strong>Date Format Mismatch:</strong> FNB outputs dates as <code>YYYY/MM/DD</code>. Sage Pastel expects <code>DD/MM/YYYY</code>.</li>\n  <li><strong>Unquoted Description Commas:</strong> FNB store names often include commas (e.g. <code>ENGEN, QUICKSHOP 102</code>). When unquoted, CSV parsers split this into two columns, shifting the amount into the balance column.</li>\n</ol>\n\n<h2>The Fix: Transforming FNB CSV to Pastel Specification</h2>\n<ol>\n  <li>Open the downloaded FNB CSV in Notepad or Excel.</li>\n  <li><strong>Delete Rows 1, 2, and 3 completely</strong> so that your first actual transaction is on Row 1.</li>\n  <li>Select the <strong>Date</strong> column and format to <code>dd/mm/yyyy</code>.</li>\n  <li>Ensure amounts are single-column (negative for payments, positive for receipts).</li>\n  <li>Save the file as <strong>CSV (Comma Delimited) (*.csv)</strong>.</li>\n</ol>\n",
        "faqs": [
            {
                "q": "Why does Pastel Cashbook give an 'Invalid Date' error on FNB CSV?",
                "a": "FNB exports dates as YYYY/MM/DD, whereas Sage Pastel requires DD/MM/YYYY. Furthermore, the first 3 lines contain account text rather than dates."
            },
            {
                "q": "How can I convert FNB CSVs without using Excel?",
                "a": "You can drop your FNB statement directly into TaxClean. It automatically strips the 3 header rows, reformats all dates to DD/MM/YYYY, sanitizes store commas, and outputs an import-ready Pastel CSV in 2 seconds."
            }
        ],
        "country": "ZA"
    },
    {
        "slug": "standard-bank-csv-format-sage-business-cloud",
        "breadcrumb_title": "Standard Bank CSV to Sage Cloud",
        "guide_category": "Standard Bank &bull; Sage Business Cloud &bull; Pastel",
        "h1_title": "Standard Bank CSV Format for Sage Business Cloud & Pastel Partner (Fix Layout Mismatch)",
        "meta_title": "Standard Bank CSV Format for Sage Business Cloud & Pastel | TaxClean",
        "meta_desc": "Fix Standard Bank CSV layout mismatch errors in Sage Business Cloud Accounting (Sage One) and Pastel Partner. Complete column mapping guide.",
        "meta_keywords": "standard bank csv format sage business cloud, standard bank statement pastel partner, standard bank csv layout mismatch sage one, standard bank to excel",
        "cta_text": "Format Standard Bank Statement (Free)",
        "cta_link": "/?bank=standardbank&export=sageone#app",
        "direct_answer": "Standard Bank CSV statements fail in Sage Accounting because they start with 4 metadata header lines and leading apostrophes on dates. Delete the top 4 metadata rows, remove date apostrophes, and ensure DD/MM/YYYY formatting for seamless import.",
        "howto_steps": [
            {
                "name": "Purge Metadata Header Block",
                "text": "Delete rows 1 to 4 of Standard Bank export containing Historical Statement text."
            },
            {
                "name": "Strip Leading Date Apostrophes",
                "text": "Remove the prepended single quote character from date values ('2026-11-15)."
            },
            {
                "name": "Map Columns in Sage Cloud",
                "text": "Map Date, Description, Amount in Sage Business Cloud Banking import."
            }
        ],
        "article_body_html": "\n<h2>Why Standard Bank CSV Statements Fail in Sage Accounting</h2>\n<p>Standard Bank Internet Banking and NetBank Enterprise provide CSV downloads for business accounts. However, importing them into <strong>Sage Business Cloud Accounting</strong> (formerly Sage One) or <strong>Sage Pastel Partner</strong> frequently triggers:</p>\n\n<pre><code>\"The file uploaded does not match the expected layout\" or \"Invalid delimiter detected\"</code></pre>\n\n<p>This layout error stems from two distinct formatting quirks in Standard Bank's export engine:</p>\n<ul>\n  <li><strong>4-Line Metadata Block:</strong> Standard Bank begins the export with 4 rows of statement metadata (e.g. <code>Historical Statement</code>, <code>Account Number: 002345678</code>, date ranges, and empty separator rows).</li>\n  <li><strong>Leading Apostrophe on Date Strings:</strong> To prevent Microsoft Excel from corrupting date formats, Standard Bank frequently prepends dates with a single quote (e.g. <code>'2026-11-15</code>). While invisible in Excel, accounting software parsers read this as invalid text rather than a timestamp.</li>\n</ul>\n",
        "faqs": [
            {
                "q": "Why does Standard Bank put an apostrophe in front of the date in CSV?",
                "a": "Standard Bank adds a leading apostrophe ('2026-11-15) to prevent Excel from automatically converting dates into US format. However, this apostrophe breaks automated import parsers in Sage and Xero."
            },
            {
                "q": "How do I import Standard Bank statements into Sage Business Cloud?",
                "a": "In Sage Business Cloud, go to Banking > Transactions > Import Bank Statements. Upload your TaxClean-formatted CSV file and map Date, Description, and Amount."
            }
        ],
        "country": "ZA"
    },
    {
        "slug": "convert-nedbank-pdf-statement-to-csv-xero",
        "breadcrumb_title": "Nedbank PDF to CSV & Xero",
        "guide_category": "Nedbank &bull; Xero &bull; Sage Pastel",
        "h1_title": "How to Convert Nedbank Password-Protected PDF Statements to CSV for Xero & Pastel",
        "meta_title": "Convert Nedbank PDF Statements to CSV & Xero (Encrypted Fix) | TaxClean",
        "meta_desc": "Convert password-protected Nedbank PDF bank statements into balanced CSV for Xero, Sage Pastel, and QuickBooks Online with zero data leaks.",
        "meta_keywords": "convert nedbank pdf statement to csv xero, nedbank password protected bank statement converter, nedbank statement pastel partner, nedbank pdf to excel",
        "cta_text": "Convert Nedbank Statement (Free)",
        "cta_link": "/?bank=nedbank&export=xero#app",
        "direct_answer": "To import Nedbank PDF statements into Xero or Pastel, enter the statement password to unlock the file, condense the 6-column layout into standard columns, and strip opening balance, closing balance, and fee summary rows to prevent duplicate transactions.",
        "howto_steps": [
            {
                "name": "Unlock Password Locally",
                "text": "Decrypt Nedbank statement in local browser RAM using account holder SA ID or CIPC registration number."
            },
            {
                "name": "Filter Out Non-Transaction Rows",
                "text": "Exclude opening balance, closing balance, and interest summary rows."
            },
            {
                "name": "Export to Xero or Pastel",
                "text": "Generate a 5-column Xero CSV or 3-column Pastel Cashbook file."
            }
        ],
        "article_body_html": "\n<h2>The Challenges of Nedbank Monthly e-Statements</h2>\n<p>Nedbank issues monthly bank statements as digitally encrypted PDF documents. For accounting professionals, Nedbank files introduce three major hurdles:</p>\n<ol>\n  <li><strong>Password Encryption:</strong> E-statements are locked with the account holder's South African ID number or company registration number. Most generic online converters crash with \"Encrypted PDF: Password required\".</li>\n  <li><strong>6-Column Layout:</strong> Nedbank uses six columns: <code>Date</code>, <code>Transaction Description</code>, <code>Value Date</code>, <code>Amount</code>, <code>Balance</code>, and <code>Bank Charges</code>. If imported directly into Xero, the separate Value Date and Fee columns create duplicate transactions.</li>\n  <li><strong>Embedded Summary Totals:</strong> Nedbank places opening balance, closing balance, and interest totals directly inside the transaction table grid.</li>\n</ol>\n",
        "faqs": [
            {
                "q": "What is the default password for Nedbank PDF statements?",
                "a": "For individual accounts, the password is typically the account holder's 13-digit South African ID number. For business accounts, it is usually the CK / CIPC registration number without slashes."
            },
            {
                "q": "Is my statement password saved or transmitted to TaxClean servers?",
                "a": "No. The password decryption happens entirely in your local browser RAM via WebAssembly. Your password and financial transactions are never transmitted over the internet."
            }
        ],
        "country": "ZA"
    },
    {
        "slug": "absa-csv-reverse-order-sage-pastel",
        "breadcrumb_title": "Absa Reverse Order Fix",
        "guide_category": "Absa Bank &bull; Sage Pastel Partner &bull; Chrono-Sort",
        "h1_title": "How to Reverse Absa Bank CSV Order & Date Format for Sage Pastel Cashbook",
        "meta_title": "Reverse Absa CSV Order for Sage Pastel Cashbook Import | TaxClean",
        "meta_desc": "Fix Absa bank statement reverse chronological order and ISO date format errors when importing into Sage Pastel Partner Cashbook.",
        "meta_keywords": "absa csv reverse order sage pastel import, absa bank statement csv pastel, absa date format yyyy-mm-dd pastel error, absa statement to excel",
        "cta_text": "Sort & Clean Absa Statement (Free)",
        "cta_link": "/?bank=absa&export=pastel#app",
        "direct_answer": "Absa Online exports CSV statements in reverse chronological order with the latest transaction at the top. Sage Pastel Partner Cashbook requires transactions in strict chronological order (oldest first). Sort data ascending by date and reformat to DD/MM/YYYY.",
        "howto_steps": [
            {
                "name": "Reverse Transaction Order",
                "text": "Sort transactions ascending by date so the oldest transaction sits on row 1."
            },
            {
                "name": "Reformat ISO Dates",
                "text": "Convert YYYY-MM-DD dates to DD/MM/YYYY format."
            },
            {
                "name": "Strip Quotes & Export",
                "text": "Remove wrapping quotation marks and export to Pastel Cashbook 3-column layout."
            }
        ],
        "article_body_html": "\n<h2>Why Absa's Reverse Transaction Order Scrambles Sage Pastel</h2>\n<p>When downloading statement transactions from Absa Online Banking, Absa lists transactions in reverse chronological order (newest date at the top, oldest date at the bottom). While convenient for quick browsing, importing this directly into Sage Pastel Partner Cashbook causes:</p>\n<ul>\n  <li><strong>Scrambled Running Balances:</strong> Pastel calculates the cashbook balance chronologically. When payments and deposits post in reverse, intermediate running balances do not balance with monthly statements.</li>\n  <li><strong>Invalid Date Formatting:</strong> Absa exports dates as <code>YYYY-MM-DD</code> (ISO format) rather than Pastel's mandatory <code>DD/MM/YYYY</code>.</li>\n</ul>\n",
        "faqs": [
            {
                "q": "Why does Sage Pastel Cashbook require oldest transactions first?",
                "a": "Pastel processes cashbook entries sequentially. If transactions enter in reverse order, running bank reconciliations and interest calculations are posted backward."
            }
        ],
        "country": "ZA"
    },
    {
        "slug": "sage-pastel-bank-statement-csv-specification",
        "breadcrumb_title": "Sage Pastel CSV Specification",
        "guide_category": "Sage Pastel Partner &bull; Cashbook Specification &bull; Reference",
        "h1_title": "Sage Pastel Partner Bank Statement CSV Layout & Format Specification",
        "meta_title": "Sage Pastel Bank Statement CSV Format Specification | TaxClean",
        "meta_desc": "The complete layout specification for Sage Pastel Partner & Xpress cashbook CSV imports. Column orders, character limits, delimiters, and sample files.",
        "meta_keywords": "sage pastel bank statement csv format specification, pastel partner import bank statement column layout, pastel cashbook csv layout, pastel import format",
        "cta_text": "Export to Sage Pastel Format (Free)",
        "cta_link": "/?export=pastel#app",
        "direct_answer": "Sage Pastel Partner accepts two bank statement CSV formats: a 3-column layout (Date, Description, Amount) and a 5-column layout (Date, Reference, Description, Amount, GDC Code). Both layouts require NO header row, comma delimiters, DD/MM/YYYY date formatting, and negative values for payments.",
        "howto_steps": [
            {
                "name": "Choose 3-Col or 5-Col Layout",
                "text": "Select 3-column layout for standard Bank Manager reconciliation or 5-column layout for pre-allocated GDC codes."
            },
            {
                "name": "Enforce Strict Column Rules",
                "text": "Ensure no header row, comma delimiters, DD/MM/YYYY dates, and negative amounts for payments."
            },
            {
                "name": "Save as Plain CSV",
                "text": "Export without quotes or currency symbols and import via Process > Cashbooks."
            }
        ],
        "article_body_html": "\n<h2>The Official CSV Import Specifications for Sage Pastel Partner</h2>\n<p>Sage Pastel Partner and Sage Pastel Xpress support importing electronic bank statements directly into Cashbook batches. Depending on your practice workflow, two distinct import paths exist:</p>\n\n<h3>Path 1: Standard 3-Column Cashbook Bank Statement Import</h3>\n<p>Used for importing raw bank transactions to reconcile against your cashbook:</p>\n<div class=\"table-container\">\n  <table>\n    <thead>\n      <tr>\n        <th>Position</th>\n        <th>Field Name</th>\n        <th>Type</th>\n        <th>Rules &amp; Constraints</th>\n      </tr>\n    </thead>\n    <tbody>\n      <tr>\n        <td>1</td>\n        <td>Date</td>\n        <td>Date</td>\n        <td>Strictly <code>DD/MM/YYYY</code>. Do not use hyphens.</td>\n      </tr>\n      <tr>\n        <td>2</td>\n        <td>Description</td>\n        <td>String</td>\n        <td>Maximum 30 characters. Commas must be removed or enclosed in quotes.</td>\n      </tr>\n      <tr>\n        <td>3</td>\n        <td>Amount</td>\n        <td>Decimal</td>\n        <td>Negative for Payments (e.g. <code>-150.00</code>), Positive for Receipts (<code>500.00</code>). Period decimal only.</td>\n      </tr>\n    </tbody>\n  </table>\n</div>\n\n<h3>Path 2: Advanced 10-Column Cashbook Batch ASCII Journal</h3>\n<p>Used when importing pre-coded accounting batches directly into general ledger journal batches:</p>\n<p>Format: <code>Period, Date (DD/MM/YYYY), GDC Code (G/D/C), Account, Reference, Description, Amount, TaxType, TaxAmount, OpenItem</code>.</p>\n<p><em>Note:</em> In the 10-column batch journal, payments are positive and receipts are negative, reflecting credit bank balance postings.</p>\n",
        "faqs": [
            {
                "q": "Should a Sage Pastel CSV file include column header titles?",
                "a": "NO. Sage Pastel Cashbook will fail if line 1 contains text headers like 'Date, Description, Amount'. Row 1 must contain the first actual transaction."
            },
            {
                "q": "Why does Pastel import with semicolons instead of commas?",
                "a": "In Windows, if your regional locale uses a comma as a decimal separator, Excel will save CSV files using semicolons. You can override this in Windows Regional Settings or use TaxClean's direct Pastel exporter."
            }
        ],
        "country": "ZA"
    },
    {
        "slug": "popia-compliance-bank-statements-accounting-south-africa",
        "breadcrumb_title": "POPIA Compliance Guide",
        "guide_category": "POPIA Act 4 of 2013 &bull; Data Security &bull; Accounting Firms",
        "h1_title": "POPIA Section 72 & Client Bank Statements: Why SA Accounting Practices Must Stop Using Cloud PDF Converters",
        "meta_title": "POPIA Compliance for Bank Statements: Why SA Accountants Avoid Cloud Converters | TaxClean",
        "meta_desc": "Understand POPIA Section 72 transborder liabilities when converting client bank statements. Why cloud PDF tools violate South African data privacy laws.",
        "meta_keywords": "popia compliance bank statements accounting south africa, popia section 72 transborder data, secure bank statement converter south africa, popia accounting firm liability",
        "cta_text": "Convert Privately in Browser RAM (Free)",
        "cta_link": "/?privacy=popia#app",
        "direct_answer": "Under POPIA Section 72, transferring client bank statements to offshore cloud converters without binding contracts or consent is unlawful. In-browser client-side WebAssembly processing keeps financial records strictly in local RAM, ensuring full compliance with POPIA Section 19 security obligations.",
        "howto_steps": None,
        "article_body_html": "\n<h2>The Hidden Legal Risk in Everyday Accounting Practice</h2>\n<p>When an accounting firm receives client bank statements in PDF format, junior staff often upload these documents to free or paid online PDF-to-Excel converters (such as Smallpdf, Zamzar, or US/UK cloud tools). What many practitioners do not realize is that this practice constitutes an immediate breach of <strong>South Africa's Protection of Personal Information Act (POPIA Act 4 of 2013)</strong>.</p>\n\n<h3>1. Section 72: Prohibition on Transborder Information Transfers</h3>\n<p>POPIA Section 72 strictly prohibits sending personal information outside the Republic of South Africa unless:</p>\n<ul>\n  <li>The recipient country offers an adequate level of data protection substantially similar to POPIA.</li>\n  <li>The data subject (your accounting client) has provided <strong>explicit, informed consent</strong>.</li>\n  <li>A binding contract (Data Processing Agreement) exists holding the third party to POPIA standards.</li>\n</ul>\n<p>Most foreign PDF websites retain uploaded files on overseas servers for OCR training, caching, or unverified periods, exposing the accounting practice to severe regulatory fines and civil liability.</p>\n\n<h3>2. Section 19: Security Safeguards &amp; Duty of Care</h3>\n<p>Under Section 19, responsible parties must secure the integrity and confidentiality of personal information by preventing unlawful access. Bank statements contain account numbers, branch codes, physical addresses, and sensitive financial behavior\u2014making them high-risk financial data.</p>\n\n<h2>The Architectural Solution: Client-Side WebAssembly Processing</h2>\n<p>TaxClean was engineered from the ground up to solve the POPIA compliance dilemma for South African accountants:</p>\n<ol>\n  <li><strong>Local Browser RAM Execution:</strong> When a PDF is parsed, 100% of the extraction logic runs inside the user's browser using WebAssembly.</li>\n  <li><strong>Zero Server Transmission:</strong> The document is never uploaded to any remote server or third-party cloud.</li>\n  <li><strong>Zero Retention:</strong> As soon as the browser tab is closed, all memory is immediately wiped.</li>\n</ol>\n",
        "faqs": [
            {
                "q": "Does POPIA apply to small bookkeeping practices?",
                "a": "Yes. POPIA applies to all legal entities in South Africa processing personal information, regardless of turnover or firm size."
            },
            {
                "q": "What penalties exist under POPIA for data breaches?",
                "a": "The Information Regulator can impose administrative fines of up to R10 million, along with imprisonment for severe offenses and significant reputational damage."
            }
        ],
        "country": "ZA"
    },
    {
        "country": "ZA",
        "slug": "sars-vat201-efiling-bank-reconciliation-guide",
        "breadcrumb_title": "SARS VAT201 Bank Reconciliation",
        "guide_category": "South Africa &bull; SARS VAT201 &bull; eFiling &bull; Sage Pastel",
        "h1_title": "How to Reconcile Bank Statements for SARS VAT201 eFiling (Without Audit Disallowances)",
        "meta_title": "SARS VAT201 Bank Statement Reconciliation Guide | TaxClean",
        "meta_desc": "Reconcile South African bank statements for SARS VAT201 eFiling. Step-by-step 15/115 tax fraction calculation, zero-rated fuel, and entertainment disallowances.",
        "meta_keywords": "sars vat201 bank reconciliation, vat201 efiling guide, 15/115 vat calculation south africa, section 16 2 tax invoices, zero rated fuel vat201",
        "cta_text": "Generate SARS VAT201 Schedule (.xlsx)",
        "cta_link": "/?export=vat201#app",
        "direct_answer": "To prepare a SARS VAT201 return from bank statements, calculate the 15/115 tax fraction on standard-rated expenses while isolating zero-rated forecourt fuel, exempt bank fees, and disallowed entertainment expenses before claiming input tax on eFiling.",
        "howto_steps": [
            {
                "name": "Separate Zero-Rated & Exempt Items",
                "text": "Isolate Section 11(1)(h) petrol/diesel fuel purchases, bank service fees, and salary payments from claimable supplies."
            },
            {
                "name": "Calculate 15/115 Input Tax Fraction",
                "text": "Apply the statutory 15/115 fraction to standard-rated commercial expenses to compute deductible input tax."
            },
            {
                "name": "Reconcile Against Valid Tax Invoices",
                "text": "Verify that every transaction claimed under eFiling Field 15 is supported by a valid Section 20 tax invoice with supplier VAT registration."
            }
        ],
        "article_body_html": "\n<h2>Why Bank Statements Alone Trigger SARS VAT201 Audits</h2>\n<p>Every two months, registered VAT vendors in South Africa file their <strong>VAT201 declaration</strong> on SARS eFiling. A common mistake made by small business owners and bookkeepers is pulling bank statement totals into Microsoft Excel and multiplying the total expenditure by 15%. When SARS issues a <em>Request for Relevant Material (Verification Letter)</em>, this shortcut leads to massive input tax disallowances, penalties, and interest under the Tax Administration Act.</p>\n\n<p>Under <strong>Section 16(2) of the VAT Act 89 of 1991</strong>, no input tax deduction may be made unless the vendor possesses a valid full tax invoice (or abridged tax invoice for amounts under R5,000) containing the supplier's 10-digit VAT registration number, physical address, and detailed description of goods or services.</p>\n\n<h2>The 4 Statutory Expenditure Buckets on Bank Statements</h2>\n<p>When reconciling an FNB, Standard Bank, Nedbank, Capitec, or Absa bank statement for VAT201 filing, transactions must be partitioned into four distinct statutory treatments:</p>\n\n<div class=\"table-container\">\n  <table>\n    <thead>\n      <tr>\n        <th>Category</th>\n        <th>Statutory Reference</th>\n        <th>Common Examples on Statement</th>\n        <th>VAT201 Treatment</th>\n      </tr>\n    </thead>\n    <tbody>\n      <tr>\n        <td><strong>Standard-Rated (15%)</strong></td>\n        <td>Section 7(1)(a)</td>\n        <td>Checkers, Makro, Vodacom, Adobe, Stationery, Subcontractors</td>\n        <td>Claim <code>Gross &times; 15 / 115</code> in Field 15 (Input Tax)</td>\n      </tr>\n      <tr>\n        <td><strong>Zero-Rated (0%)</strong></td>\n        <td>Section 11(1)(h)</td>\n        <td>Engen, Shell, BP, Sasol, Total (Petrol &amp; Diesel fuel)</td>\n        <td>Include in total expenditure, but claim R 0.00 input VAT</td>\n      </tr>\n      <tr>\n        <td><strong>Exempt Supplies</strong></td>\n        <td>Section 12(a)</td>\n        <td>Bank monthly fees, card transaction fees, interest paid, overdraft fees</td>\n        <td>Excluded from VAT claim entirely</td>\n      </tr>\n      <tr>\n        <td><strong>Disallowed Supplies</strong></td>\n        <td>Section 17(2)</td>\n        <td>Spur, Mugg &amp; Bean, restaurant meals, staff entertainment, gym fees</td>\n        <td>Input VAT strictly denied by law even if supplier charged 15% VAT</td>\n      </tr>\n    </tbody>\n  </table>\n</div>\n\n<h2>How TaxClean Generates an Audit-Proof VAT201 Working Schedule</h2>\n<p>TaxClean includes an automated <strong>SARS VAT201 Working Paper Generator</strong> built directly into the local browser engine:</p>\n<ol>\n  <li><strong>Automatic Merchant Classification:</strong> TaxClean detects forecourt fuel brands (Engen, Shell, BP, Sasol) and flags them as zero-rated under Section 11(1)(h).</li>\n  <li><strong>Entertainment Isolation:</strong> Food and beverage merchants (Spur, KFC, Nandos, Seattle Coffee) are automatically isolated into an \"Entertainment Disallowed\" schedule.</li>\n  <li><strong>Input vs. Output Net Calculation:</strong> Reconciles customer receipts (Standard-Rated Field 1A) against qualifying vendor payments (Field 15) to produce the exact Net Payable or Refund due.</li>\n  <li><strong>1-Click Excel Schedule:</strong> Exports a multi-tab workbook formatted specifically for SARS verification audits with formulas intact.</li>\n</ol>\n",
        "faqs": [
            {
                "q": "Can I claim VAT back on petrol or diesel bought for company vehicles?",
                "a": "No. Under Section 11(1)(h) of the South African VAT Act, fuel subject to the fuel levy (petrol and diesel) is zero-rated at 0%. No input VAT may be claimed."
            },
            {
                "q": "What is the formula to calculate 15% VAT from a gross bank statement amount?",
                "a": "To extract VAT from a gross inclusive amount in South Africa, multiply the gross amount by 15 and divide by 115 (Amount * 15 / 115)."
            },
            {
                "q": "Are bank fees subject to VAT in South Africa?",
                "a": "Bank charges, monthly administration fees, and cash handling fees are financial services exempt from VAT under Section 12(a). Do not claim input VAT on bank charges."
            }
        ]
    },
    {
        "country": "ZA",
        "slug": "convert-discovery-bank-pdf-statement-to-excel-xero",
        "breadcrumb_title": "Discovery Bank to Excel & Xero",
        "guide_category": "South Africa &bull; Discovery Bank &bull; Xero &bull; Excel",
        "h1_title": "How to Convert Discovery Bank PDF Statements to Excel & Xero (Strip Vitality Points)",
        "meta_title": "Convert Discovery Bank PDF Statements to Excel & Xero | TaxClean",
        "meta_desc": "Convert Discovery Bank Gold, Platinum & Black PDF statements to clean Excel (.xlsx) and Xero CSV. Strips Vitality Money cashback points and currency conversion lines.",
        "meta_keywords": "convert discovery bank pdf statement to excel, discovery bank to xero csv, discovery vitality cashback accounting, discovery bank statement converter",
        "cta_text": "Convert Discovery Statement (Free)",
        "cta_link": "/?bank=discovery&export=xero#app",
        "direct_answer": "To convert Discovery Bank PDF statements into Excel or Xero, extract pure banking debits and credits while stripping embedded Vitality Money reward points, multi-currency conversion lines, and interest summaries into a standardized 3-column CSV.",
        "howto_steps": [
            {
                "name": "Isolate Vitality Money Cashbacks",
                "text": "Filter out reward points and promotional cashback lines from actual bank cash movements."
            },
            {
                "name": "Consolidate Multi-Currency Rows",
                "text": "Collapse foreign transaction markup lines into a single ZAR settlement amount."
            },
            {
                "name": "Map Columns to Xero CSV",
                "text": "Format transactions into Date (DD/MM/YYYY), Amount, and Payee for direct Xero or Excel import."
            }
        ],
        "article_body_html": "\n<h2>Why Discovery Bank Statements are Difficult to Reconcile</h2>\n<p>Discovery Bank is popular among professionals and high-growth businesses due to its dynamic interest rates and Vitality Money rewards integration. However, monthly PDF statements generated by the Discovery Banking app present severe formatting challenges for bookkeepers:</p>\n<ul>\n  <li><strong>Embedded Vitality Money Points:</strong> Statements interleave actual ZAR cash transactions with Vitality Miles earning summaries, spend boost cashbacks, and partner discounts. Generic PDF converters import these as regular bank transactions, distorting closing balances.</li>\n  <li><strong>Multi-Line FX Transactions:</strong> Foreign card payments (e.g. Google, Zoom, Microsoft) are rendered across 3 distinct sub-rows displaying original foreign currency amount, exchange rate markup, and final settled Rand amount.</li>\n  <li><strong>Dynamic Daily Interest Lines:</strong> Discovery calculates and displays daily interest rate changes within the statement grid.</li>\n</ul>\n\n<h2>Converting to Xero and Sage Pastel</h2>\n<p>To successfully import Discovery statements without manual editing:</p>\n<ol>\n  <li>Drop the PDF into TaxClean with the \"Discovery Bank\" profile selected.</li>\n  <li>TaxClean automatically filters out Vitality Miles rewards and interest rate notices.</li>\n  <li>Multi-line foreign transactions are collapsed into a single row with the final ZAR settlement amount and the foreign currency referenced in the description.</li>\n  <li>Download the balanced 5-column Xero CSV or formatted Sage Pastel Cashbook batch import file.</li>\n</ol>\n",
        "faqs": [
            {
                "q": "How does TaxClean handle Discovery Vitality Money cashbacks?",
                "a": "TaxClean recognizes promotional points and miles notations, keeping actual bank cash deposits while stripping non-monetary points summaries from your accounting export."
            },
            {
                "q": "Does Discovery Bank offer direct CSV downloads on web?",
                "a": "Discovery Bank web banking allows basic CSV export for some transactional accounts, but credit card and shared vault accounts frequently require PDF statement conversion."
            }
        ]
    },
    {
        "country": "US",
        "slug": "convert-chase-pdf-statement-to-quickbooks-online-iif",
        "breadcrumb_title": "Chase to QuickBooks Online & IIF",
        "guide_category": "United States &bull; Chase Bank &bull; QuickBooks Online &bull; Desktop IIF",
        "h1_title": "How to Convert JPMorgan Chase PDF Statements to QuickBooks Online & Desktop (.IIF)",
        "meta_title": "Convert Chase PDF Statements to QuickBooks (.CSV & .IIF) | TaxClean",
        "meta_desc": "Convert JPMorgan Chase checking and commercial credit card PDF statements to QuickBooks Online (.csv) and QuickBooks Desktop (.iif) with MM/DD/YYYY dates.",
        "meta_keywords": "convert chase pdf statement to quickbooks, chase statement to quickbooks desktop iif, chase credit card pdf to csv, chase bank quickbooks import error",
        "cta_text": "Convert Chase Statement to QuickBooks (Free)",
        "cta_link": "/?bank=chase&export=qbo#app",
        "direct_answer": "To import Chase PDF bank statements into QuickBooks Online or Desktop, convert the statement into a 3-column CSV (Date, Description, Amount) with MM/DD/YYYY dates, or export directly to QuickBooks IIF format with check numbers mapped.",
        "howto_steps": [
            {
                "name": "Extract Chase Statement Grids",
                "text": "Parse deposits, electronic withdrawals, and check registers from multi-page Chase PDF statements."
            },
            {
                "name": "Enforce US Date Format (MM/DD/YYYY)",
                "text": "Standardize all date entries to US month-first formatting to prevent QuickBooks date inversion."
            },
            {
                "name": "Export to QBO CSV or Desktop IIF",
                "text": "Export 3-column CSV for QuickBooks Online Banking or .IIF batch file for QuickBooks Desktop."
            }
        ],
        "article_body_html": "\n<h2>Common Issues When Importing Chase Statements to QuickBooks</h2>\n<p>JPMorgan Chase is the largest business bank in the United States. While Chase offers direct feeds for some business accounts, feeds frequently disconnect, miss historical transactions over 90 days, or fail for secondary commercial cards. When accountants convert monthly PDF e-statements manually, they hit three persistent issues:</p>\n<ol>\n  <li><strong>Fragmented Transaction Sections:</strong> Chase statements group transactions into distinct sections: <em>Deposits and Additions</em>, <em>ATM &amp; Debit Card Withdrawals</em>, <em>Electronic Withdrawals</em>, and <em>Checks Paid</em> (with separate check number tables). Generic converters scramble the order or drop check numbers completely.</li>\n  <li><strong>Date Inversion Bugs in Excel:</strong> Opening converted CSVs in spreadsheet software often converts US dates (<code>11/05/2026</code> - November 5) into international format (May 11), creating chaotic reconciliations in QuickBooks.</li>\n  <li><strong>QuickBooks Desktop .IIF Syntax:</strong> QuickBooks Desktop requires strict tab-delimited Intuit Interchange Format (<code>.IIF</code>) headers with specific transaction block markers (<code>!TRNS</code>, <code>!SPL</code>, <code>!ENDTRNS</code>).</li>\n</ol>\n\n<h2>QuickBooks Online (QBO) 3-Column CSV Specification</h2>\n<p>For QuickBooks Online, format your file as a clean 3-column CSV:</p>\n<div class=\"table-container\">\n  <table>\n    <thead>\n      <tr>\n        <th>Date</th>\n        <th>Description</th>\n        <th>Amount</th>\n      </tr>\n    </thead>\n    <tbody>\n      <tr>\n        <td>11/15/2026</td>\n        <td>STRIPE PAYOUT REF 8901</td>\n        <td>2450.00</td>\n      </tr>\n      <tr>\n        <td>11/16/2026</td>\n        <td>AMAZON WEB SERVICES</td>\n        <td>-128.50</td>\n      </tr>\n    </tbody>\n  </table>\n</div>\n",
        "faqs": [
            {
                "q": "What date format does QuickBooks Online require for US bank imports?",
                "a": "QuickBooks Online in the United States requires MM/DD/YYYY date formatting (e.g. 11/15/2026). Using DD/MM/YYYY will cause dates after the 12th of the month to be rejected."
            },
            {
                "q": "Can TaxClean convert Chase statements directly to QuickBooks Desktop .IIF?",
                "a": "Yes. TaxClean includes a native QuickBooks Desktop .IIF exporter that formats transactions with correct header blocks and account mappings without requiring third-party plugins."
            }
        ]
    },
    {
        "country": "GB",
        "slug": "convert-barclays-pdf-statement-to-xero-freeagent",
        "breadcrumb_title": "Barclays to Xero & FreeAgent",
        "guide_category": "United Kingdom &bull; Barclays Bank &bull; Xero &bull; FreeAgent &bull; HMRC MTD",
        "h1_title": "How to Convert Barclays PDF Bank Statements to Xero & FreeAgent (HMRC MTD Ready)",
        "meta_title": "Convert Barclays PDF Statements to Xero & FreeAgent | TaxClean",
        "meta_desc": "Convert Barclays business and personal PDF bank statements into balanced Xero and FreeAgent CSVs. Solves disconnected Open Banking feeds and multi-line descriptions.",
        "meta_keywords": "convert barclays pdf statement to xero, barclays statement to freeagent csv, barclays bank feed disconnected xero, barclays pdf to excel hmrc vat",
        "cta_text": "Convert Barclays Statement (Free)",
        "cta_link": "/?bank=barclays&export=xero#app",
        "direct_answer": "To import Barclays PDF statements into Xero or FreeAgent, normalize transaction lines into standard columns: Date (DD/MM/YYYY), Amount, and Payee. Merge split Faster Payment descriptions and filter out opening balance lines for HMRC MTD compliance.",
        "howto_steps": [
            {
                "name": "Merge Sub-Line Description Markers",
                "text": "Stitch multi-line BGC, Direct Debit, and Faster Payment details into single Payee strings."
            },
            {
                "name": "Standardize to DD/MM/YYYY Format",
                "text": "Format dates to UK standard DD/MM/YYYY and isolate debits as negative values."
            },
            {
                "name": "Import into Xero or FreeAgent",
                "text": "Upload the clean CSV to Xero Accounting or FreeAgent for 1-click HMRC Making Tax Digital reconciliation."
            }
        ],
        "article_body_html": "\n<h2>Why Barclays Bank Feeds Fail in UK Accounting Software</h2>\n<p>Under UK Open Banking regulations, direct bank feeds between Barclays and platforms like Xero, QuickBooks, and FreeAgent must be re-authenticated every 90 days. When feeds break or historical catch-up bookkeeping is required (e.g. for year-end self-assessment or quarterly HMRC Making Tax Digital VAT returns), accountants must import PDF statements manually.</p>\n\n<p>Barclays statements contain specific layout structures that break generic converters:</p>\n<ul>\n  <li><strong>Multi-Line Sub-Descriptors:</strong> A single transaction displays merchant name, execution code (e.g. <code>BGC</code>, <code>FT</code>, <code>DD</code>), and internal transaction reference numbers across 2 to 3 lines.</li>\n  <li><strong>Embedded Overdraft &amp; Fee Summaries:</strong> End-of-month statements include non-transactional interest calculation and overdraft facility notices inside the main balance ledger.</li>\n</ul>\n\n<h2>FreeAgent &amp; Xero CSV Layout Requirements</h2>\n<p>FreeAgent expects a simple 3-column CSV: <code>Date (DD/MM/YYYY), Amount (Negative for payments, positive for receipts), Description</code>.</p>\n<p>Xero accepts either a 3-column CSV or a 5-column CSV with Payee, Description, and Reference separated.</p>\n",
        "faqs": [
            {
                "q": "Why do UK accountants use FreeAgent with Barclays statements?",
                "a": "Barclays offers free FreeAgent software to business banking customers. However, when automated feeds experience outages, bookkeepers rely on TaxClean to generate clean FreeAgent CSVs."
            },
            {
                "q": "Is TaxClean compliant with UK GDPR regulations?",
                "a": "Yes. TaxClean executes entirely in local browser RAM using client-side WebAssembly. No banking records or financial transactions leave your UK workstation or touch external servers."
            }
        ]
    },
    {
        "slug": "convert-bank-of-america-pdf-statement-to-quickbooks-excel",
        "country": "US",
        "meta_title": "Convert Bank of America PDF Statement to QuickBooks Online & Excel | TaxClean",
        "meta_desc": "Fix Bank of America PDF statement date errors and check table splits. Convert BofA checking & credit card PDFs to QuickBooks Online (QBO 3-column CSV) & Excel.",
        "meta_keywords": "bank of america pdf to quickbooks, convert bofa pdf statement to excel, bank of america statement date error qbo, bofa csv import quickbooks online",
        "breadcrumb_title": "Bank of America to QuickBooks & Excel",
        "guide_category": "United States \u2022 Bank of America \u2022 QuickBooks Online \u2022 Excel",
        "h1_title": "How to Convert Bank of America PDF Statements to QuickBooks Online & Excel",
        "direct_answer": "To convert Bank of America PDF statements to QuickBooks Online or Excel, extract transactions into a 3-column CSV (Date, Description, Amount) with MM/DD/YYYY dates while collapsing multi-line Zelle and ACH descriptions into single transaction rows.",
        "cta_text": "Convert Bank of America Statement to QuickBooks (Free)",
        "cta_link": "/?bank=bofa&export=qbo#app",
        "article_body_html": "\n<h2>Why Bank of America PDF Imports Break in QuickBooks Online</h2>\n<p>Small businesses and CPAs across the United States frequently encounter errors when importing Bank of America statements into QuickBooks Online (QBO) and QuickBooks Desktop. Bank of America structures checking and corporate credit card statements with specialized multi-table layouts that generic PDF-to-Excel converters fail to parse accurately:</p>\n\n<ul>\n  <li><strong>Split Transaction Tables:</strong> Bank of America divides transactions into distinct sections: <em>Deposits and other credits</em>, <em>Withdrawals and other debits</em>, and a separate <em>Checks and other debits</em> ledger with dedicated check numbers. Generic converters drop check numbers or mix check sequences into debit descriptions.</li>\n  <li><strong>Multi-Line Zelle &amp; ACH Descriptors:</strong> Online payments and wire transfers frequently span 2 to 3 lines (e.g. <code>ZELLE TRANSFER CONF# 102938475; VENDOR NAME; INVOICE 8841</code>). Naive parsers split these descriptors across multiple rows, multiplying ghost transactions in QuickBooks.</li>\n  <li><strong>Date Inversion Bugs:</strong> QuickBooks Online in the United States strictly requires <code>MM/DD/YYYY</code> dates (e.g., <code>11/15/2026</code>). Converting statements with international tools forces dates past the 12th of each month to fail with <em>'Invalid Date Format'</em> errors upon QBO upload.</li>\n</ul>\n\n<h2>Required QuickBooks Online 3-Column CSV Specification</h2>\n<p>To successfully upload your Bank of America statement through QuickBooks Online's <strong>Transactions &gt; Bank Transactions &gt; Upload from file</strong> workflow, the CSV file must strictly follow this structure:</p>\n\n<table style=\"width:100%; border-collapse:collapse; margin:20px 0; font-size:14px;\">\n  <thead>\n    <tr style=\"background:var(--slate-100); text-align:left; border-bottom:2px solid var(--slate-300);\">\n      <th style=\"padding:10px;\">Column A (Date)</th>\n      <th style=\"padding:10px;\">Column B (Description)</th>\n      <th style=\"padding:10px;\">Column C (Amount)</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr style=\"border-bottom:1px solid var(--slate-200);\">\n      <td style=\"padding:10px;\"><code>MM/DD/YYYY</code> (e.g. 11/04/2026)</td>\n      <td style=\"padding:10px;\">Acme Industrial Supplies Check #4102</td>\n      <td style=\"padding:10px;\"><code>-450.00</code> (Negative for debits)</td>\n    </tr>\n    <tr style=\"border-bottom:1px solid var(--slate-200);\">\n      <td style=\"padding:10px;\"><code>MM/DD/YYYY</code> (e.g. 11/08/2026)</td>\n      <td style=\"padding:10px;\">Client Retainer Payment Zelle</td>\n      <td style=\"padding:10px;\"><code>2500.00</code> (Positive for deposits)</td>\n    </tr>\n  </tbody>\n</table>\n\n<h2>Step-by-Step Conversion Workflow</h2>\n<ol style=\"margin-left:20px; line-height:1.8;\">\n  <li><strong>Select Bank of America PDF:</strong> Drag and drop your monthly statement into TaxClean. Client-side WebAssembly reads the document in your workstation's local memory.</li>\n  <li><strong>Automated Check &amp; ACH Reconciliation:</strong> The engine matches check numbers from the checks table and collapses multi-line Zelle strings into clean merchant names.</li>\n  <li><strong>Download Import-Ready QBO CSV or Excel:</strong> Download the pre-formatted 3-column CSV or open the balanced Excel spreadsheet with automated balance checks.</li>\n</ol>\n",
        "faqs": [
            {
                "question": "Why does QuickBooks Online reject Bank of America CSV files?",
                "answer": "QuickBooks Online in the United States requires an exact 3-column format (Date, Description, Amount) formatted as MM/DD/YYYY. Online banking exports frequently include extra header metadata lines that cause QBO upload errors."
            },
            {
                "question": "How does TaxClean handle Bank of America check numbers?",
                "answer": "TaxClean's engine parses the dedicated 'Checks and other debits' table, integrating the check number into the payee description so it reconciles automatically against your QuickBooks check register."
            },
            {
                "question": "Is client banking data safe when converting on TaxClean?",
                "answer": "Yes. TaxClean operates entirely within your browser memory (local RAM). No account numbers, balances, or transaction details are transmitted to external servers, satisfying US GLBA and FTC Safeguards compliance requirements."
            }
        ]
    },
    {
        "slug": "convert-hsbc-uk-pdf-statement-to-xero-sage",
        "country": "GB",
        "meta_title": "Convert HSBC UK PDF Statements to Xero & Sage (Fix Trailing Minus Signs) | TaxClean",
        "meta_desc": "Convert HSBC UK business and Kinetic bank statement PDFs to Xero and Sage CSV. Fixes trailing minus signs, mid-statement fee summaries, and DD/MM/YYYY dates.",
        "meta_keywords": "convert hsbc uk pdf statement to xero, hsbc bank statement to sage csv, hsbc trailing minus sign fix, hsbc kinetic pdf to excel",
        "breadcrumb_title": "HSBC UK to Xero & Sage",
        "guide_category": "United Kingdom \u2022 HSBC UK \u2022 Xero \u2022 Sage Business Cloud \u2022 HMRC MTD",
        "h1_title": "How to Convert HSBC UK PDF Statements to Xero & Sage (Fix Trailing Minus Signs)",
        "direct_answer": "To convert HSBC UK PDF statements to Xero or Sage, normalize transactions into a 3-column CSV with DD/MM/YYYY dates, invert trailing minus signs into standard negative amounts, and exclude end-of-month interest calculation summaries.",
        "cta_text": "Convert HSBC UK Statement (Free)",
        "cta_link": "/?bank=hsbc&export=xero#app",
        "article_body_html": "\n<h2>Common HSBC UK PDF Statement Import Obstacles</h2>\n<p>HSBC UK Business Banking and HSBC Kinetic statements present unique layout characteristics that frequently disrupt direct imports into Xero, Sage Business Cloud, and QuickBooks Online:</p>\n\n<ul>\n  <li><strong>Trailing Minus Signs &amp; Accounting Parentheses:</strong> HSBC frequently formats debit transactions with trailing minus signs (e.g. <code>\u00a31,250.00-</code>) or enclosed in brackets <code>(\u00a31,250.00)</code>. When converted naively, spreadsheet applications treat these amounts as unparseable text strings, triggering mathematical balance validation errors during software import.</li>\n  <li><strong>HSBC Transaction Execution Codes:</strong> Statements display transaction codes such as <code>BP</code> (Bill Payment), <code>CR</code> (Credit), <code>DR</code> (Debit), <code>SO</code> (Standing Order), and <code>DD</code> (Direct Debit) in dedicated sub-columns. Standard tools misalign these codes, shifting payee names into the date or amount column.</li>\n  <li><strong>End-of-Month Fee &amp; Interest Blocks:</strong> HSBC statements often interleave quarterly maintenance fee schedules, borrowing rate notices, and overdraft summaries directly into the transaction ledger, throwing off closing balance reconciliations.</li>\n</ul>\n\n<h2>HMRC Making Tax Digital (MTD) VAT Alignment</h2>\n<p>Under HMRC Making Tax Digital (MTD) regulations, UK VAT-registered businesses must maintain an unbroken digital audit trail from digital source documents to the 9-box VAT return (VAT100). Manual copy-pasting of HSBC statement figures into spreadsheets breaches digital link requirements.</p>\n\n<p>TaxClean converts HSBC PDF statements into compliant 3-column CSV files (<code>Date [DD/MM/YYYY], Amount, Description</code>) that import directly into your accounting software's reconciliation screen with zero copy-pasting.</p>\n\n<h2>Step-by-Step Conversion Process</h2>\n<ol style=\"margin-left:20px; line-height:1.8;\">\n  <li><strong>Upload HSBC Statement PDF:</strong> Drag and drop your monthly HSBC Business or Kinetic PDF statement into TaxClean.</li>\n  <li><strong>Automated Sign &amp; Description Normalization:</strong> Trailing minus signs are normalized to standard signed floats (e.g. <code>-1250.00</code>) and non-transactional fee notices are filtered out.</li>\n  <li><strong>Export Clean CSV for Xero or Sage:</strong> Download your balanced CSV formatted for direct import into Xero, Sage, FreeAgent, or Excel.</li>\n</ol>\n",
        "faqs": [
            {
                "question": "How does TaxClean fix HSBC trailing minus signs?",
                "answer": "TaxClean's engine detects accounting debit notations (such as 150.00- or (150.00)) and converts them into standardized signed decimal values (-150.00) recognized by Xero, Sage, and Excel."
            },
            {
                "question": "Does TaxClean support HSBC Kinetic mobile statements?",
                "answer": "Yes. Both classic HSBC Business Banking PDF statements and modern HSBC Kinetic mobile app PDF statement downloads are fully supported."
            },
            {
                "question": "Is client data kept private under UK GDPR?",
                "answer": "Yes. All processing executes client-side inside your browser memory using WebAssembly. Client financial statements never leave your UK workstation or touch external cloud servers."
            }
        ]
    },
    {
        "slug": "convert-commbank-pdf-statement-to-xero-myob",
        "country": "AU",
        "meta_title": "Convert CommBank PDF Statements to Xero & MYOB (ATO BAS Ready) | TaxClean",
        "meta_desc": "Convert CommBank & CommBiz PDF statements to Xero and MYOB CSV. Formats DD/MM/YYYY dates, strips pending PayID lines, and prepares data for ATO BAS 10% GST.",
        "meta_keywords": "convert commbank pdf statement to xero, commbiz statement to myob csv, commbank pdf to excel australia, commbank ato bas gst reconciliation",
        "breadcrumb_title": "CommBank to Xero & MYOB",
        "guide_category": "Australia \u2022 CommBank \u2022 CommBiz \u2022 Xero \u2022 MYOB \u2022 ATO BAS",
        "h1_title": "How to Convert CommBank PDF Statements to Xero & MYOB (ATO BAS Ready)",
        "direct_answer": "To convert CommBank PDF statements to Xero or MYOB, extract transactions into a 3-column CSV with DD/MM/YYYY dates while collapsing multi-line PayID descriptions and filtering out pending or pre-authorized transactions for ATO BAS reconciliation.",
        "cta_text": "Convert CommBank Statement to Xero / MYOB (Free)",
        "cta_link": "/?bank=commbank&export=xero#app",
        "article_body_html": "\n<h2>Why CommBank &amp; CommBiz PDF Statements Require Normalization</h2>\n<p>Australian bookkeepers, tax agents, and small business owners dealing with Commonwealth Bank of Australia (CommBank) and CommBiz PDF statements face distinct technical challenges when preparing accounts for MYOB and Xero:</p>\n\n<ul>\n  <li><strong>Multi-Line PayID &amp; Osko Descriptors:</strong> Faster payments in CommBank split merchant name, BSB/Account, and transaction reference numbers across 2 to 3 lines (e.g. <code>TRANSFER TO 062-000 12345678 OSKO PAYMENT TO ACME PTY LTD REF: INV 4421</code>). Basic converters fragment these details into separate empty rows.</li>\n  <li><strong>Pending &amp; Authorised Transaction Bleed:</strong> CommBiz monthly statement exports occasionally list pending credit card authorizations at the cutoff date, causing the calculated closing balance to diverge from the physical statement balance.</li>\n  <li><strong>ATO BAS 10% GST Categorization:</strong> Preparing quarterly Business Activity Statements (BAS) for the Australian Taxation Office (ATO) requires isolating standard 10% GST taxable expenses (using the <code>1/11th</code> GST fraction for Label 1B) from input-taxed financial supplies (bank fees, loan interest) and GST-free purchases.</li>\n</ul>\n\n<h2>MYOB &amp; Xero Australian CSV Layout Requirements</h2>\n<p>Both MYOB (AccountRight &amp; MYOB Business) and Xero Australia accept a streamlined 3-column CSV layout:</p>\n\n<table style=\"width:100%; border-collapse:collapse; margin:20px 0; font-size:14px;\">\n  <thead>\n    <tr style=\"background:var(--slate-100); text-align:left; border-bottom:2px solid var(--slate-300);\">\n      <th style=\"padding:10px;\">Date</th>\n      <th style=\"padding:10px;\">Amount</th>\n      <th style=\"padding:10px;\">Payee / Description</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr style=\"border-bottom:1px solid var(--slate-200);\">\n      <td style=\"padding:10px;\"><code>DD/MM/YYYY</code> (e.g. 15/11/2026)</td>\n      <td style=\"padding:10px;\"><code>-320.00</code></td>\n      <td style=\"padding:10px;\">Bunnings Warehouse Alexandria</td>\n    </tr>\n    <tr style=\"border-bottom:1px solid var(--slate-200);\">\n      <td style=\"padding:10px;\"><code>DD/MM/YYYY</code> (e.g. 18/11/2026)</td>\n      <td style=\"padding:10px;\"><code>1850.00</code></td>\n      <td style=\"padding:10px;\">Client Invoice 2084 Direct Credit</td>\n    </tr>\n  </tbody>\n</table>\n\n<h2>Step-by-Step CommBank Conversion Workflow</h2>\n<ol style=\"margin-left:20px; line-height:1.8;\">\n  <li><strong>Select CommBank PDF Statement:</strong> Drag and drop your CommBank personal, NetBank, or CommBiz business PDF statement into TaxClean.</li>\n  <li><strong>Automated Osko &amp; PayID Consolidation:</strong> The engine merges multi-line transaction references into a single clean Payee line.</li>\n  <li><strong>Download MYOB or Xero CSV:</strong> Save your balanced, reconciled CSV ready for immediate import into your Australian bank feed.</li>\n</ol>\n",
        "faqs": [
            {
                "question": "What CSV format does MYOB require for Australian bank imports?",
                "answer": "MYOB AccountRight and MYOB Business require a 3-column CSV: Date (DD/MM/YYYY), Amount (Negative for payments, positive for deposits), and Description."
            },
            {
                "question": "How does TaxClean assist with ATO BAS preparation?",
                "answer": "TaxClean's Excel export provides an automated statutory tax schedule, isolating input-taxed bank fees and GST-free purchases from standard 10% GST taxable claims."
            },
            {
                "question": "Does TaxClean comply with the Australian Privacy Principles (APPs)?",
                "answer": "Yes. TaxClean processes files 100% client-side in your device's browser memory (local RAM). No client financial data is transmitted to offshore cloud servers, complying with the Privacy Act 1988 and TASA 2009 standards."
            }
        ]
    }
]

def generate_schema_json(guide):
    canonical = f"{BASE_URL}/guides/{guide['slug']}.html"
    c_code = guide.get("country", "ZA")
    in_lang = "en-US" if c_code == "US" else ("en-GB" if c_code == "GB" else ("en-AU" if c_code == "AU" else "en-ZA"))
    
    faq_entities = []
    for f in guide["faqs"]:
        q_text = f.get("q") or f.get("question", "")
        a_text = f.get("a") or f.get("answer", "")
        faq_entities.append({
            "@type": "Question",
            "name": q_text,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": a_text
            }
        })
        
    graph_entities = [
        {
            "@type": "Article",
            "@id": f"{canonical}#article",
            "isPartOf": {
                "@type": "WebSite",
                "@id": f"{BASE_URL}/#website",
                "name": "TaxClean",
                "url": BASE_URL
            },
            "headline": guide["h1_title"],
            "description": guide["meta_desc"],
            "image": f"{BASE_URL}/og-banner.png",
            "url": canonical,
            "inLanguage": in_lang,
            "datePublished": "2026-11-09T08:00:00+02:00",
            "dateModified": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "author": {
                "@type": "Person",
                "name": "Nikhar Bechan",
                "jobTitle": "Founder & Technical Lead",
                "url": BASE_URL
            },
            "publisher": {
                "@type": "Organization",
                "@id": f"{BASE_URL}/#organization",
                "name": "TaxClean Technologies",
                "url": BASE_URL,
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{BASE_URL}/og-banner.png"
                }
            }
        }
    ]

    # Only add HowTo schema if steps exist (omits on legal advisory)
    if guide.get("howto_steps"):
        steps = []
        for step_data in guide["howto_steps"]:
            steps.append({
                "@type": "HowToStep",
                "name": step_data["name"],
                "text": step_data["text"]
            })
        graph_entities.append({
            "@type": "HowTo",
            "@id": f"{canonical}#howto",
            "name": guide["h1_title"],
            "description": guide["direct_answer"],
            "step": steps
        })

    graph_entities.extend([
        {
            "@type": "FAQPage",
            "@id": f"{canonical}#faq",
            "mainEntity": faq_entities
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"{canonical}#breadcrumbs",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Home",
                    "item": BASE_URL
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "Guides",
                    "item": f"{BASE_URL}/guides/"
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": guide["breadcrumb_title"],
                    "item": canonical
                }
            ]
        }
    ])

    return json.dumps({"@context": "https://schema.org", "@graph": graph_entities}, indent=2)

def build_related_guides_html(current_slug):
    """
    Smart contextual linking:
    - For International guides (US, GB, AU): links to sibling guides from the same country first,
      then OTHER international guides (never drops into South African retail banks).
    - For South African guides: links exclusively to sibling South African banks.
    """
    curr_guide = next((g for g in GUIDES if g["slug"] == current_slug), None)
    curr_country = curr_guide["country"] if curr_guide else "ZA"
    
    selected = []
    if curr_country != "ZA":
        same_country = [g for g in GUIDES if g.get("country") == curr_country and g["slug"] != current_slug]
        other_intl = [g for g in GUIDES if g.get("country") not in ("ZA", curr_country) and g["slug"] != current_slug]
        selected.extend(same_country)
        selected.extend(other_intl)
        if len(selected) > 3:
            selected = selected[:3]
        elif len(selected) < 3:
            remaining = [g for g in GUIDES if g["slug"] != current_slug and g not in selected]
            selected.extend(remaining[:(3 - len(selected))])
    else:
        same_country = [g for g in GUIDES if g.get("country") == "ZA" and g["slug"] != current_slug]
        selected = same_country[:3]
        
    cards = []
    for g in selected:
        cards.append(f"""          <a href="/guides/{g['slug']}.html" class="related-card">
            <div>
              <div style="font-size:11px;font-weight:700;color:var(--primary-dark);text-transform:uppercase;margin-bottom:4px">{g.get('guide_category', '').split('&bull;')[0].strip()}</div>
              <h4>{g['h1_title']}</h4>
              <p>{g['meta_desc'][:110]}...</p>
            </div>
            <span>Read Step-by-Step Fix &rarr;</span>
          </a>""")
    return "\n".join(cards)

def build_faq_html(faqs):
    items = []
    for f in faqs:
        q_text = f.get('q') or f.get('question', '')
        a_text = f.get('a') or f.get('answer', '')
        items.append(f"""          <div class="faq-item">
            <div class="faq-question">{q_text}</div>
            <div class="faq-answer">{a_text}</div>
          </div>""")
    return "\n".join(items)

def generate_guides_hub_html():
    hub_canonical = f"{BASE_URL}/guides/"
    guide_cards = []
    for g in GUIDES:
        c_code = g.get('country', 'ZA')
        flag = "🇿🇦" if c_code == "ZA" else ("🇺🇸" if c_code == "US" else ("🇬🇧" if c_code == "GB" else ("🇦🇺" if c_code == "AU" else "🌐")))
        country_name = "South Africa" if c_code == "ZA" else ("United States" if c_code == "US" else ("United Kingdom" if c_code == "GB" else ("Australia" if c_code == "AU" else "Global")))
        guide_cards.append(f"""        <div class="guide-item-card" data-country="{c_code}" style="background:#fff; border:1px solid var(--slate-200); border-radius:12px; padding:24px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 2px 8px rgba(0,0,0,0.04); transition:all 0.15s ease;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <span style="display:inline-block; background:var(--primary-light); color:var(--primary-dark); font-size:11px; font-weight:800; text-transform:uppercase; padding:3px 10px; border-radius:99px; border:1px solid var(--primary-border);">
                {g['guide_category']}
              </span>
              <span style="font-size:12px; font-weight:700; color:var(--slate-500);">{flag} {c_code}</span>
            </div>
            <h3 style="font-size:18px; font-weight:800; color:var(--slate-900); margin-bottom:8px; line-height:1.35;">
              <a href="/guides/{g['slug']}.html" style="color:inherit; text-decoration:none;">{g['h1_title']}</a>
            </h3>
            <p style="font-size:14px; color:var(--slate-600); line-height:1.5; margin-bottom:16px;">
              {g['meta_desc']}
            </p>
          </div>
          <div>
            <a href="/guides/{g['slug']}.html" style="color:var(--primary-dark); font-size:13.5px; font-weight:700; text-decoration:none; display:inline-flex; align-items:center; gap:4px;">
              Read Technical Guide &rarr;
            </a>
          </div>
        </div>""")

    cards_html = "\n".join(guide_cards)

    hub_schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": f"{hub_canonical}#webpage",
                "name": "Global Bank Statement & Accounting Troubleshooting Guides | TaxClean",
                "description": "Technical troubleshooting guides, exact CSV column layouts, and error fixes for South Africa, United States, United Kingdom, and Australian banks and accounting software.",
                "url": hub_canonical,
                "inLanguage": ["en-ZA", "en-US", "en-GB", "en-AU"],
                "publisher": {
                    "@type": "Organization",
                    "name": "TaxClean Technologies",
                    "url": BASE_URL
                }
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{hub_canonical}#breadcrumbs",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Home",
                        "item": BASE_URL
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Guides",
                        "item": hub_canonical
                    }
                ]
            }
        ]
    }

    return f"""<!DOCTYPE html>
<html lang="en-ZA">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Bank Statement &amp; Accounting Troubleshooting Guides | TaxClean</title>
  <meta name="description" content="Technical troubleshooting guides, format specifications, and error fixes for South African, US, UK, and Australian bank statement imports into Sage Pastel, Xero, QuickBooks, MYOB, and FreeAgent." />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{hub_canonical}" />
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23061326'/%3E%3Ctext x='5' y='22' font-family='Inter,Arial,sans-serif' font-weight='800' font-size='15' fill='%23ffffff'%3ETC%3Ctspan fill='%2310b981'%3E.%3C/tspan%3E%3C/text%3E%3C/svg%3E" />
  
  <!-- OpenGraph Metadata -->
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="TaxClean" />
  <meta property="og:url" content="{hub_canonical}" />
  <meta property="og:title" content="Bank Statement &amp; Accounting Troubleshooting Guides | TaxClean" />
  <meta property="og:description" content="Technical troubleshooting guides, format specifications, and error fixes for South African, US, UK, and Australian bank statement imports into Sage Pastel, Xero, QuickBooks, MYOB, and FreeAgent." />
  <meta property="og:image" content="https://taxcleanza.com/og-banner.png" />
  
  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="Bank Statement &amp; Accounting Troubleshooting Guides | TaxClean" />
  <meta name="twitter:description" content="Technical troubleshooting guides, format specifications, and error fixes for South African, US, UK, and Australian bank statement imports into Sage Pastel, Xero, QuickBooks, MYOB, and FreeAgent." />
  <meta name="twitter:image" content="https://taxcleanza.com/og-banner.png" />

  <script type="application/ld+json">
{json.dumps(hub_schema, indent=2)}
  </script>
  <style>
    :root {{
      --primary: #10b981;
      --primary-dark: #059669;
      --primary-light: #ecfdf5;
      --primary-border: #a7f3d0;
      --slate-900: #090d16;
      --slate-800: #1e293b;
      --slate-600: #475569;
      --slate-500: #64748b;
      --slate-200: #e2e8f0;
      --slate-50: #f8fafc;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #0f172a; line-height: 1.6; }}
    nav {{ background: var(--slate-900); padding: 16px 24px; border-bottom: 1px solid rgba(255,255,255,0.08); }}
    nav .wrap {{ max-width: 1040px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }}
    nav .brand {{ color: #fff; font-weight: 800; font-size: 18px; text-decoration: none; }}
    nav .brand span {{ color: var(--primary); }}
    .header {{ max-width: 1040px; margin: 40px auto 20px auto; padding: 0 20px; }}
    h1 {{ font-size: 32px; font-weight: 900; color: #0f172a; margin-bottom: 8px; letter-spacing: -0.02em; }}
    p.lead {{ font-size: 16px; color: var(--slate-600); max-width: 720px; margin-bottom: 24px; }}
    
    /* Country Filter Tabs */
    .filter-tabs {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 18px;
    }}
    .filter-btn {{
      background: #fff;
      border: 1px solid var(--slate-200);
      border-radius: 9999px;
      padding: 7px 16px;
      font-size: 13.5px;
      font-weight: 700;
      color: var(--slate-700);
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .filter-btn:hover, .filter-btn.active {{
      background: var(--slate-900);
      color: #fff;
      border-color: var(--slate-900);
    }}

    .grid {{ max-width: 1040px; margin: 30px auto 60px auto; padding: 0 20px; display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }}
    footer {{ background: #060c18; color: #94a3b8; padding: 36px 20px; font-size: 13px; text-align: center; }}
    footer a {{ color: #cbd5e1; text-decoration: none; margin: 0 10px; }}
    footer a:hover {{ color: var(--primary); }}
  </style>
</head>
<body>
  <nav>
    <div class="wrap">
      <a href="/" class="brand">TaxClean<span>.</span></a>
      <a href="/#app" style="background:var(--primary); color:#061326; font-weight:700; font-size:13px; padding:8px 16px; border-radius:6px; text-decoration:none;">Convert Statements Free &rarr;</a>
    </div>
  </nav>
  <header class="header">
    <div style="font-size:12px; font-weight:800; text-transform:uppercase; color:var(--primary-dark); margin-bottom:8px;">Knowledge Base &amp; Technical Specifications</div>
    <h1>Bank Statement &amp; Accounting Troubleshooting Guides</h1>
    <p class="lead">Step-by-step technical guides, exact CSV column layouts, and error fixes for South African, US, UK, and Australian bank statement imports into Sage Pastel, Xero, QuickBooks, MYOB, and FreeAgent.</p>
    
    <div class="filter-tabs">
      <button type="button" class="filter-btn active" onclick="filterGuides('ALL')">All Guides (14)</button>
      <button type="button" class="filter-btn" onclick="filterGuides('ZA')">🇿🇦 South Africa (9)</button>
      <button type="button" class="filter-btn" onclick="filterGuides('US')">🇺🇸 United States (2)</button>
      <button type="button" class="filter-btn" onclick="filterGuides('GB')">🇬🇧 United Kingdom (2)</button>
      <button type="button" class="filter-btn" onclick="filterGuides('AU')">🇦🇺 Australia (1)</button>
    </div>
  </header>
  <main class="grid" id="guidesGrid">
    {cards_html}
  </main>
  
  <script>
    function filterGuides(country) {{
      document.querySelectorAll('.filter-btn').forEach(function(btn) {{ btn.classList.remove('active'); }});
      if (window.event && window.event.target) {{ window.event.target.classList.add('active'); }}
      var cards = document.querySelectorAll('.guide-item-card');
      cards.forEach(function(card) {{
        if (country === 'ALL' || card.getAttribute('data-country') === country) {{
          card.style.display = 'flex';
        }} else {{
          card.style.display = 'none';
        }}
      }});
    }}
  </script>

  <footer>
    <p>&copy; 2026 TaxClean Technologies. Local browser bank statement converter &bull; Port Shepstone, KZN.</p>
    <p style="margin-top: 10px;">
      <a href="/">Home</a>
      <a href="/guides/">All Guides</a>
      <a href="/privacy.html">POPIA Privacy</a>
      <a href="/terms.html">Terms</a>
      <a href="mailto:sales@taxcleanza.com">Contact Support</a>
    </p>
  </footer>
</body>
</html>
"""
def update_sitemap(new_urls):
    """Safely append new URLs to sitemap.xml if not already present."""
    if not os.path.exists(SITEMAP_PATH):
        print(f"Warning: Sitemap not found at {SITEMAP_PATH}")
        return

    tree = ET.parse(SITEMAP_PATH)
    root = tree.getroot()
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")

    existing_locs = set()
    for url in root.findall("s:url", ns):
        loc = url.find("s:loc", ns)
        if loc is not None and loc.text:
            existing_locs.add(loc.text.strip())

    added_count = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for url_str in new_urls:
        if url_str not in existing_locs:
            url_elem = ET.SubElement(root, "url")
            loc_elem = ET.SubElement(url_elem, "loc")
            loc_elem.text = url_str
            lastmod_elem = ET.SubElement(url_elem, "lastmod")
            lastmod_elem.text = today
            changefreq_elem = ET.SubElement(url_elem, "changefreq")
            changefreq_elem.text = "weekly"
            priority_elem = ET.SubElement(url_elem, "priority")
            priority_elem.text = "0.90" if "/guides/" in url_str else "0.95"
            existing_locs.add(url_str)
            added_count += 1

    ET.indent(tree, space="  ", level=0)
    tree.write(SITEMAP_PATH, encoding="UTF-8", xml_declaration=True)
    print(f"Sitemap updated: Added {added_count} new URLs (Total: {len(existing_locs)})")
    return list(existing_locs)

def ping_indexnow(urls):
    """Pings the IndexNow API so Bing and participating search engines discover the URLs instantly."""
    endpoint = "https://api.indexnow.org/indexnow"
    payload = {
        "host": "taxcleanza.com",
        "key": INDEXNOW_KEY,
        "keyLocation": f"{BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": urls
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.getcode()
            print(f"IndexNow API response: HTTP {status} (Notified {len(urls)} URLs)")
            return status
    except Exception as e:
        print(f"IndexNow ping notification: {e}")
        return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    created_urls = []

    # 1. Generate Hub Page
    hub_html = generate_guides_hub_html()
    hub_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(hub_path, "w", encoding="utf-8") as f:
        f.write(hub_html)
    print(f"Generated Hub: {hub_path}")
    created_urls.append(f"{BASE_URL}/guides/")

    root_guides_path = os.path.join(os.path.dirname(__file__), "website", "guides.html")
    with open(root_guides_path, "w", encoding="utf-8") as f:
        f.write(hub_html)
    print(f"Generated Root Mirror: {root_guides_path}")

    # 2. Generate Each Guide
    for guide in GUIDES:
        canonical = f"{BASE_URL}/guides/{guide['slug']}.html"
        schema_json = generate_schema_json(guide)
        related_html = build_related_guides_html(guide["slug"])
        faq_html = build_faq_html(guide["faqs"])

        country = guide.get("country", "ZA")
        slug = guide["slug"]
        
        # Guide-specific CTA sub-paragraphs to prevent copy-paste leaks
        if "bank-of-america" in slug:
            default_cta_sub = "Don't waste hours manually re-keying check tables in Excel. Drop your Bank of America statement below to generate balanced, import-ready QuickBooks Online (.csv) or Excel (.xlsx) files in 2 seconds."
        elif "chase" in slug:
            default_cta_sub = "Don't waste hours manually re-keying check tables in Excel. Drop your Chase statement below to generate balanced, import-ready QuickBooks Online (.csv), QuickBooks Desktop (.IIF), or Excel files in 2 seconds."
        elif "hsbc" in slug:
            default_cta_sub = "Don't waste hours untangling trailing minus signs and fee summaries in Excel. Drop your HSBC UK statement below to generate balanced, import-ready Xero, Sage Business Cloud, or Excel CSVs in 2 seconds."
        elif "barclays" in slug:
            default_cta_sub = "Don't waste hours untangling multi-line BGC descriptions in Excel. Drop your Barclays PDF statement below to generate balanced, import-ready FreeAgent, Xero, or Excel CSVs in 2 seconds."
        elif "commbank" in slug:
            default_cta_sub = "Don't waste hours untangling CommBiz multi-line PayID descriptions in Excel. Drop your CommBank statement below to generate balanced, import-ready Xero, MYOB, or Excel CSVs in 2 seconds."
        else:
            default_cta_sub = "Don't waste hours manually restructuring CSV rows in Excel. Drop your bank statement below to generate balanced, import-ready Sage Pastel, Xero, or Excel files in 2 seconds."
            
        cta_sub = guide.get("cta_sub", default_cta_sub)

        if country == "US":
            page_lang = "en-US"
            geo_region = "US-NY"
            geo_placename = "New York, United States"
            og_locale = "en_US"
            target_audience = "US Small Business, CPAs &amp; Bookkeepers"
            cta_badge = "100% In-Browser RAM Processing &bull; Zero Server Uploads &bull; GLBA &amp; SOC2 Privacy Compliant"
            compliance_box_html = """<div class="popia-box" style="background:#f0f9ff;border-color:#bae6fd;border-left-color:#0284c7">
        <h4 style="color:#0369a1">Client Data Privacy Notice for US CPAs &amp; Bookkeepers</h4>
        <p style="color:#075985">Under the FTC Safeguards Rule and Gramm-Leach-Bliley Act (GLBA), uploading unredacted client bank statements to unvetted cloud PDF converters creates serious regulatory and cyber-insurance liabilities. TaxClean parses statements 100% client-side in your workstation's browser RAM—no financial data is ever transmitted to an external server.</p>
      </div>"""
            related_heading = "Related Accounting &amp; Bank Statement Guides"
            footer_brand_summary = '<strong style="color:#fff; font-size:16px;">TaxClean Global</strong> &bull; Local Browser Bank Statement Converter &bull; 100% On-Device Privacy'
            footer_privacy_link = '<a href="/privacy.html">Privacy Policy</a>'
            footer_trademark_note = '&copy; 2026 TaxClean Technologies. All trademarks (Bank of America, Chase, QuickBooks, Xero) belong to their respective owners.'
        elif country == "GB":
            page_lang = "en-GB"
            geo_region = "GB-ENG"
            geo_placename = "London, United Kingdom"
            og_locale = "en_GB"
            target_audience = "UK Accounting, Bookkeeping &amp; HMRC MTD Compliance"
            cta_badge = "100% In-Browser RAM Processing &bull; Zero Server Uploads &bull; UK GDPR &amp; DPA 2018 Compliant"
            compliance_box_html = """<div class="popia-box" style="background:#f0f9ff;border-color:#bae6fd;border-left-color:#0284c7">
        <h4 style="color:#0369a1">UK GDPR &amp; ICAEW / AAT Data Privacy Notice</h4>
        <p style="color:#075985">Under the UK General Data Protection Regulation (UK GDPR) and the Data Protection Act 2018, transferring unencrypted client banking records to cloud PDF processors violates statutory client confidentiality obligations. TaxClean operates entirely within your local browser memory—client financial data never departs your UK workstation.</p>
      </div>"""
            related_heading = "Related UK &amp; International Bank Statement Guides"
            footer_brand_summary = '<strong style="color:#fff; font-size:16px;">TaxClean Global</strong> &bull; Local Browser Bank Statement Converter &bull; 100% On-Device Privacy'
            footer_privacy_link = '<a href="/privacy.html">Privacy Policy</a>'
            footer_trademark_note = '&copy; 2026 TaxClean Technologies. All trademarks (HSBC, Barclays, Xero, Sage, FreeAgent) belong to their respective owners.'
        elif country == "AU":
            page_lang = "en-AU"
            geo_region = "AU-NSW"
            geo_placename = "Sydney, Melbourne, Brisbane, Australia"
            og_locale = "en_AU"
            target_audience = "Australian Small Business, Bookkeepers &amp; ATO BAS Compliance"
            cta_badge = "100% In-Browser RAM Processing &bull; Zero Server Uploads &bull; Australian Privacy Act 1988 &amp; TASA Compliant"
            compliance_box_html = """<div class="popia-box" style="background:#f0fdf4;border-color:#bbf7d0;border-left-color:#16a34a">
        <h4 style="color:#15803d">Australian Privacy Principles (APPs) &amp; Client Data Protection Notice</h4>
        <p style="color:#166534">Under the Australian Privacy Act 1988 (Cth) and Tax Agent Services Act 2009 (TASA Code of Professional Conduct s 50), tax agents and bookkeepers must protect confidential client records from unauthorized offshore data transfer. TaxClean parses statements 100% client-side in your workstation's browser memory—client financial data never departs your device.</p>
      </div>"""
            related_heading = "Related Australian &amp; International Bank Statement Guides"
            footer_brand_summary = '<strong style="color:#fff; font-size:16px;">TaxClean Global</strong> &bull; Local Browser Bank Statement Converter &bull; 100% On-Device Privacy'
            footer_privacy_link = '<a href="/privacy.html">Privacy Policy</a>'
            footer_trademark_note = '&copy; 2026 TaxClean Technologies. All trademarks (CommBank, CommBiz, MYOB, Xero) belong to their respective owners.'
        else:
            page_lang = "en-ZA"
            geo_region = "ZA-KZN"
            geo_placename = "Johannesburg, Cape Town, Durban, Pretoria, Port Shepstone, South Africa"
            og_locale = "en_ZA"
            target_audience = "South African Accounting &amp; Bookkeeping"
            cta_badge = "100% In-Browser RAM Processing &bull; Zero Server Uploads &bull; POPIA Compliant"
            compliance_box_html = """<div class="popia-box">
        <h4>POPIA Notice for South African Accountants &amp; Bookkeepers</h4>
        <p>Under Section 72 of the Protection of Personal Information Act (POPIA Act 4 of 2013), transferring client bank records outside South Africa without strict data agreements creates major legal liabilities. TaxClean executes 100% locally in your device's browser memory—no client transaction data ever touches an external server.</p>
      </div>"""
            related_heading = "Related South African Bank Statement Guides"
            footer_brand_summary = '<strong style="color:#fff; font-size:16px;">TaxClean</strong> &bull; Local Browser Bank Statement Converter &bull; Port Shepstone, KZN'
            footer_privacy_link = '<a href="/privacy.html">POPIA &amp; Privacy</a>'
            footer_trademark_note = '&copy; 2026 TaxClean Technologies. All trademarks (Sage, Pastel, Xero, QuickBooks, Capitec, FNB, Nedbank, Standard Bank, Absa, Discovery) belong to their respective owners.'

        page_html = PAGE_TEMPLATE.format(
            meta_title=guide["meta_title"],
            meta_desc=guide["meta_desc"],
            meta_keywords=guide["meta_keywords"],
            canonical_url=canonical,
            schema_json=schema_json,
            breadcrumb_title=guide["breadcrumb_title"],
            guide_category=guide["guide_category"],
            h1_title=guide["h1_title"],
            direct_answer=guide["direct_answer"],
            cta_text=guide["cta_text"],
            cta_link=guide["cta_link"],
            cta_sub=cta_sub,
            cta_badge=cta_badge,
            compliance_box_html=compliance_box_html,
            related_heading=related_heading,
            page_lang=page_lang,
            geo_region=geo_region,
            geo_placename=geo_placename,
            og_locale=og_locale,
            target_audience=target_audience,
            footer_brand_summary=footer_brand_summary,
            footer_privacy_link=footer_privacy_link,
            footer_trademark_note=footer_trademark_note,
            article_body_html=guide["article_body_html"],
            faq_html=faq_html,
            related_guides_html=related_html
        )

        out_path = os.path.join(OUTPUT_DIR, f"{guide['slug']}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page_html)
        print(f"Generated Guide: {out_path}")
        created_urls.append(canonical)

    # 3. Update Sitemap
    update_sitemap(created_urls)

    # 4. Trigger IndexNow API Ping
    ping_indexnow(created_urls)
    print("SEO & AEO Guide Generation Complete!")

if __name__ == "__main__":
    main()

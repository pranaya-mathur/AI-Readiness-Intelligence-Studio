import io
import logging
from datetime import datetime
from typing import Dict, Any, List
from xhtml2pdf import pisa
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from pptx import Presentation
from pptx.util import Inches as PtInches, Pt as PtFont
from pptx.dml.color import RGBColor as PptRGBColor

logger = logging.getLogger("DocumentGenerators")

class DocumentGenerators:
    @staticmethod
    def _summary_text(assessment: dict) -> str:
        return (
            assessment.get("client_summary")
            or assessment.get("business_summary")
            or "A comprehensive audit mapping corporate structures, manual workflows, and high-impact automated opportunities."
        )

    @staticmethod
    def _approval_label(assessment: dict) -> str:
        return (assessment.get("approval_status") or "draft").replace("_", " ").title()

    @staticmethod
    def _report_date() -> str:
        return datetime.now().strftime("%B %d, %Y")

    @staticmethod
    def _signal_lines(assessment: Dict[str, Any], limit: int = 3) -> List[str]:
        lines = []
        for signal in assessment.get("extracted_signals", [])[:limit]:
            lines.append(
                f"{signal.get('signal_type')}: {signal.get('description')} "
                f"(Source: {signal.get('source_file')}, Confidence: {signal.get('confidence', 0)}%)"
            )
        return lines

    @staticmethod
    def generate_pdf_report(assessment: Dict[str, Any]) -> io.BytesIO:
        """
        Generates a premium CSS-styled PDF report summarizing the assessment.
        """
        logger.info(f"Generating PDF for {assessment.get('company_name')}...")
        
        # Build CSS-rich HTML layout
        html_content = f"""
        <html>
        <head>
            <style>
                @page {{
                    size: letter;
                    margin: 1in;
                }}
                body {{
                    font-family: Arial, sans-serif;
                    color: #1e293b;
                    line-height: 1.6;
                }}
                .header-container {{
                    text-align: center;
                    border-bottom: 2px solid #3b82f6;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                .logo-tagline {{
                    font-size: 11pt;
                    color: #3b82f6;
                    font-weight: bold;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .main-title {{
                    font-size: 26pt;
                    color: #0f172a;
                    margin: 10px 0;
                    font-weight: 800;
                }}
                .tagline {{
                    font-style: italic;
                    color: #64748b;
                    margin-bottom: 20px;
                }}
                .section {{
                    margin-top: 30px;
                    page-break-inside: avoid;
                }}
                .section-title {{
                    font-size: 16pt;
                    color: #0f172a;
                    border-left: 4px solid #3b82f6;
                    padding-left: 10px;
                    margin-bottom: 15px;
                }}
                .grid-2 {{
                    width: 100%;
                    border-spacing: 15px;
                }}
                .grid-cell {{
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 15px;
                    vertical-align: top;
                }}
                .score-circle {{
                    background: #3b82f6;
                    color: white;
                    border-radius: 50%;
                    width: 80px;
                    height: 80px;
                    text-align: center;
                    font-size: 24pt;
                    font-weight: bold;
                    margin: 0 auto 10px auto;
                    padding-top: 15px;
                }}
                .score-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                .score-table th, .score-table td {{
                    padding: 8px;
                    border-bottom: 1px solid #e2e8f0;
                    text-align: left;
                }}
                .score-bar {{
                    background: #3b82f6;
                    height: 12px;
                    border-radius: 6px;
                }}
                .score-bg {{
                    background: #e2e8f0;
                    width: 100px;
                    height: 12px;
                    border-radius: 6px;
                }}
                .badge {{
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-size: 8pt;
                    font-weight: bold;
                    color: white;
                }}
                .badge-p1 {{ background: #ef4444; }}
                .badge-p2 {{ background: #f59e0b; }}
                .badge-high {{ background: #10b981; }}
                .badge-med {{ background: #3b82f6; }}
            </style>
        </head>
        <body>
            <div class="header-container">
                <div class="logo-tagline">AI Readiness Intelligence Studio</div>
                <div class="main-title">AI Transformation Roadmap</div>
                <div class="tagline">“From business documents to AI opportunity roadmap in minutes.”</div>
                <p>Prepared for: <strong>{assessment.get('company_name')}</strong> &nbsp;|&nbsp; Date: {DocumentGenerators._report_date()} &nbsp;|&nbsp; Review Status: {DocumentGenerators._approval_label(assessment)}</p>
            </div>

            <div class="section">
                <div class="section-title">Executive Summary</div>
                <p>{DocumentGenerators._summary_text(assessment)}</p>
                
                <table class="grid-2">
                    <tr>
                        <td class="grid-cell" style="width: 35%; text-align: center;">
                            <div style="font-weight: bold; color: #64748b; margin-bottom: 10px;">Overall AI Readiness</div>
                            <div class="score-circle">{int(assessment.get('overall_score', 0))}</div>
                            <p style="font-size: 10pt; color: #475569;">Confidence level: {assessment.get('confidence_score', 85.0)}%</p>
                        </td>
                        <td class="grid-cell" style="width: 65%;">
                            <div style="font-weight: bold; color: #64748b; margin-bottom: 5px;">Transformation Impact</div>
                            <p style="margin: 0 0 10px 0;"><strong>Estimated Automation Potential:</strong> {int(assessment.get('automation_potential', 28))}%</p>
                            <p style="margin: 0 0 5px 0;"><strong>Recommended First Pilot:</strong> {assessment.get('recommended_first_pilot')}</p>
                            <p style="margin: 0; font-size: 9.5pt; color: #475569;">{assessment.get('why_recommended_pilot')}</p>
                        </td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <div class="section-title">AI Readiness Scores Breakdown</div>
                <table class="score-table">
                    <tr>
                        <th style="width: 40%;">Category</th>
                        <th style="width: 20%; text-align: center;">Score</th>
                        <th style="width: 40%;">Index Bar</th>
                    </tr>
                    {"".join(f'''
                    <tr>
                        <td>{category}</td>
                        <td style="text-align: center; font-weight: bold;">{int(score)}/100</td>
                        <td>
                            <div class="score-bg">
                                <div class="score-bar" style="width: {int(score)}px;"></div>
                            </div>
                        </td>
                    </tr>
                    ''' for category, score in [
                        ("Data Readiness", assessment.get("data_readiness", 0)),
                        ("Process Readiness", assessment.get("process_readiness", 0)),
                        ("Integration Readiness", assessment.get("integration_readiness", 0)),
                        ("Governance Readiness", assessment.get("governance_readiness", 0)),
                        ("Security Readiness", assessment.get("security_readiness", 0)),
                        ("Team Readiness", assessment.get("team_readiness", 0)),
                        ("Business Alignment", assessment.get("business_alignment", 0))
                    ])}
                </table>
                <p style="font-size: 9.5pt; color: #475569; margin-top: 15px;"><strong>Interpretation:</strong> {assessment.get('readiness_interpretation')}</p>
            </div>

            <div class="section" style="page-break-before: always;">
                <div class="section-title">Prioritized AI Use Case Catalog</div>
                <table class="score-table">
                    <tr style="background: #f8fafc;">
                        <th>Use Case Name</th>
                        <th>Department</th>
                        <th style="text-align: center;">Value</th>
                        <th style="text-align: center;">Priority</th>
                    </tr>
                    {"".join(f'''
                    <tr>
                        <td><strong>{u.get("use_case_name")}</strong><br/><span style="font-size: 8.5pt; color: #64748b;">{u.get("description")}</span></td>
                        <td>{u.get("department")}</td>
                        <td style="text-align: center;"><span class="badge badge-high">{u.get("value")}</span></td>
                        <td style="text-align: center;"><span class="badge badge-p1">{u.get("priority")}</span></td>
                    </tr>
                    ''' for u in assessment.get("use_cases", []))}
                </table>
            </div>

            <div class="section">
                <div class="section-title">Risk Register & Control Checklist</div>
                <table class="score-table">
                    <tr style="background: #f8fafc;">
                        <th>Risk Identified</th>
                        <th style="text-align: center;">Severity</th>
                        <th>Recommendation Control</th>
                    </tr>
                    {"".join(f'''
                    <tr>
                        <td><strong>{r.get("risk_name")}</strong></td>
                        <td style="text-align: center; color: #ef4444; font-weight: bold;">{r.get("severity")}</td>
                        <td>{r.get("recommendation")}</td>
                    </tr>
                    ''' for r in assessment.get("risks", []))}
                </table>
            </div>

            <div class="section">
                <div class="section-title">Evidence Basis</div>
                <table class="score-table">
                    <tr style="background: #f8fafc;">
                        <th>Extracted Signal</th>
                    </tr>
                    {"".join(f'''
                    <tr>
                        <td>{line}</td>
                    </tr>
                    ''' for line in (DocumentGenerators._signal_lines(assessment) or ["No extracted signals were available. This report is based on assessment inputs and generated recommendations."]))}
                </table>
            </div>

            <div class="section">
                <div class="section-title">90-Day Implementation Timeline</div>
                <table class="score-table">
                    <tr style="background: #f8fafc;">
                        <th style="width: 20%;">Phase</th>
                        <th style="width: 45%;">Action Item</th>
                        <th style="width: 35%;">Expected Impact</th>
                    </tr>
                    {"".join(f'''
                    <tr>
                        <td><strong>{item.get("phase")}</strong></td>
                        <td>{item.get("action_item")}</td>
                        <td>{item.get("expected_impact")}</td>
                    </tr>
                    ''' for item in assessment.get("roadmap_items", []))}
                </table>
            </div>
        </body>
        </html>
        """
        pdf_buffer = io.BytesIO()
        pisa.CreatePDF(html_content, dest=pdf_buffer)
        pdf_buffer.seek(0)
        return pdf_buffer

    @staticmethod
    def generate_docx_proposal(assessment: Dict[str, Any]) -> io.BytesIO:
        """
        Generates a professionally structured proposal in MS Word format.
        """
        logger.info(f"Generating DOCX for {assessment.get('company_name')}...")
        doc = Document()
        
        # Style Setup
        styles = doc.styles
        normal = styles['Normal']
        normal.font.name = 'Arial'
        normal.font.size = Pt(11)
        
        # Cover Page / Header
        title = doc.add_paragraph()
        title_run = title.add_run("AI Transformation Pilot Proposal")
        title_run.font.size = Pt(24)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(15, 23, 42)
        
        subtitle = doc.add_paragraph()
        sub_run = subtitle.add_run("“From business documents to AI opportunity roadmap in minutes.”")
        sub_run.font.size = Pt(12)
        sub_run.font.italic = True
        sub_run.font.color.rgb = RGBColor(100, 116, 139)
        
        doc.add_paragraph(
            f"Prepared For: {assessment.get('company_name')}\n"
            f"Date: {DocumentGenerators._report_date()}\n"
            f"Review Status: {DocumentGenerators._approval_label(assessment)}\n"
            "Studio Node Run: LangGraph Active"
        )
        doc.add_page_break()
        
        # Section 1: Executive Briefing
        h1 = doc.add_heading(level=1)
        h1_run = h1.add_run("1. Executive Summary")
        h1_run.font.color.rgb = RGBColor(59, 130, 246)
        
        doc.add_paragraph(DocumentGenerators._summary_text(assessment))
        
        # Pilot Callout
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.5)
        p.add_run("Recommended First Pilot Opportunity: ").bold = True
        p.add_run(f"{assessment.get('recommended_first_pilot')}\n")
        p.add_run("Why recommended: ").bold = True
        p.add_run(f"{assessment.get('why_recommended_pilot')}\n")
        p.add_run("Expected Impact: ").bold = True
        p.add_run(f"{assessment.get('expected_pilot_impact')}")
        
        # Section 2: Opportunities
        h2 = doc.add_heading(level=1)
        h2_run = h2.add_run("2. Prioritized Use Case Catalog")
        h2_run.font.color.rgb = RGBColor(59, 130, 246)
        
        # Use Case Table
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Light Shading Accent 1'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Use Case'
        hdr_cells[1].text = 'Department'
        hdr_cells[2].text = 'Value'
        hdr_cells[3].text = 'Priority'
        
        for u in assessment.get("use_cases", []):
            row_cells = table.add_row().cells
            row_cells[0].text = f"{u.get('use_case_name')}: {u.get('description')}"
            row_cells[1].text = u.get('department')
            row_cells[2].text = u.get('value')
            row_cells[3].text = u.get('priority')
            
        doc.add_page_break()

        h2b = doc.add_heading(level=1)
        h2b_run = h2b.add_run("3. Evidence Basis")
        h2b_run.font.color.rgb = RGBColor(59, 130, 246)

        evidence_lines = DocumentGenerators._signal_lines(assessment)
        if evidence_lines:
            for line in evidence_lines:
                doc.add_paragraph(line, style="List Bullet")
        else:
            doc.add_paragraph("No extracted signals were available. This proposal is based on assessment inputs and generated recommendations.")
        
        # Section 4: Roadmap
        h3 = doc.add_heading(level=1)
        h3_run = h3.add_run("4. 90-Day Implementation Roadmap")
        h3_run.font.color.rgb = RGBColor(59, 130, 246)
        
        for item in assessment.get("roadmap_items", []):
            dp = doc.add_paragraph()
            dp.add_run(f"[{item.get('phase')}] ").bold = True
            dp.add_run(f"{item.get('action_item')}\n")
            dp.add_run("Expected Impact: ").italic = True
            dp.add_run(f"{item.get('expected_impact')} (Confidence: {item.get('confidence') or 80}%)")
            
        docx_buffer = io.BytesIO()
        doc.save(docx_buffer)
        docx_buffer.seek(0)
        return docx_buffer

    @staticmethod
    def generate_pptx_deck(assessment: Dict[str, Any]) -> io.BytesIO:
        """
        Generates a modern slide presentation in PPTX format.
        """
        logger.info(f"Generating PPTX for {assessment.get('company_name')}...")
        prs = Presentation()
        
        # Slide 1: Cover Slide
        slide_layout = prs.slide_layouts[0] # Cover layout
        slide = prs.slides.add_slide(slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        
        title.text = f"AI Transformation Strategy\n{assessment.get('company_name')}"
        subtitle.text = "From business documents to AI opportunity roadmap in minutes.\nAI Readiness Intelligence Studio"
        
        # Slide 2: Executive Summary & Scores
        slide_layout = prs.slide_layouts[1] # Content layout
        slide = prs.slides.add_slide(slide_layout)
        title = slide.shapes.title
        title.text = "Executive Summary & Readiness Score"
        
        left = top = width = height = PtInches(1)
        txBox = slide.shapes.add_textbox(PtInches(1), PtInches(2), PtInches(8), PtInches(4.5))
        tf = txBox.text_frame
        
        p = tf.add_paragraph()
        p.text = f"Overall AI Readiness Score: {int(assessment.get('overall_score', 0))}/100"
        p.font.size = PtFont(20)
        p.font.bold = True
        
        p2 = tf.add_paragraph()
        p2.text = f"Business Summary: {DocumentGenerators._summary_text(assessment)}"
        p2.font.size = PtFont(14)
        
        p3 = tf.add_paragraph()
        p3.text = f"Recommended First Pilot: {assessment.get('recommended_first_pilot')}"
        p3.font.bold = True
        p3.font.size = PtFont(16)

        # Slide 3: Evidence basis
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = "Evidence Basis"
        txBox = slide.shapes.add_textbox(PtInches(0.8), PtInches(1.8), PtInches(8.5), PtInches(4.5))
        tf = txBox.text_frame
        evidence_lines = DocumentGenerators._signal_lines(assessment)
        if evidence_lines:
            for idx, line in enumerate(evidence_lines):
                paragraph = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
                paragraph.text = line
                paragraph.font.size = PtFont(16)
        else:
            tf.text = "No extracted signals were available. This deck is based on assessment inputs and generated recommendations."

        # Slide 4: Use Cases Matrix
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = "Prioritized AI Use Case Catalog"
        
        # Create a table for use cases
        rows = min(5, len(assessment.get("use_cases", [])) + 1)
        left = PtInches(0.5)
        top = PtInches(1.8)
        width = PtInches(9)
        height = PtInches(4)
        
        table_shape = slide.shapes.add_table(rows, 4, left, top, width, height)
        table = table_shape.table
        
        table.columns[0].width = PtInches(3)
        table.columns[1].width = PtInches(2)
        table.columns[2].width = PtInches(2)
        table.columns[3].width = PtInches(2)
        
        table.cell(0, 0).text = "Use Case Name"
        table.cell(0, 1).text = "Department"
        table.cell(0, 2).text = "Value"
        table.cell(0, 3).text = "Priority"
        
        for idx, u in enumerate(assessment.get("use_cases", [])[:rows-1]):
            table.cell(idx+1, 0).text = u.get("use_case_name")
            table.cell(idx+1, 1).text = u.get("department")
            table.cell(idx+1, 2).text = u.get("value")
            table.cell(idx+1, 3).text = u.get("priority")
            
        # Slide 5: Roadmap
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = "90-Day Implementation Roadmap"
        
        txBox = slide.shapes.add_textbox(PtInches(1), PtInches(2), PtInches(8), PtInches(4))
        tf = txBox.text_frame
        
        for idx, item in enumerate(assessment.get("roadmap_items", [])):
            p = tf.add_paragraph()
            p.text = f"Phase {item.get('phase')}: {item.get('action_item')}"
            p.font.bold = True
            p.font.size = PtFont(16)
            
            p_sub = tf.add_paragraph()
            p_sub.text = f"  Expected Impact: {item.get('expected_impact')}"
            p_sub.font.size = PtFont(13)
            
        pptx_buffer = io.BytesIO()
        prs.save(pptx_buffer)
        pptx_buffer.seek(0)
        return pptx_buffer

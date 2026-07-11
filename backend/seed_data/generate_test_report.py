"""
Script to generate a beautifully styled PDF blood report for testing TwinCare AI.
Saves the generated PDF to the workspace directory: test_blood_report.pdf
"""

import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_test_report_pdf(filename: str):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=15
    )
    
    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=12,
        spaceAfter=6,
        borderPadding=4
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['BodyText'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569')
    )

    story = []
    
    # Header Banner
    story.append(Paragraph("TwinCare Lab Diagnostics — Biomarker Report", title_style))
    story.append(Paragraph("<b>Patient Name:</b> John Doe &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Age:</b> 45 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Sex:</b> Male", body_style))
    story.append(Paragraph("<b>Report Date:</b> October 24, 2024 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Lab ID:</b> TC-884291-B", body_style))
    story.append(Spacer(1, 15))
    
    # Section: Lipid Panel
    story.append(Paragraph("LIPID PROFILE", section_style))
    lipid_data = [
        [Paragraph("Biomarker", header_style), Paragraph("Observed Value", header_style), Paragraph("Unit", header_style), Paragraph("Reference Range", header_style), Paragraph("Status", header_style)],
        [Paragraph("Total Cholesterol", body_style), Paragraph("242", body_style), Paragraph("mg/dL", body_style), Paragraph("125 - 200", body_style), Paragraph("<b>HIGH</b>", body_style)],
        [Paragraph("LDL Cholesterol", body_style), Paragraph("158", body_style), Paragraph("mg/dL", body_style), Paragraph("0 - 100", body_style), Paragraph("<b>HIGH</b>", body_style)],
        [Paragraph("HDL Cholesterol", body_style), Paragraph("42", body_style), Paragraph("mg/dL", body_style), Paragraph("40 - 100", body_style), Paragraph("Normal", body_style)],
        [Paragraph("Triglycerides", body_style), Paragraph("185", body_style), Paragraph("mg/dL", body_style), Paragraph("0 - 150", body_style), Paragraph("<b>HIGH</b>", body_style)],
    ]
    t_lipid = Table(lipid_data, colWidths=[2.2*inch, 1.2*inch, 0.8*inch, 1.8*inch, 1.2*inch])
    t_lipid.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(t_lipid)
    story.append(Spacer(1, 15))
    
    # Section: Blood Sugar
    story.append(Paragraph("GLYCEMIC INDEX & BLOOD GLUCOSE", section_style))
    sugar_data = [
        [Paragraph("Biomarker", header_style), Paragraph("Observed Value", header_style), Paragraph("Unit", header_style), Paragraph("Reference Range", header_style), Paragraph("Status", header_style)],
        [Paragraph("Fasting Glucose", body_style), Paragraph("112", body_style), Paragraph("mg/dL", body_style), Paragraph("70 - 100", body_style), Paragraph("<b>HIGH</b>", body_style)],
        [Paragraph("HbA1c", body_style), Paragraph("5.9", body_style), Paragraph("%", body_style), Paragraph("4.0 - 5.7", body_style), Paragraph("<b>HIGH</b>", body_style)],
    ]
    t_sugar = Table(sugar_data, colWidths=[2.2*inch, 1.2*inch, 0.8*inch, 1.8*inch, 1.2*inch])
    t_sugar.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(t_sugar)
    story.append(Spacer(1, 15))
    
    # Section: Vitals & Body Comp
    story.append(Paragraph("CLINICAL VITALS", section_style))
    vitals_data = [
        [Paragraph("Biomarker", header_style), Paragraph("Observed Value", header_style), Paragraph("Unit", header_style), Paragraph("Reference Range", header_style), Paragraph("Status", header_style)],
        [Paragraph("Systolic BP", body_style), Paragraph("145", body_style), Paragraph("mmHg", body_style), Paragraph("90 - 120", body_style), Paragraph("<b>HIGH</b>", body_style)],
        [Paragraph("Diastolic BP", body_style), Paragraph("90", body_style), Paragraph("mmHg", body_style), Paragraph("60 - 80", body_style), Paragraph("<b>HIGH</b>", body_style)],
        [Paragraph("BMI", body_style), Paragraph("28.5", body_style), Paragraph("kg/m2", body_style), Paragraph("18.5 - 24.9", body_style), Paragraph("<b>HIGH</b>", body_style)],
        [Paragraph("Heart Rate", body_style), Paragraph("78", body_style), Paragraph("bpm", body_style), Paragraph("60 - 100", body_style), Paragraph("Normal", body_style)],
    ]
    t_vitals = Table(vitals_data, colWidths=[2.2*inch, 1.2*inch, 0.8*inch, 1.8*inch, 1.2*inch])
    t_vitals.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(t_vitals)
    story.append(Spacer(1, 20))
    
    # Disclaimer
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748B')
    )
    story.append(Paragraph("Disclaimer: This report is a generated sample for clinical testing and system validation. All values represent standard physiological tests.", disclaimer_style))
    
    doc.build(story)
    print(f"✅ Created test blood report PDF at {filename}")

if __name__ == '__main__':
    create_test_report_pdf('/Users/abhisheksingh/Downloads/twincareai/test_blood_report.pdf')

"""
Creates a small synthetic dataset of emails + PDF attachments.
Run this once: python create_sample_data.py
"""
import os
import email.utils
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import io

os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/raw/attachments", exist_ok=True)


def make_pdf(filename, title, paragraphs):
    """Make a simple multi-page PDF."""
    path = f"data/raw/attachments/{filename}"
    doc = SimpleDocTemplate(path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles['Title']), Spacer(1, 20)]
    for p in paragraphs:
        story.append(Paragraph(p, styles['Normal']))
        story.append(Spacer(1, 12))
    doc.build(story)
    return path


def make_eml(filename, msg_id, in_reply_to, subject, sender, to, date, body, attachments=None):
    """Make a .eml file."""
    msg = MIMEMultipart()
    msg['Message-ID'] = f"<{msg_id}@enron-demo.com>"
    if in_reply_to:
        msg['In-Reply-To'] = f"<{in_reply_to}@enron-demo.com>"
        msg['References'] = f"<{in_reply_to}@enron-demo.com>"
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    msg['Date'] = email.utils.formatdate(email.utils.mktime_tz(email.utils.parsedate_tz(date)))
    msg.attach(MIMEText(body, 'plain'))

    if attachments:
        for att_path in attachments:
            with open(att_path, 'rb') as f:
                part = MIMEApplication(f.read(), _subtype='pdf')
            part.add_header('Content-Disposition', 'attachment',
                            filename=os.path.basename(att_path))
            msg.attach(part)

    with open(f"data/raw/{filename}", 'w') as f:
        f.write(msg.as_string())


# ===== THREAD 1: Storage Vendor Approval =====
pdf1 = make_pdf("storage_proposal_v1.pdf",
                "Storage Vendor Proposal - Draft v1",
                ["Vendor: DataSafe Storage Inc.",
                 "Initial proposed budget: $52,000 for Q3 storage infrastructure.",
                 "This is page one of the draft proposal.",
                 "PAGE BREAK",
                 "Page 2: Detailed breakdown includes 50TB storage, 24/7 support, and a 3-year warranty.",
                 "The draft proposal was prepared by the IT team on April 28, 2001."])

pdf2 = make_pdf("storage_approval_final.pdf",
                "Storage Vendor - Final Approval",
                ["Approved Vendor: DataSafe Storage Inc.",
                 "This is the final approval document.",
                 "PAGE BREAK",
                 "Final approved budget: $45,000 for Q3 2001 storage infrastructure.",
                 "Approved by: Finance Department, May 12, 2001.",
                 "The approval reduces the original budget by $7,000 after negotiation."])

make_eml("email_001.eml", "m_8f1", None,
         "Storage Vendor Proposal - Initial Review",
         "john.smith@enron.com", "finance@enron.com",
         "Mon, 30 Apr 2001 10:00:00 -0500",
         "Hi team,\n\nPlease find attached the initial draft proposal for the storage vendor.\nThe proposed budget is $52,000. Looking forward to your review.\n\nBest,\nJohn",
         [pdf1])

make_eml("email_002.eml", "m_8f2", "m_8f1",
         "Re: Storage Vendor Proposal - Initial Review",
         "sarah.jones@enron.com", "john.smith@enron.com",
         "Tue, 01 May 2001 14:30:00 -0500",
         "John,\n\nThe budget seems high. Can we negotiate down to around $45,000?\nFinance is concerned about the Q3 spend.\n\nSarah",
         None)

make_eml("email_003.eml", "m_8f3", "m_8f2",
         "Re: Storage Vendor Proposal - Initial Review",
         "john.smith@enron.com", "sarah.jones@enron.com",
         "Wed, 02 May 2001 09:15:00 -0500",
         "Sarah,\n\nI'll talk to DataSafe and try to negotiate. Will get back to you next week.\n\nJohn",
         None)

make_eml("email_004.eml", "m_9b2", "m_8f3",
         "Re: Storage Vendor Proposal - Initial Review",
         "john.smith@enron.com", "sarah.jones@enron.com, finance@enron.com",
         "Sat, 12 May 2001 16:45:00 -0500",
         "Team,\n\nGreat news! Finance has approved the storage vendor at $45,000.\nThe approval was sent today, May 12, 2001. Please find the final approval document attached.\n\nThanks for everyone's effort in negotiating this down.\n\nJohn",
         [pdf2])

# ===== THREAD 2: Q2 Budget Review =====
pdf3 = make_pdf("q2_budget_report.pdf",
                "Q2 2001 Budget Report",
                ["Q2 2001 Budget Summary",
                 "Total Q2 spend: $1,250,000",
                 "PAGE BREAK",
                 "Page 2: Department breakdown shows IT at $450,000, Operations at $500,000, Marketing at $300,000.",
                 "Variance from forecast: +3.2%."])

make_eml("email_005.eml", "m_a01", None,
         "Q2 Budget Review Meeting",
         "cfo@enron.com", "executives@enron.com",
         "Mon, 04 Jun 2001 09:00:00 -0500",
         "All,\n\nPlease review the attached Q2 budget report before our meeting on Friday.\n\nKey points:\n- Total spend: $1.25M\n- Slightly over forecast\n\nCFO",
         [pdf3])

make_eml("email_006.eml", "m_a02", "m_a01",
         "Re: Q2 Budget Review Meeting",
         "cto@enron.com", "cfo@enron.com",
         "Tue, 05 Jun 2001 11:20:00 -0500",
         "Reviewed the report. IT spend is on track. The 3.2% variance is mostly from unplanned infrastructure upgrades.\n\nCTO",
         None)

# ===== THREAD 3: Vendor Contract Renewal =====
pdf4 = make_pdf("contract_renewal.pdf",
                "Vendor Contract Renewal Terms",
                ["Vendor: TechSupport Solutions",
                 "Current contract expires: June 30, 2001.",
                 "PAGE BREAK",
                 "Page 2: Renewal terms - 12 months, $80,000 annual, 99.5% SLA.",
                 "Recommended action: Approve renewal with negotiated 5% discount."])

make_eml("email_007.eml", "m_b01", None,
         "Vendor Contract Renewal - TechSupport",
         "procurement@enron.com", "operations@enron.com",
         "Fri, 15 Jun 2001 13:00:00 -0500",
         "Hi,\n\nTechSupport Solutions contract is up for renewal. Attached is the renewal proposal.\nNew annual cost: $80,000.\n\nProcurement Team",
         [pdf4])

make_eml("email_008.eml", "m_b02", "m_b01",
         "Re: Vendor Contract Renewal - TechSupport",
         "operations@enron.com", "procurement@enron.com",
         "Mon, 18 Jun 2001 10:30:00 -0500",
         "Looks reasonable. Push for the 5% discount mentioned in the proposal.\n\nOps",
         None)

print("✓ Created 8 sample emails across 3 threads with 4 PDF attachments")
print("✓ Files saved to data/raw/")
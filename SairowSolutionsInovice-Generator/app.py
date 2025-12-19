import streamlit as st
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Circle
from reportlab.graphics import renderPDF
import io
import base64
import os

# Page configuration
st.set_page_config(
    page_title="Sairow Solutions - Invoice Generator",
    page_icon="📄",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #2E86AB;
        color: white;
        font-weight: bold;
        padding: 0.5rem;
        border-radius: 5px;
    }
    .invoice-header {
        text-align: center;
        color: #2E86AB;
        padding: 1rem;
        border-bottom: 3px solid #2E86AB;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'invoice_items' not in st.session_state:
    st.session_state.invoice_items = []
if 'invoice_number' not in st.session_state:
    st.session_state.invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-001"

# Header
st.markdown('<div class="invoice-header"><h1>🧾 Sairow Solutions Invoice Generator</h1></div>', unsafe_allow_html=True)

# Sidebar - Company Info ONLY
with st.sidebar:
    st.markdown("### 📋 Company Information")
    company_name = st.text_input("Company Name", "Sairow Solutions")
    company_address = st.text_area("Address", "Gilgit-Baltistan, Pakistan")
    company_phone = st.text_input("Phone", "+92-XXX-XXXXXXX")
    company_email = st.text_input("Email", "info@sairowsolutionsgb.com")
    company_website = st.text_input("Website", "www.sairowsolutionsgb.com")

# Main content area - Invoice and Client Details
st.subheader("📝 Invoice Details")
invoice_col1, invoice_col2 = st.columns(2)

with invoice_col1:
    invoice_number = st.text_input("Invoice Number", st.session_state.invoice_number)
with invoice_col2:
    invoice_date = st.date_input("Invoice Date", datetime.now())

st.divider()

# CLIENT INFORMATION IN MAIN AREA
st.subheader("👤 Client/Customer Information")
st.info("⚠️ Please fill in client details below to generate the invoice")

client_col1, client_col2 = st.columns(2)

with client_col1:
    client_name = st.text_input("Client Name *", "", placeholder="Enter client/customer name")
    client_phone = st.text_input("Client Phone", "", placeholder="+92-XXX-XXXXXXX")

with client_col2:
    client_email = st.text_input("Client Email", "", placeholder="client@example.com")
    client_address = st.text_area("Client Address", "", placeholder="Enter complete address")

st.divider()

# Add items section
st.subheader("➕ Add Items/Services")

item_col1, item_col2, item_col3, item_col4 = st.columns([3, 1, 1, 1])

with item_col1:
    item_name = st.text_input("Item/Service Description", key="item_name")
with item_col2:
    item_qty = st.number_input("Quantity", min_value=1, value=1, key="item_qty")
with item_col3:
    item_rate = st.number_input("Rate (PKR)", min_value=0.0, value=0.0, step=0.01, key="item_rate")
with item_col4:
    st.write("")
    st.write("")
    if st.button("Add Item"):
        if item_name and item_rate > 0:
            amount = item_qty * item_rate
            st.session_state.invoice_items.append({
                "Description": item_name,
                "Quantity": item_qty,
                "Rate": item_rate,
                "Amount": amount
            })
            st.success("Item added!")
            st.rerun()
        else:
            st.error("Please enter item description and rate")

# Display items table
if st.session_state.invoice_items:
    st.subheader("📊 Invoice Items")
    
    # Create dataframe
    df = pd.DataFrame(st.session_state.invoice_items)
    
    # Create a copy for display with formatted values
    display_df = df.copy()
    display_df['Rate'] = display_df['Rate'].apply(lambda x: f"PKR {x:,.2f}")
    display_df['Amount'] = display_df['Amount'].apply(lambda x: f"PKR {x:,.2f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Delete item functionality
    col_del1, col_del2 = st.columns([3, 1])
    with col_del2:
        if st.button("🗑️ Clear All Items"):
            st.session_state.invoice_items = []
            st.rerun()
    
    # Calculate totals
    subtotal = sum([item['Amount'] for item in st.session_state.invoice_items])
    
    st.divider()
    
    # Discount section
    col_calc1, col_calc2 = st.columns([2, 1])
    
    with col_calc2:
        st.subheader("💰 Invoice Summary")
        st.write(f"**Subtotal:** PKR {subtotal:,.2f}")
        
        discount_type = st.radio("Discount Type", ["Percentage (%)", "Fixed Amount (PKR)"], horizontal=True)
        
        if discount_type == "Percentage (%)":
            discount_percent = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
            discount_amount = (subtotal * discount_percent) / 100
        else:
            discount_amount = st.number_input("Discount Amount (PKR)", min_value=0.0, max_value=float(subtotal), value=0.0, step=0.01)
            discount_percent = (discount_amount / subtotal * 100) if subtotal > 0 else 0
        
        st.write(f"**Discount:** PKR {discount_amount:,.2f} ({discount_percent:.1f}%)")
        
        tax_percent = st.number_input("Tax/GST (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
        tax_amount = ((subtotal - discount_amount) * tax_percent) / 100
        
        st.write(f"**Tax ({tax_percent}%):** PKR {tax_amount:,.2f}")
        
        total = subtotal - discount_amount + tax_amount
        st.markdown(f"### **Total: PKR {total:,.2f}**")
        
        notes = st.text_area("Additional Notes", "Thank you for your business!")

# PDF Generation Function
def create_pdf(items, client_info, company_info, invoice_info, logo_path):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2E86AB'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        alignment=TA_CENTER
    )
    
    # Add logo if exists
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=80, height=80)
            img.hAlign = 'CENTER'
            elements.append(img)
            elements.append(Spacer(1, 10))
        except:
            pass
    
    # Company header
    elements.append(Paragraph(company_info['name'], title_style))
    elements.append(Paragraph(company_info['address'], header_style))
    elements.append(Paragraph(f"Phone: {company_info['phone']} | Email: {company_info['email']}", header_style))
    elements.append(Paragraph(f"Website: {company_info['website']}", header_style))
    elements.append(Spacer(1, 20))
    
    # Invoice title
    invoice_title = ParagraphStyle('InvoiceTitle', parent=styles['Heading2'], 
                                   fontSize=18, textColor=colors.HexColor('#2E86AB'))
    elements.append(Paragraph("INVOICE", invoice_title))
    elements.append(Spacer(1, 20))
    
    # Invoice details and client info
    info_data = [
        ['Invoice Number:', invoice_info['number'], 'Bill To:', client_info['name']],
        ['Invoice Date:', invoice_info['date'], 'Address:', client_info['address']],
        ['', '', 'Phone:', client_info['phone']],
        ['', '', 'Email:', client_info['email']]
    ]
    
    info_table = Table(info_data, colWidths=[1.5*inch, 2*inch, 1*inch, 2.5*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E86AB')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#2E86AB')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 30))
    
    # Items table
    table_data = [['Description', 'Quantity', 'Rate (PKR)', 'Amount (PKR)']]
    
    for item in items:
        table_data.append([
            item['Description'],
            str(item['Quantity']),
            f"{item['Rate']:,.2f}",
            f"{item['Amount']:,.2f}"
        ])
    
    item_table = Table(table_data, colWidths=[3.5*inch, 1*inch, 1.5*inch, 1.5*inch])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(item_table)
    elements.append(Spacer(1, 20))
    
    # Summary table
    summary_data = [
        ['Subtotal:', f"PKR {invoice_info['subtotal']:,.2f}"],
        ['Discount:', f"PKR {invoice_info['discount']:,.2f}"],
        ['Tax:', f"PKR {invoice_info['tax']:,.2f}"],
        ['Total:', f"PKR {invoice_info['total']:,.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[5.5*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#2E86AB')),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#2E86AB')),
        ('FONTSIZE', (0, 0), (-1, -2), 10),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Notes
    if invoice_info.get('notes'):
        elements.append(Paragraph(f"<b>Notes:</b> {invoice_info['notes']}", styles['Normal']))
        elements.append(Spacer(1, 20))
    
    # Bank Details Section
    elements.append(Spacer(1, 10))
    
    bank_title_style = ParagraphStyle(
        'BankTitle',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#2E86AB'),
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    elements.append(Paragraph("Payment Information", bank_title_style))
    
    # Bank details table
    bank_data = [
        ['Account Holder', 'Payment Method', 'Account Details'],
        ['Waqas Ali', 'Easypaisa', '03035330448'],
        ['Waqas Ali', 'SadaPay', 'PK30SADA0000003175079337'],
        ['Muhammad Ertaza Ali', 'Meezan Bank', 'Account: 03060107950315'],
        ['', '', 'IBAN: PK10MEZN0003060107950315']
    ]
    
    bank_table = Table(bank_data, colWidths=[2.2*inch, 2*inch, 3.3*inch])
    bank_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(bank_table)
    elements.append(Spacer(1, 20))
    
    # Footer note
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Paragraph("Thank you for your business! For any queries, please contact us.", footer_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Generate Invoice Button
if st.session_state.invoice_items and client_name:
    st.divider()
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn2:
        if st.button("🎯 Generate Invoice PDF", type="primary"):
            # Prepare data
            company_info = {
                'name': company_name,
                'address': company_address,
                'phone': company_phone,
                'email': company_email,
                'website': company_website
            }
            
            client_info = {
                'name': client_name,
                'address': client_address,
                'phone': client_phone,
                'email': client_email
            }
            
            invoice_info = {
                'number': invoice_number,
                'date': invoice_date.strftime('%B %d, %Y'),
                'subtotal': subtotal,
                'discount': discount_amount,
                'tax': tax_amount,
                'total': total,
                'notes': notes
            }
            
            # Generate PDF
            logo_path = "assets/SairowSolutionsGB logo.jpg"
            # Fallback to current directory if assets folder doesn't exist
            if not os.path.exists(logo_path):
                logo_path = "SairowSolutionsGB logo.jpg"
            pdf_buffer = create_pdf(st.session_state.invoice_items, client_info, company_info, invoice_info, logo_path)
            
            # Download button
            st.download_button(
                label="📥 Download Invoice PDF",
                data=pdf_buffer,
                file_name=f"Invoice_{invoice_number}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
            
            st.success("✅ Invoice generated successfully! Click the button above to download.")
            st.info("💡 **Tip:** You can print the downloaded PDF directly from your PDF viewer.")

elif not st.session_state.invoice_items:
    st.info("👆 Please add at least one item to generate an invoice.")
elif not client_name:
    st.error("⚠️ Please enter CLIENT NAME above in the 'Client/Customer Information' section to generate invoice!")

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p>Powered by <b>Sairow Solutions</b> | www.sairowsolutionsgb.com</p>
        <p style='font-size: 0.8rem;'>Professional Invoice Generator © 2024</p>
    </div>
""", unsafe_allow_html=True)
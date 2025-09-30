"""
PDF generation service for invoices and receipts
"""
import io
import structlog
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import base64

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from app.database import fetch_one
from app.utils.s3 import S3Service

logger = structlog.get_logger()


class PDFService:
    """Service for generating PDF invoices and receipts"""
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab not available, PDF generation will be limited")
        self.s3_service = S3Service()
    
    async def generate_invoice_pdf(self, invoice_id: str) -> Optional[str]:
        """Generate PDF for invoice and upload to S3"""
        try:
            if not REPORTLAB_AVAILABLE:
                return await self._generate_simple_pdf(invoice_id)
            
            # Get invoice data
            invoice_data = await self._get_invoice_data(invoice_id)
            if not invoice_data:
                raise ValueError("Invoice not found")
            
            # Generate PDF
            pdf_buffer = await self._create_invoice_pdf(invoice_data)
            
            # Upload to S3
            s3_key = f"invoices/{invoice_data['public_id']}/{invoice_data['invoice_number']}.pdf"
            pdf_url = await self.s3_service.upload_file(
                pdf_buffer.getvalue(),
                s3_key,
                content_type="application/pdf"
            )
            
            # Update invoice with PDF info
            from app.database import execute_query
            await execute_query(
                "UPDATE invoices SET pdf_s3_key = $1, pdf_url = $2 WHERE public_id = $3",
                (s3_key, pdf_url, invoice_id)
            )
            
            logger.info("Invoice PDF generated", invoice_id=invoice_id, s3_key=s3_key)
            return pdf_url
            
        except Exception as e:
            logger.error("Error generating invoice PDF", error=str(e), invoice_id=invoice_id)
            raise
    
    async def _get_invoice_data(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get complete invoice data for PDF generation"""
        query = """
            SELECT 
                i.*,
                p.period,
                p.due_date,
                p.notes as payment_notes,
                d.name as debtor_name,
                d.document_number,
                d.phone as debtor_phone,
                d.email as debtor_email,
                u.label as unit_label,
                u.floor,
                u.unit_type,
                c.code as currency_code,
                c.name as currency_name,
                pm.name as payment_method_name
            FROM invoices i
            JOIN payments p ON i.payment_id = p.id
            JOIN debtors d ON p.debtor_id = d.id
            LEFT JOIN leases l ON p.lease_id = l.id
            LEFT JOIN units u ON l.unit_id = u.id
            LEFT JOIN currencies c ON i.currency_id = c.id
            LEFT JOIN payment_methods pm ON pm.code = i.origin
            WHERE i.public_id = $1
        """
        
        return await fetch_one(query, (invoice_id,))
    
    async def _create_invoice_pdf(self, data: Dict[str, Any]) -> io.BytesIO:
        """Create PDF using ReportLab"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2563eb')
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#1f2937')
        )
        
        normal_style = styles['Normal']
        
        # Build PDF content
        story = []
        
        # Title
        story.append(Paragraph("FACTURA DE PAGO", title_style))
        story.append(Spacer(1, 20))
        
        # Invoice info table
        invoice_info = [
            ['Número de Factura:', data['invoice_number']],
            ['Fecha de Emisión:', data['created_at'].strftime('%d/%m/%Y')],
            ['Estado:', data['status']],
            ['Método de Pago:', data.get('payment_method_name', data['origin'])],
        ]
        
        if data.get('paid_at'):
            invoice_info.append(['Fecha de Pago:', data['paid_at'].strftime('%d/%m/%Y %H:%M')])
        
        invoice_table = Table(invoice_info, colWidths=[2*inch, 3*inch])
        invoice_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(invoice_table)
        story.append(Spacer(1, 30))
        
        # Debtor info
        story.append(Paragraph("INFORMACIÓN DEL INQUILINO", header_style))
        
        debtor_info = [
            ['Nombre:', data['debtor_name']],
            ['Documento:', data.get('document_number', 'N/A')],
            ['Teléfono:', data.get('debtor_phone', 'N/A')],
            ['Email:', data.get('debtor_email', 'N/A')],
        ]
        
        if data.get('unit_label'):
            debtor_info.append(['Unidad:', f"{data['unit_label']} - Piso {data.get('floor', 'N/A')}"])
        
        debtor_table = Table(debtor_info, colWidths=[2*inch, 3*inch])
        debtor_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(debtor_table)
        story.append(Spacer(1, 30))
        
        # Payment details
        story.append(Paragraph("DETALLE DEL PAGO", header_style))
        
        payment_details = [
            ['Concepto', 'Período', 'Monto'],
            [f'Alquiler - {data.get("unit_type", "Unidad")}', data['period'], f"{data['currency_code']} {data['amount']:.2f}"]
        ]
        
        payment_table = Table(payment_details, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(payment_table)
        story.append(Spacer(1, 30))
        
        # Total
        total_data = [
            ['TOTAL A PAGAR:', f"{data['currency_code']} {data['amount']:.2f}"]
        ]
        
        total_table = Table(total_data, colWidths=[4*inch, 2*inch])
        total_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#dbeafe')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e40af')),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#1e40af')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(total_table)
        story.append(Spacer(1, 40))
        
        # Footer
        footer_text = """
        <para align="center">
        <font size="8" color="#6b7280">
        Esta factura fue generada automáticamente por el Sistema de Alquileres<br/>
        Fecha de generación: {}<br/>
        ID de Factura: {}
        </font>
        </para>
        """.format(
            datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            data['public_id']
        )
        
        story.append(Paragraph(footer_text, normal_style))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    async def _generate_simple_pdf(self, invoice_id: str) -> Optional[str]:
        """Generate simple text-based PDF when ReportLab is not available"""
        try:
            # Get invoice data
            invoice_data = await self._get_invoice_data(invoice_id)
            if not invoice_data:
                raise ValueError("Invoice not found")
            
            # Create simple HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Factura {invoice_data['invoice_number']}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .header {{ text-align: center; color: #2563eb; margin-bottom: 30px; }}
                    .section {{ margin-bottom: 20px; }}
                    .label {{ font-weight: bold; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f3f4f6; }}
                    .total {{ background-color: #dbeafe; font-weight: bold; font-size: 18px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>FACTURA DE PAGO</h1>
                    <p>Número: {invoice_data['invoice_number']}</p>
                </div>
                
                <div class="section">
                    <h3>Información de la Factura</h3>
                    <p><span class="label">Fecha de Emisión:</span> {invoice_data['created_at'].strftime('%d/%m/%Y')}</p>
                    <p><span class="label">Estado:</span> {invoice_data['status']}</p>
                    <p><span class="label">Método de Pago:</span> {invoice_data.get('payment_method_name', invoice_data['origin'])}</p>
                </div>
                
                <div class="section">
                    <h3>Información del Inquilino</h3>
                    <p><span class="label">Nombre:</span> {invoice_data['debtor_name']}</p>
                    <p><span class="label">Documento:</span> {invoice_data.get('document_number', 'N/A')}</p>
                    <p><span class="label">Email:</span> {invoice_data.get('debtor_email', 'N/A')}</p>
                </div>
                
                <table>
                    <tr>
                        <th>Concepto</th>
                        <th>Período</th>
                        <th>Monto</th>
                    </tr>
                    <tr>
                        <td>Alquiler</td>
                        <td>{invoice_data['period']}</td>
                        <td>{invoice_data['currency_code']} {invoice_data['amount']:.2f}</td>
                    </tr>
                    <tr class="total">
                        <td colspan="2">TOTAL</td>
                        <td>{invoice_data['currency_code']} {invoice_data['amount']:.2f}</td>
                    </tr>
                </table>
                
                <div style="text-align: center; margin-top: 40px; font-size: 12px; color: #6b7280;">
                    Factura generada automáticamente - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
                </div>
            </body>
            </html>
            """
            
            # Convert HTML to PDF (simplified approach)
            # In a real implementation, you might use libraries like weasyprint or pdfkit
            
            # For now, save as HTML and return a mock URL
            s3_key = f"invoices/{invoice_data['public_id']}/{invoice_data['invoice_number']}.html"
            html_url = await self.s3_service.upload_file(
                html_content.encode('utf-8'),
                s3_key,
                content_type="text/html"
            )
            
            # Update invoice with PDF info
            from app.database import execute_query
            await execute_query(
                "UPDATE invoices SET pdf_s3_key = $1, pdf_url = $2 WHERE public_id = $3",
                (s3_key, html_url, invoice_id)
            )
            
            logger.info("Simple invoice HTML generated", invoice_id=invoice_id, s3_key=s3_key)
            return html_url
            
        except Exception as e:
            logger.error("Error generating simple PDF", error=str(e), invoice_id=invoice_id)
            raise

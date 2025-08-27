"""
PDF Report Generator for Oakville Real Estate Analyzer
Generates comprehensive property analysis reports in PDF format
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, PageTemplate, BaseDocTemplate
import io
from datetime import datetime
import os

class PropertyReportGenerator:
    """Generate professional PDF reports for property analysis"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
    def setup_custom_styles(self):
        """Setup custom paragraph styles for the report"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1E3A5F'),
            spaceAfter=12,
            alignment=TA_CENTER
        ))
        
        # Property Address style
        self.styles.add(ParagraphStyle(
            name='PropertyAddress',
            parent=self.styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#2E5090'),
            spaceAfter=6,
            alignment=TA_LEFT
        ))
        
        # Section Header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=14,
            textColor=colors.white,
            backColor=colors.HexColor('#4A6FA5'),
            spaceAfter=12,
            spaceBefore=12,
            alignment=TA_CENTER
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))
        
    def generate_property_report(self, property_data, output_buffer=None):
        """
        Generate a comprehensive property report PDF
        
        Args:
            property_data: Dictionary containing all property information
            output_buffer: BytesIO buffer for the PDF (if None, creates new)
        
        Returns:
            BytesIO buffer containing the PDF
        """
        if output_buffer is None:
            output_buffer = io.BytesIO()
            
        # Create the PDF document
        doc = SimpleDocTemplate(
            output_buffer,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.5*inch
        )
        
        # Build the content
        story = []
        
        # Add header with property address
        story.append(self._create_header(property_data))
        story.append(Spacer(1, 0.2*inch))
        
        # Add designation section
        story.append(self._create_designation_section(property_data))
        story.append(Spacer(1, 0.15*inch))
        
        # Create main content in two-column layout
        main_content = self._create_main_content(property_data)
        # main_content now returns a list of elements, so extend rather than append
        story.extend(main_content)
        story.append(Spacer(1, 0.15*inch))
        
        # Add Maximum Height section
        story.append(self._create_height_section(property_data))
        story.append(Spacer(1, 0.15*inch))
        
        # Add conservation authority section
        story.append(self._create_conservation_section(property_data))
        story.append(Spacer(1, 0.1*inch))
        
        # Add zone details and special provisions
        zone_details = self._create_zone_details_section(property_data)
        story.extend(zone_details)
        story.append(Spacer(1, 0.15*inch))
        
        # Add detailed analysis sections
        detailed_analysis = self._create_detailed_analysis(property_data)
        story.extend(detailed_analysis)
        
        # Add footer with generation info
        story.append(Spacer(1, 0.3*inch))
        story.append(self._create_footer())
        
        # Build the PDF
        doc.build(story)
        
        # Reset buffer position
        output_buffer.seek(0)
        return output_buffer
    
    def _create_header(self, data):
        """Create header with property address"""
        address = data.get('address', 'Property Address Not Available')
        city = data.get('city', 'Oakville, ON')
        
        header_data = [
            [Paragraph(f"<b>{address}</b>", self.styles['PropertyAddress'])],
            [Paragraph(city, self.styles['Normal'])]
        ]
        
        header_table = Table(header_data, colWidths=[7.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        return header_table
    
    def _create_designation_section(self, data):
        """Create designation section"""
        zone_code = data.get('zone_code', 'N/A')
        
        designation_data = [
            ['Designation', zone_code]
        ]
        
        designation_table = Table(designation_data, colWidths=[1.5*inch, 6*inch])
        designation_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#E0E0E0')),
            ('FONT', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONT', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (1, 0), 12),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        return designation_table
    
    def _create_main_content(self, data):
        """Create main content with two-column layout"""
        # Left column data
        left_column = []
        
        # Site Dimensions section
        dimensions_header = [['Site Dimensions', '']]
        left_column.append(self._create_section_table(dimensions_header, header=True))
        
        dimensions_data = [
            ['Lot Area', f"{data.get('lot_area', 'N/A')} m²"],
            ['Lot Frontage', f"{data.get('frontage', 'N/A')} m"],
            ['Lot Depth', f"{data.get('depth', 'N/A')} m"],
        ]
        left_column.append(self._create_section_table(dimensions_data))
        
        # Max RFA section
        rfa_header = [['Max RFA', '']]
        left_column.append(self._create_section_table(rfa_header, header=True))
        
        max_floor_area = data.get('max_floor_area', 'N/A')
        if max_floor_area != 'N/A':
            rfa_data = [
                ['Maximum Area', f"{max_floor_area:.2f} m²"],
                ['Maximum Area', f"{max_floor_area * 10.764:.2f} ft²"],
                ['Ratio', f"{data.get('max_far', 'N/A')}"],
            ]
        else:
            rfa_data = [
                ['Maximum Area', 'N/A'],
                ['Ratio', 'N/A'],
            ]
        left_column.append(self._create_section_table(rfa_data))
        
        # Building Size Limits section
        limits_header = [['Building Size Limits', '']]
        left_column.append(self._create_section_table(limits_header, header=True))
        
        limits_data = [
            ['Max Building Depth', f"{data.get('max_building_depth', 'N/A')} m"],
            ['Garage Projection', f"{data.get('garage_projection', 'N/A')} m"],
        ]
        left_column.append(self._create_section_table(limits_data))
        
        # Right column data
        right_column = []
        
        # Site Info section
        info_header = [['Site Info', '']]
        right_column.append(self._create_section_table(info_header, header=True))
        
        info_data = [
            ['Conservation', data.get('conservation_status', 'N/A')],
            ['Arborist', data.get('arborist_status', 'N/A')],
            ['Heritage', data.get('heritage_status', 'N/A')],
            ['Dev Apps', data.get('development_status', 'N/A')],
        ]
        right_column.append(self._create_section_table(info_data))
        
        # Max Coverage section
        coverage_header = [['Max Coverage', '']]
        right_column.append(self._create_section_table(coverage_header, header=True))
        
        coverage_area = data.get('max_coverage_area', 'N/A')
        if coverage_area != 'N/A':
            coverage_data = [
                ['Maximum Area', f"{coverage_area:.2f} m²"],
                ['Maximum Area', f"{coverage_area * 10.764:.2f} ft²"],
                ['Coverage %', f"{data.get('max_coverage_percent', 'N/A')}%"],
            ]
        else:
            coverage_data = [
                ['Maximum Area', 'N/A'],
                ['Coverage %', 'N/A'],
            ]
        right_column.append(self._create_section_table(coverage_data))
        
        # Minimum Setbacks section
        setbacks_header = [['Minimum Setbacks', '']]
        right_column.append(self._create_section_table(setbacks_header, header=True))
        
        setbacks = data.get('setbacks', {})
        front_yard = setbacks.get('front_yard', 'N/A')
        if front_yard == "-1":
            front_yard = "Existing -1"
            
        setbacks_data = [
            ['Minimum Front', f"{front_yard} m"],
            ['Maximum Front', f"Min + 5.5 m" if data.get('has_suffix_zero') else 'N/A'],
            ['Int Side L', f"{setbacks.get('interior_side_min', 'N/A')} m"],
            ['Int Side R', f"{setbacks.get('interior_side_max', 'N/A')} m"],
            ['Rear', f"{setbacks.get('rear_yard', 'N/A')} m"],
        ]
        right_column.append(self._create_section_table(setbacks_data))
        
        # For ReportLab, we need to combine the columns differently
        # Let's create side-by-side tables manually
        from reportlab.platypus import KeepTogether
        
        # Create a combined layout - return both columns as separate elements
        # This will require the calling method to handle the layout
        all_elements = []
        
        # Add left column elements
        for element in left_column:
            all_elements.append(element)
        
        # Add some space
        all_elements.append(Spacer(1, 0.1*inch))
        
        # Add right column elements  
        for element in right_column:
            all_elements.append(element)
            
        return all_elements
    
    def _create_section_table(self, data, header=False):
        """Create a section table with consistent styling"""
        if header:
            table = Table(data, colWidths=[3.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0E0E0')),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ]))
        else:
            table = Table(data, colWidths=[2*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (0, -1), 'Helvetica'),
                ('FONT', (1, 0), (1, -1), 'Helvetica'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
        
        return table
    
    def _create_height_section(self, data):
        """Create Maximum Height section"""
        height_header = [['Maximum Height', '', '', '']]
        height_data = [
            ['Building Height', 'Flat Roof', 'Eaves', 'Storeys'],
            [
                f"{data.get('max_height', 'N/A')} m",
                f"{data.get('flat_roof_height', 'N/A')} m",
                f"{data.get('eave_height', 'N/A')}",
                f"{data.get('max_storeys', 'N/A')}"
            ]
        ]
        
        height_table = Table(height_header + height_data, colWidths=[1.875*inch]*4)
        height_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0E0E0')),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 1), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        
        return height_table
    
    def _create_conservation_section(self, data):
        """Create Conservation Authority section"""
        conservation_header = [['Conservation Authority Information', '', '', '']]
        
        ca_info = data.get('conservation_authority', 'Unknown')
        
        conservation_data = [
            ['Authority', 'Status', 'Permits', 'Contact Required'],
            [
                ca_info.split(' - ')[0] if ' - ' in ca_info else ca_info,
                ca_info.split(' - ')[1] if ' - ' in ca_info else 'Check Required',
                'May be Required' if 'Halton' in ca_info else 'Unknown',
                'Yes' if 'Contact' in ca_info or 'Required' in ca_info else 'Possibly'
            ]
        ]
        
        conservation_table = Table(conservation_header + conservation_data, 
                                  colWidths=[1.875*inch, 1.875*inch, 1.875*inch, 1.875*inch])
        conservation_table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0E0E0')),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            
            # Subheader styling 
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F5F5F5')),
            ('FONT', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, 1), 9),
            
            # Data styling
            ('FONT', (0, 2), (-1, -1), 'Helvetica'),
            ('ALIGN', (0, 2), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 2), (-1, -1), 8),
            
            # Borders
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        return conservation_table
    
    def _format_coverage_value(self, value):
        """Safely format coverage value for display"""
        if value in ['N/A', None, '']:
            return 'N/A'
        try:
            # Try to convert to float and format as percentage
            float_val = float(value)
            return f"{float_val * 100:.0f}%"
        except (ValueError, TypeError):
            # If conversion fails, return the original value as string
            return str(value)
    
    def _create_zone_details_section(self, data):
        """Create Zone Details and Special Provisions section"""
        elements = []
        
        # Zone Information header
        zone_header = Paragraph('<b>Zone Details & Special Provisions</b>', self.styles['Heading2'])
        elements.append(zone_header)
        elements.append(Spacer(1, 0.1*inch))
        
        # Zone information table
        zone_info_data = [
            ['Zone Name', data.get('zone_name', 'N/A')],
            ['Zone Category', data.get('zone_category', 'N/A')],
        ]
        
        zone_info_table = Table(zone_info_data, colWidths=[2.5*inch, 4*inch])
        zone_info_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONT', (1, 0), (1, -1), 'Helvetica'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(zone_info_table)
        
        # Special Provisions section
        if data.get('special_provision'):
            elements.append(Spacer(1, 0.1*inch))
            
            sp_header = Paragraph('<b>Special Provisions Apply</b>', self.styles['Heading3'])
            elements.append(sp_header)
            
            sp_data = [
                ['Provision Code', data.get('special_provision', 'N/A')],
                ['Description', data.get('special_provision_description', 'Site-specific zoning requirements')],
            ]
            
            sp_table = Table(sp_data, colWidths=[2*inch, 4.5*inch])
            sp_table.setStyle(TableStyle([
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONT', (1, 0), (1, -1), 'Helvetica'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF8DC')),
            ]))
            elements.append(sp_table)
        
        # Suffix-0 Zone Details section
        if data.get('suffix_zero_details'):
            elements.append(Spacer(1, 0.1*inch))
            
            suffix_header = Paragraph('<b>Suffix-0 Zone Modifications</b>', self.styles['Heading3'])
            elements.append(suffix_header)
            
            suffix_details = data['suffix_zero_details']
            suffix_desc = Paragraph(suffix_details.get('description', 'Enhanced infill development permissions'), self.styles['Normal'])
            elements.append(suffix_desc)
            
            suffix_data = [
                ['Modification', 'Value', 'Note'],
                ['Front Yard Setback', 'Existing -1m', 'Reduced from standard'],
                ['Max Height', f"{suffix_details.get('max_height', 'N/A')}", 'Enhanced for infill'],
                ['Max Storeys', f"{suffix_details.get('max_storeys', 'N/A')}", 'May exceed standard'],
                ['Max Coverage', self._format_coverage_value(suffix_details.get('max_coverage', 'N/A')), 'Increased allowance'],
                ['Floor Area Ratio', f"{suffix_details.get('max_far', 'N/A')}", 'Enhanced density']
            ]
            
            suffix_table = Table(suffix_data, colWidths=[2*inch, 1.5*inch, 2*inch])
            suffix_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONT', (0, 1), (-1, -1), 'Helvetica'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (1, -1), 'CENTER'),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E6F3FF')),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F0F8FF')),
            ]))
            elements.append(suffix_table)
        
        # Permitted Uses section
        if data.get('permitted_uses'):
            elements.append(Spacer(1, 0.1*inch))
            
            uses_header = Paragraph('<b>Primary Permitted Uses</b>', self.styles['Heading3'])
            elements.append(uses_header)
            
            uses_text = ', '.join(data['permitted_uses'])
            uses_para = Paragraph(uses_text, self.styles['Normal'])
            elements.append(uses_para)
        
        return elements
    
    def _create_detailed_analysis(self, data):
        """Create detailed analysis sections"""
        story = []
        
        # Add Final Buildable Area Analysis if available
        if data.get('final_buildable_analysis'):
            story.append(PageBreak())
            story.append(Paragraph('<b>Final Buildable Floor Area Analysis</b>', self.styles['Heading1']))
            story.append(Spacer(1, 0.1*inch))
            
            analysis = data['final_buildable_analysis']
            
            # Summary box
            if analysis.get('final_buildable_sqft'):
                summary_text = f"""
                <b>Final Analysis Result:</b><br/>
                Based on our understanding and interpretation of the by-law, we are confident that you can build 
                a house of approximately <b>{analysis['final_buildable_sqft']:,.0f} sq. ft.</b> 
                ({analysis['final_buildable_sqm']:,.0f} sq. m.)
                <br/><br/>
                <b>Confidence Level:</b> {analysis.get('confidence_level', 'Moderate')}
                """
                story.append(Paragraph(summary_text, self.styles['Normal']))
                story.append(Spacer(1, 0.15*inch))
            
            # Calculation breakdown
            story.append(Paragraph('<b>Calculation Breakdown:</b>', self.styles['Heading2']))
            
            calc_data = [
                ['Calculation Method', analysis.get('calculation_method', 'Standard')],
                ['Lot Coverage', f"{analysis.get('lot_coverage_sqm', 0):,.2f} m² ({analysis.get('lot_coverage_sqft', 0):,.2f} sq ft)"],
                ['Max Floors', str(analysis.get('max_floors', 2))],
                ['Gross Floor Area', f"{analysis.get('gross_floor_area_sqft', 0):,.2f} sq ft"],
                ['Setback Deductions', f"{analysis.get('setback_deduction_sqft', 750):,.0f} sq ft"],
                ['Final Buildable Area', f"{analysis.get('final_buildable_sqft', 0):,.0f} sq ft"],
            ]
            
            calc_table = Table(calc_data, colWidths=[2.5*inch, 5*inch])
            calc_table.setStyle(TableStyle([
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F4FF')),
            ]))
            story.append(calc_table)
            story.append(Spacer(1, 0.1*inch))
            
            if analysis.get('analysis_note'):
                story.append(Paragraph(f"<i>{analysis['analysis_note']}</i>", self.styles['Normal']))
        
        # Add Zoning Compliance section
        if data.get('meets_requirements') is not None:
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph('<b>Zoning Compliance Status</b>', self.styles['Heading1']))
            
            if data['meets_requirements']:
                compliance_text = '<font color="green">✓ Property meets all minimum zoning requirements</font>'
            else:
                compliance_text = '<font color="red">✗ Property has zoning compliance issues</font>'
            
            story.append(Paragraph(compliance_text, self.styles['Normal']))
            
            # Add violations if any
            if data.get('violations'):
                story.append(Paragraph('<b>Violations:</b>', self.styles['Heading2']))
                for violation in data['violations']:
                    story.append(Paragraph(f"• {violation}", self.styles['Normal']))
            
            # Add warnings if any
            if data.get('warnings'):
                story.append(Paragraph('<b>Warnings:</b>', self.styles['Heading2']))
                for warning in data['warnings']:
                    story.append(Paragraph(f"• {warning}", self.styles['Normal']))
        
        # Add Special Requirements if available
        if data.get('special_requirements'):
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph('<b>Special Requirements</b>', self.styles['Heading1']))
            
            special_req = data['special_requirements']
            req_data = []
            
            for category, items in special_req.items():
                req_data.append([category, ', '.join(items) if isinstance(items, list) else str(items)])
            
            req_table = Table(req_data, colWidths=[2.5*inch, 5*inch])
            req_table.setStyle(TableStyle([
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(req_table)
        
        return story
    
    def _create_footer(self):
        """Create footer with generation information"""
        footer_text = f"""
        This information was collected by scaling online city mapping. 
        This information should be confirmed with an accurate survey.
        <br/>
        Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}
        <br/>
        Oakville Real Estate Analyzer - Professional Property Analysis System
        """
        
        footer_para = Paragraph(footer_text, self.styles['Footer'])
        
        footer_table = Table([[footer_para]], colWidths=[7.5*inch])
        footer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.grey),
        ]))
        
        return footer_table


def generate_property_pdf(property_data):
    """
    Generate a PDF report for property data
    
    Args:
        property_data: Dictionary containing all property information
        
    Returns:
        BytesIO buffer containing the PDF
    """
    generator = PropertyReportGenerator()
    return generator.generate_property_report(property_data)
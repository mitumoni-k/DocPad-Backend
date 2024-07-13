
import fitz
import re
import docx
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_summary_pdf(highlighted_texts_with_headings, output_path):
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    current_heading = None
    y_position = height - 40  # Initial position from the top

    # Setting up the styles
    styles = getSampleStyleSheet()
    bullet_style = ParagraphStyle(
        'Bullet', 
        parent=styles['Normal'], 
        leftIndent=20, 
        spaceAfter=10,
        fontName="Helvetica",
        fontSize=12
    )
    heading_style = ParagraphStyle(
        'Heading', 
        parent=styles['Heading1'], 
        spaceAfter=20,
        fontName="Helvetica-Bold",
        fontSize=14
    )

    for item in highlighted_texts_with_headings:
        if item['heading'] and item['heading'] != current_heading:
            paragraph = Paragraph(item['heading'], heading_style)
            w, h = paragraph.wrap(width - 80, y_position)
            
            if y_position - h < 40:  # Check if we need to start a new page
                c.showPage()
                y_position = height - 40
            
            # Draw the paragraph
            paragraph.drawOn(c, 40, y_position - h)
            y_position -= h + 10  # Move down for next item
            current_heading = item['heading']

        # Add text as a bullet point
        bullet_text = f"• {item['highlight']}"

        # Create a Paragraph object and wrap the text
        paragraph = Paragraph(bullet_text, bullet_style)
        w, h = paragraph.wrap(width - 80, y_position)
        
        if y_position - h < 40:  # Check if we need to start a new page
            c.showPage()
            y_position = height - 40
        
        # Draw the paragraph
        paragraph.drawOn(c, 60, y_position - h)
        y_position -= h + 10  # Move down for next bullet point

    c.save()
    return output_path


def extract_from_pdf(file_path):
    doc = fitz.open(file_path)
    
    def is_heading(span, prev_span):
        if prev_span and span['size'] > prev_span['size'] * 1.2:
            return True
        if span['flags'] & 2 or span['flags'] & 16:
            return True
        heading_patterns = [
            r'^[A-Z\d]+\.\s',
            r'^[A-Z][a-z]+\s*\d*:',
            r'^[A-Z\s]{3,}$'
        ]
        return any(re.match(pattern, span['text'].strip()) for pattern in heading_patterns)
    
    def get_heading(page, highlight_y0):
        text = page.get_text("dict")
        spans = []
        if "blocks" in text:
            for block in text["blocks"]:
                if "lines" in block and block["type"] == 0:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            spans.append({
                                "text": span["text"],
                                "size": span["size"],
                                "flags": span["flags"],
                                "y": span["bbox"][1]
                            })
        
        spans.sort(key=lambda x: x["y"])
        
        preceding_heading = None
        prev_span = None
        for span in spans:
            if span["y"] >= highlight_y0:
                break
            if is_heading(span, prev_span):
                preceding_heading = span["text"].strip()
            prev_span = span
        
        return preceding_heading
    
    highlighted_data = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        highlights = []
        annot = page.first_annot
        while annot:
            if annot.type[0] == 8:
                highlights.append(annot.rect)
            annot = annot.next
        
        all_words = page.get_text("words")
        
        for h in highlights:
            sentence = [w[4] for w in all_words if fitz.Rect(w[:4]).intersects(h)]
            if sentence:
                highlight_text = " ".join(sentence)
                heading = get_heading(page, h.y0)
                highlighted_data.append({"heading": heading, "highlight": highlight_text})
    
    return highlighted_data


def extract_from_docx(file_path):
    doc = docx.Document(file_path)
    highlighted_data = []
    current_heading = None
    
    for paragraph in doc.paragraphs:
        if paragraph.style.name.startswith('Heading'):
            current_heading = paragraph.text
        
        for run in paragraph.runs:
            if run.font.highlight_color:
                highlighted_data.append({"heading": current_heading, "highlight": run.text})
    
    return highlighted_data


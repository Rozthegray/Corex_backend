import re
import io
import markdown
from jinja2 import Environment, DictLoader
from weasyprint import HTML
from latex2mathml.converter import convert as tex2mathml

# Official Yaba College of Technology / NBTE HTML Cover Template
COVER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            size: A4;
            margin: 2.5cm 3cm;
            @bottom-center {
                content: counter(page);
                font-family: 'Times New Roman', serif;
                font-size: 11pt;
            }
        }
        body { 
            font-family: 'Times New Roman', serif; 
            line-height: 1.6; 
            color: #000; 
            font-size: 12pt;
        }
        
        /* Official Cover Page Formatting */
        .cover-page { 
            text-align: center; 
            page-break-after: always; 
            padding-top: 1.5cm; 
        }
        .inst-title { font-size: 20pt; font-weight: bold; text-transform: uppercase; margin-bottom: 0.2cm; }
        .inst-loc { font-size: 14pt; font-weight: bold; text-transform: uppercase; margin-bottom: 1.5cm; }
        
        .school-title { font-size: 16pt; font-weight: bold; text-transform: uppercase; margin-bottom: 0.2cm; }
        .dep-title { font-size: 16pt; font-weight: bold; text-transform: uppercase; margin-bottom: 2.5cm; }
        
        .doc-title { font-size: 16pt; font-weight: bold; text-transform: uppercase; margin-bottom: 2cm; text-decoration: underline; }
        
        .presented-by-label { font-size: 12pt; margin-bottom: 0.5cm; }
        .student-name { font-size: 14pt; font-weight: bold; text-transform: uppercase; }
        .matric-no { font-size: 14pt; font-weight: bold; text-transform: uppercase; margin-bottom: 2.5cm; }
        
        .fulfillment-text { font-size: 12pt; text-transform: uppercase; line-height: 1.5; margin-bottom: 2.5cm; width: 80%; margin-left: auto; margin-right: auto; }
        
        .lecturer-label { font-size: 12pt; margin-bottom: 0.2cm; }
        .lecturer-name { font-size: 14pt; font-weight: bold; text-transform: uppercase; margin-bottom: 2cm; }
        
        .date { font-size: 14pt; font-weight: bold; text-transform: uppercase; }

        /* Document Body Styling (Images & Math) */
        h1, h2, h3, h4 { font-family: 'Arial', sans-serif; font-weight: bold; }
        
        /* Ensure generative images and diagrams scale cleanly and don't break layout */
        img { 
            max-width: 100%; 
            max-height: 400px;
            display: block; 
            margin: 1.5em auto; 
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        
        pre { background: #f8f9fa; padding: 12px; border-radius: 4px; border: 1px solid #e9ecef; }
        code { font-family: 'Courier New', monospace; font-size: 10.5pt; }
        
        table { width: 100%; border-collapse: collapse; margin: 1.5em 0; }
        th, td { border: 1px solid #000; padding: 8px; text-align: left; }
        th { background-color: #f4f4f4; }
        
        math { font-family: 'Cambria Math', serif; font-size: 12pt; }
        math[display="block"] { display: block; text-align: center; margin: 1em 0; }
    </style>
</head>
<body>
    {% if include_cover %}
    <div class="cover-page">
        <div class="inst-title">Yaba College of Technology</div>
        <div class="inst-loc">Yaba, Lagos</div>
        
        <div class="school-title">School of Technology</div>
        <div class="dep-title">Department of Computer Engineering</div>
        
        <div class="doc-title">{{ course_code }}: {{ title }}</div>
        
        <div class="presented-by-label">PRESENTED BY:</div>
        <div class="student-name">{{ student_name }}</div>
        <div class="matric-no">MATRIC NO: {{ matric_number }}</div>
        
        <div class="fulfillment-text">
            Submitted in partial fulfillment of the requirements for the award of 
            <strong>{{ program_level }}</strong> in Computer Engineering.
        </div>
        
        <div class="lecturer-label">LECTURER / SUPERVISOR:</div>
        <div class="lecturer-name">{{ lecturer_name }}</div>
        
        <div class="date">{{ submission_date }}</div>
    </div>
    {% endif %}
    
    <div class="content">
        {{ body_html | safe }}
    </div>
</body>
</html>
"""

def process_latex_to_mathml(text: str) -> str:
    def replace_display(match):
        try: return tex2mathml(match.group(1), display="block")
        except: return match.group(0)
    text = re.sub(r'\$\$(.*?)\$\$', replace_display, text, flags=re.DOTALL)
    
    def replace_inline(match):
        try: return tex2mathml(match.group(1))
        except: return match.group(0)
    text = re.sub(r'\$(.*?)\$', replace_inline, text)
    return text

def compile_academic_pdf(
    markdown_content: str, 
    include_cover: bool = False,
    metadata: dict = None
) -> bytes:
    """
    Renders multimodal markdown (text, math, images) into a YABATECH formatted PDF.
    """
    math_processed_text = process_latex_to_mathml(markdown_content)
    
    # Enable tables, code blocks, and attributes for sizing images
    body_html = markdown.markdown(math_processed_text, extensions=['tables', 'fenced_code', 'attr_list'])
    
    env = Environment(loader=DictLoader({'cover': COVER_TEMPLATE}))
    template = env.get_template('cover')
    
    render_context = {
        "include_cover": include_cover,
        "body_html": body_html,
        "program_level": metadata.get("program_level", "HIGHER NATIONAL DIPLOMA (HND)"),
        **(metadata or {})
    }
    
    final_html = template.render(**render_context)
    pdf_buffer = io.BytesIO()
    
    # WeasyPrint automatically fetches external image URLs (e.g., Imgur, Cloudinary, Generative AI links)
    HTML(string=final_html).write_pdf(pdf_buffer)
    
    return pdf_buffer.getvalue()
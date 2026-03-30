"""
PDF 报告生成服务
优先级：
1. reportlab（轻量，纯Python，推荐）
2. 降级：生成带样式的 HTML 文件
安装：pip install reportlab
"""
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

REPORT_DIR = Path("uploads/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def markdown_to_plain(md: str) -> str:
    """将 Markdown 转换为纯文本（去除标记符）"""
    import re
    text = re.sub(r'^#{1,6}\s+', '', md, flags=re.MULTILINE)  # 去标题#
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)              # 去粗体
    text = re.sub(r'\*(.+?)\*', r'\1', text)                  # 去斜体
    text = re.sub(r'^---+$', '─' * 40, text, flags=re.MULTILINE)  # 分割线
    text = re.sub(r'^- ', '• ', text, flags=re.MULTILINE)     # 列表符
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)      # 链接
    return text


def generate_pdf(report_id: int, title: str, content: str) -> Optional[str]:
    """
    生成 PDF 报告，返回文件路径
    失败时返回 None
    """
    pdf_path = str(REPORT_DIR / f"report_{report_id}.pdf")

    # 方案1：使用 reportlab
    try:
        return _generate_with_reportlab(pdf_path, title, content)
    except ImportError:
        pass

    # 方案2：生成 HTML（可在浏览器打印为PDF）
    try:
        return _generate_html_report(report_id, title, content)
    except Exception:
        pass

    return None


def _generate_with_reportlab(pdf_path: str, title: str, content: str) -> str:
    """使用 reportlab 生成 PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # 尝试注册中文字体
    font_name = 'Helvetica'
    for font_path in [
        'C:/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/msyh.ttc',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('CJK', font_path))
                font_name = 'CJK'
                break
            except:
                pass

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontName=font_name, fontSize=18, spaceAfter=16,
        textColor=colors.HexColor('#1a202c')
    )
    style_h2 = ParagraphStyle(
        'H2', parent=styles['Heading2'],
        fontName=font_name, fontSize=13, spaceBefore=14, spaceAfter=6,
        textColor=colors.HexColor('#2d3447')
    )
    style_body = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName=font_name, fontSize=10, leading=16,
        textColor=colors.HexColor('#4a5568')
    )
    style_meta = ParagraphStyle(
        'Meta', parent=styles['Normal'],
        fontName=font_name, fontSize=9,
        textColor=colors.HexColor('#718096')
    )

    story = []
    story.append(Paragraph(title, style_title))
    story.append(Paragraph(f'生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}', style_meta))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=12))

    plain = markdown_to_plain(content)
    for line in plain.split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
        elif line.startswith('─'):
            story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
        elif len(line) < 50 and line.isupper() or (
            line.startswith('一、') or line.startswith('二、') or
            line.startswith('三、') or line.startswith('四、') or
            line.startswith('五、')
        ):
            story.append(Paragraph(line, style_h2))
        else:
            story.append(Paragraph(line, style_body))

    doc.build(story)
    return pdf_path


def _generate_html_report(report_id: int, title: str, content: str) -> str:
    """生成 HTML 报告（浏览器可打印为PDF）"""
    import re
    html_path = str(REPORT_DIR / f"report_{report_id}.html")

    # 简单 Markdown 转 HTML
    html_content = content
    html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
    html_content = re.sub(r'^---$', '<hr>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^- (.+)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'(<li>.+</li>\n?)+', lambda m: f'<ul>{m.group()}</ul>', html_content)
    html_content = html_content.replace('\n\n', '</p><p>')
    html_content = html_content.replace('\n', '<br>')

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{font-family: 'Microsoft YaHei', sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; color: #2d3447; line-height: 1.8;}}
h1 {{font-size: 22px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; color: #1a202c;}}
h2 {{font-size: 16px; color: #2d3447; margin-top: 24px;}}
hr {{border: none; border-top: 1px solid #e2e8f0; margin: 16px 0;}}
ul {{padding-left: 24px;}} li {{margin: 4px 0;}}
strong {{color: #1a202c;}}
.meta {{font-size: 12px; color: #718096; margin-bottom: 16px;}}
@media print {{body {{margin: 0; padding: 10px;}}}}
</style>
</head><body>
<div class="meta">生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
{html_content}
</body></html>"""

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return html_path

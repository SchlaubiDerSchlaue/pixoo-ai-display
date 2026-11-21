from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import base64
import io
import textwrap

SIZE = 64
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
THEMES = {
    'night': ('#07101E', '#58D7FF', '#FFFFFF', '#A4B3C4'),
    'green': ('#07190C', '#5CFF91', '#FFFFFF', '#B4D9BF'),
    'warm': ('#211008', '#FFB04D', '#FFFFFF', '#E1B79A'),
    'red': ('#210910', '#FF617F', '#FFFFFF', '#E9ABBA'),
}

def font(size, bold=False):
    return ImageFont.truetype(BOLD_PATH if bold else FONT_PATH, size)

def fit_lines(draw, text, max_width, sizes, max_lines):
    for size in sizes:
        f = font(size, True)
        lines = []
        for paragraph in str(text).split('\n'):
            words = paragraph.split()
            if not words:
                lines.append('')
                continue
            line = ''
            for word in words:
                proposed = f'{line} {word}'.strip()
                if draw.textbbox((0, 0), proposed, font=f)[2] <= max_width:
                    line = proposed
                else:
                    if line:
                        lines.append(line)
                    line = word
            if line:
                lines.append(line)
        if len(lines) <= max_lines and all(draw.textbbox((0,0), line, font=f)[2] <= max_width for line in lines):
            return lines, f
    # Explicit truncation rather than silently drawing beyond panel bounds
    f = font(sizes[-1], True)
    text = str(text).replace('\n', ' ')
    lines, current = [], ''
    for word in text.split():
        candidate = (current + ' ' + word).strip()
        if draw.textbbox((0,0),candidate,font=f)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    lines = lines[:max_lines]
    for i, line in enumerate(lines):
        while line and draw.textbbox((0,0),line,font=f)[2] > max_width:
            line = line[:-1]
        lines[i] = line
    if lines and len(text) > sum(len(s) for s in lines) + max(0,len(lines)-1):
        last = lines[-1]
        while last and draw.textbbox((0,0),last+'…',font=f)[2] > max_width:
            last = last[:-1]
        lines[-1] = last+'…'
    return lines, f

def render_card(title='', value='', footer='', theme='night'):
    if theme not in THEMES:
        raise ValueError('Unbekanntes Theme')
    bg, accent, primary, muted = THEMES[theme]
    image = Image.new('RGB', (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1,1,62,62), radius=5, outline=accent, width=1)
    draw.rectangle((5,5,58,7), fill=accent)
    title_lines, title_font = fit_lines(draw, title, 54, [9,8,7,6], 2)
    for i, line in enumerate(title_lines):
        bb = draw.textbbox((0,0), line, font=title_font)
        w = bb[2]-bb[0]
        draw.text(((64-w)/2,10+i*10),line, font=title_font, fill=accent)
    val_lines, val_font = fit_lines(draw, value, 55, [18,16,14,12,10,8], 2)
    val_height = len(val_lines)* (val_font.size+2)
    y = max(27, min(43-val_height//2, 36))
    for line in val_lines:
        bb=draw.textbbox((0,0), line,font=val_font)
        draw.text(((64-(bb[2]-bb[0]))/2,y),line,font=val_font,fill=primary)
        y += val_font.size+2
    if footer:
        footer_lines, footer_font=fit_lines(draw,footer,54,[7,6,5],1)
        if footer_lines:
            line=footer_lines[0]
            bb=draw.textbbox((0,0),line,font=footer_font)
            draw.text(((64-(bb[2]-bb[0]))/2,52),line,font=footer_font,fill=muted)
    return image

def render_message(text, theme='night'):
    if theme not in THEMES:
        raise ValueError('Unbekanntes Theme')
    bg,accent,primary,muted=THEMES[theme]
    image=Image.new('RGB',(SIZE,SIZE),bg)
    draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,63,3),fill=accent)
    lines,f=fit_lines(draw,text,58,[11,10,9,8,7,6],6)
    line_height=f.size+3
    y=max(7,(64-len(lines)*line_height)//2)
    for line in lines:
        bb=draw.textbbox((0,0),line,font=f)
        draw.text(((64-(bb[2]-bb[0]))/2,y),line,font=f,fill=primary)
        y+=line_height
    return image

def image_to_payload(image):
    return base64.b64encode(image.convert('RGB').tobytes()).decode('ascii')

def image_to_data_url(image, scale=6):
    output=io.BytesIO()
    image.resize((SIZE*scale,SIZE*scale), Image.Resampling.NEAREST).save(output,'PNG')
    return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode('ascii')

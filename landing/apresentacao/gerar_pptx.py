"""Gera a versão PPTX editável da apresentação da Capivara.

Uso:
    .venv/bin/python landing/apresentacao/gerar_pptx.py

Saída:
    data/output/Capivara-Apresentacao.pptx
"""

from pathlib import Path
import re

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

RAIZ = Path(__file__).resolve().parents[2]
IMG = RAIZ / "landing" / "capivara" / "assets" / "img"
ASSETS = Path("/tmp/capi-svg")
SAIDA = RAIZ / "data" / "output" / "Capivara-Apresentacao.pptx"

# ------------------------------------------------------------------ paleta
MARROM = RGBColor(0x9B, 0x6B, 0x43)
VERDE = RGBColor(0x1F, 0xA4, 0x63)
VERDE_FORTE = RGBColor(0x16, 0x8A, 0x52)
VERDE_CLARO = RGBColor(0x3F, 0xD0, 0x8A)
AMARELO = RGBColor(0xFF, 0xD8, 0x4D)
AZUL = RGBColor(0x1F, 0x5F, 0xD1)
VERMELHO = RGBColor(0xE5, 0x48, 0x4D)
TT_ACCENT = RGBColor(0xE9, 0x45, 0x60)

FUNDO = RGBColor(0xFA, 0xF6, 0xEF)
FUNDO_ALT = RGBColor(0xF3, 0xED, 0xE2)
SUPERFICIE = RGBColor(0xFF, 0xFF, 0xFF)
TEXTO = RGBColor(0x1C, 0x1B, 0x19)
TEXTO_SUAVE = RGBColor(0x5C, 0x57, 0x4F)
MATA = RGBColor(0x0E, 0x14, 0x11)
MATA_2 = RGBColor(0x12, 0x2A, 0x1D)
MATA_3 = RGBColor(0x18, 0x36, 0x25)
CODIGO = RGBColor(0x0A, 0x0F, 0x0C)
BORDA = RGBColor(0xE6, 0xDF, 0xD3)
BORDA_ESCURA = RGBColor(0x2A, 0x34, 0x2E)
CINZA_CLARO = RGBColor(0xA8, 0xB0, 0xA9)

TITULO = "Plus Jakarta Sans"
CORPO = "Inter"
MONO = "JetBrains Mono"

W, H = 1280, 720


def px(v):
    return Inches(v / 96)


def pt(v):
    return Pt(v * 0.75)


def add_rect(slide, x, y, w, h, fill=None, line=None, radius=0.12, line_width=1.0):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, px(x), px(y), px(w), px(h)
    )
    try:
        shape.adjustments[0] = radius
    except Exception:
        pass
    shape.shadow.inherit = False
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(line_width)
    return shape


def add_oval(slide, x, y, w, h, fill):
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, px(x), px(y), px(w), px(h))
    shape.shadow.inherit = False
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background()
    return shape


def add_line(slide, x1, y1, x2, y2, color=BORDA, width=0.75):
    line = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, px(x1), px(y1), px(x2), px(y2)
    )
    line.line.color.rgb = color
    line.line.width = Pt(width)
    return line


def _aplicar_fonte(run, size, color, font=CORPO, bold=False, italic=False):
    run.font.name = font
    run.font.size = pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color


def add_text(
    slide,
    x,
    y,
    w,
    h,
    text,
    size=14,
    color=TEXTO,
    font=CORPO,
    bold=False,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    line_spacing=1.08,
    margins=(0, 0, 0, 0),
    italic=False,
):
    tb = slide.shapes.add_textbox(px(x), px(y), px(w), px(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = px(margins[0])
    tf.margin_right = px(margins[1])
    tf.margin_top = px(margins[2])
    tf.margin_bottom = px(margins[3])
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = line_spacing
    r = p.add_run()
    r.text = text
    _aplicar_fonte(r, size, color, font, bold, italic)
    return tb


def _inline_runs(text, size, color, font=CORPO, bold=False):
    """Divide `texto` em runs; trechos entre crases viram código mono."""
    partes = text.split("`")
    runs = []
    for i, parte in enumerate(partes):
        if not parte:
            continue
        if i % 2 == 1:
            runs.append(
                {
                    "text": parte,
                    "font": MONO,
                    "size": size * 0.92,
                    "color": RGBColor(0x12, 0x7A, 0x48),
                    "bold": False,
                }
            )
        else:
            runs.append(
                {
                    "text": parte,
                    "font": font,
                    "size": size,
                    "color": color,
                    "bold": bold,
                }
            )
    return runs


def add_paras(
    slide,
    x,
    y,
    w,
    h,
    paras,
    anchor=MSO_ANCHOR.TOP,
    margins=(0, 0, 0, 0),
):
    tb = slide.shapes.add_textbox(px(x), px(y), px(w), px(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = px(margins[0])
    tf.margin_right = px(margins[1])
    tf.margin_top = px(margins[2])
    tf.margin_bottom = px(margins[3])
    tf.vertical_anchor = anchor
    for i, spec in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = spec.get("align", PP_ALIGN.LEFT)
        p.line_spacing = spec.get("line_spacing", 1.08)
        p.space_before = Pt(spec.get("space_before", 0))
        p.space_after = Pt(spec.get("space_after", 0))
        for rspec in spec["runs"]:
            r = p.add_run()
            r.text = rspec["text"]
            _aplicar_fonte(
                r,
                rspec.get("size", spec.get("size", 14)),
                rspec.get("color", spec.get("color", TEXTO)),
                rspec.get("font", spec.get("font", CORPO)),
                rspec.get("bold", spec.get("bold", False)),
                rspec.get("italic", False),
            )
            if rspec.get("link"):
                r.hyperlink.address = rspec["link"]
    return tb


def add_header(slide, eyebrow, title, y=52, sub=None, dark=False, title_size=44):
    add_text(
        slide,
        64,
        y,
        600,
        18,
        eyebrow.upper(),
        size=11,
        color=VERDE_CLARO if dark else VERDE,
        font=CORPO,
        bold=True,
    )
    add_text(
        slide,
        64,
        y + 15,
        1152,
        58,
        title,
        size=title_size,
        color=RGBColor(0xF2, 0xEE, 0xE7) if dark else TEXTO,
        font=TITULO,
        bold=True,
        line_spacing=1.0,
    )
    if sub:
        add_text(
            slide,
            64,
            y + 67,
            900,
            34,
            sub,
            size=15,
            color=CINZA_CLARO if dark else TEXTO_SUAVE,
            line_spacing=1.25,
        )


def add_footer(slide, texto, pagina, dark=False):
    cor_linha = BORDA_ESCURA if dark else BORDA
    cor_texto = RGBColor(0x7A, 0x85, 0x7D) if dark else TEXTO_SUAVE
    add_line(slide, 64, 674, 1216, 674, color=cor_linha, width=0.75)
    add_text(slide, 64, 682, 900, 16, texto, size=10.5, color=cor_texto)
    add_text(
        slide,
        1160,
        682,
        56,
        16,
        f"{pagina:02d}",
        size=10.5,
        color=cor_texto,
        font=MONO,
        align=PP_ALIGN.RIGHT,
    )


def add_pill(slide, x, y, w, h, texto, fill, color, size=10.5, bold=False):
    shape = add_rect(slide, x, y, w, h, fill=fill, line=None, radius=0.5)
    tf = shape.text_frame
    tf.word_wrap = False
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = texto
    _aplicar_fonte(r, size, color, CORPO, bold)
    return shape


def add_card(slide, x, y, w, h, kicker, titulo, corpo, dark=False, min_h=None):
    add_rect(slide, x, y, w, h, fill=SUPERFICIE, line=BORDA, radius=0.12)
    add_text(
        slide,
        x + 22,
        y + 20,
        80,
        14,
        kicker,
        size=9.5,
        color=VERDE_CLARO if dark else VERDE,
        font=MONO,
        bold=True,
    )
    add_text(
        slide,
        x + 22,
        y + 40,
        w - 44,
        28,
        titulo,
        size=21,
        color=TEXTO,
        font=TITULO,
        bold=True,
    )
    add_text(
        slide,
        x + 22,
        y + 75,
        w - 44,
        h - 90,
        corpo,
        size=14.5,
        color=TEXTO_SUAVE,
        line_spacing=1.18,
    )


def add_check_list(slide, x, y, w, h, itens, size=13.5, dark=False, gap=9):
    paras = []
    for item in itens:
        runs = [
            {
                "text": "✓  ",
                "font": CORPO,
                "size": size,
                "color": VERDE_CLARO if dark else VERDE,
                "bold": True,
            }
        ]
        runs.extend(_inline_runs(item, size, CINZA_CLARO if dark else TEXTO_SUAVE))
        paras.append({"runs": runs, "space_after": gap, "line_spacing": 1.16})
    return add_paras(slide, x, y, w, h, paras)


def add_code_block(slide, x, y, w, h, linhas, titulo=None, fonte=12):
    add_rect(slide, x, y, w, h, fill=CODIGO, line=BORDA_ESCURA, radius=0.04)
    if titulo:
        add_rect(slide, x, y, w, 30, fill=RGBColor(0x12, 0x18, 0x14), line=None, radius=0.04)
        add_oval(slide, x + 13, y + 11, 8, 8, RGBColor(0xFF, 0x5F, 0x57))
        add_oval(slide, x + 27, y + 11, 8, 8, RGBColor(0xFE, 0xBC, 0x2E))
        add_oval(slide, x + 41, y + 11, 8, 8, RGBColor(0x28, 0xC8, 0x40))
        add_text(
            slide,
            x + 58,
            y + 8,
            300,
            16,
            titulo,
            size=10,
            color=RGBColor(0x8A, 0x9A, 0x8F),
            font=MONO,
        )
        y_code = y + 44
        h_code = h - 54
    else:
        y_code = y + 16
        h_code = h - 26

    tb = slide.shapes.add_textbox(px(x + 18), px(y_code), px(w - 36), px(h_code))
    tf = tb.text_frame
    tf.word_wrap = False
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, linha in enumerate(linhas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.45
        p.space_after = Pt(0)
        _adicionar_runs_codigo(p, linha, fonte)


KEYWORDS = {"from", "import", "with", "as", "def", "return", "if", "else", "for", "in"}
COMENTARIO = RGBColor(0x6F, 0x8A, 0x7B)
AMARELO_CODIGO = RGBColor(0xFF, 0xD8, 0x4D)
VERDE_CODIGO = RGBColor(0x3F, 0xD0, 0x8A)
BRANCO_CODIGO = RGBColor(0xE6, 0xEF, 0xE9)


def _adicionar_runs_codigo(p, linha, fonte):
    if linha.strip().startswith("#"):
        r = p.add_run()
        r.text = linha
        _aplicar_fonte(r, fonte, COMENTARIO, MONO)
        return

    padrao = re.compile(r'("[^"]*"|\b(?:from|import|with|as|def|return|if|else|for|in)\b)')
    pos = 0
    for m in padrao.finditer(linha):
        if m.start() > pos:
            r = p.add_run()
            r.text = linha[pos : m.start()]
            _aplicar_fonte(r, fonte, BRANCO_CODIGO, MONO)
        token = m.group(0)
        r = p.add_run()
        r.text = token
        _aplicar_fonte(
            r,
            fonte,
            VERDE_CODIGO if token.startswith('"') else AMARELO_CODIGO,
            MONO,
        )
        pos = m.end()
    if pos < len(linha):
        r = p.add_run()
        r.text = linha[pos:]
        _aplicar_fonte(r, fonte, BRANCO_CODIGO, MONO)


def add_picture(slide, path, x, y, w=None, h=None, border=True):
    kwargs = {}
    if w is not None:
        kwargs["width"] = px(w)
    if h is not None:
        kwargs["height"] = px(h)
    pic = slide.shapes.add_picture(str(path), px(x), px(y), **kwargs)
    if border:
        pic.line.color.rgb = BORDA
        pic.line.width = Pt(1)
    return pic


def add_browser_chrome(slide, x, y, w, url):
    add_rect(slide, x, y, w, 30, fill=FUNDO_ALT, line=BORDA, radius=0.04)
    add_oval(slide, x + 11, y + 11, 8, 8, RGBColor(0xFF, 0x5F, 0x57))
    add_oval(slide, x + 25, y + 11, 8, 8, RGBColor(0xFE, 0xBC, 0x2E))
    add_oval(slide, x + 39, y + 11, 8, 8, RGBColor(0x28, 0xC8, 0x40))
    add_pill(
        slide,
        x + 58,
        y + 7,
        min(230, w - 80),
        16,
        url,
        SUPERFICIE,
        TEXTO_SUAVE,
        size=8,
    )


def slide_base(prs, dark=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = MATA if dark else FUNDO
    return slide


def slide_capa(prs):
    s = slide_base(prs, dark=True)
    add_oval(s, 760, 70, 520, 520, MATA_2)
    add_oval(s, 900, 220, 380, 380, MATA_3)

    add_picture(s, ASSETS / "favicon.png", 64, 44, w=34, h=34, border=False)
    add_text(s, 108, 50, 120, 24, "Capivara", size=20, color=RGBColor(0xF2, 0xEE, 0xE7), font=TITULO, bold=True)
    add_pill(s, 202, 52, 118, 20, "RPA EM PYTHON", RGBColor(0x1B, 0x2A, 0x21), CINZA_CLARO, size=8.5, bold=True)

    add_text(s, 64, 150, 600, 18, "APRESENTAÇÃO INSTITUCIONAL · 2026", size=11, color=VERDE_CLARO, bold=True)
    add_paras(
        s,
        64,
        172,
        650,
        180,
        [
            {"runs": [{"text": "Deixa que a", "size": 80, "color": RGBColor(0xF2, 0xEE, 0xE7), "font": TITULO, "bold": True}], "line_spacing": 0.96},
            {"runs": [{"text": "Capivara", "size": 80, "color": VERDE_CLARO, "font": TITULO, "bold": True}, {"text": " faz.", "size": 80, "color": RGBColor(0xF2, 0xEE, 0xE7), "font": TITULO, "bold": True}], "line_spacing": 0.96},
        ],
    )
    add_text(s, 64, 360, 540, 70, "Automação de processos com Python, 100% em português. Simples para começar, completa para ir à produção.", size=19, color=CINZA_CLARO, line_spacing=1.35)
    add_pill(s, 64, 450, 104, 30, "Python 3.11+", RGBColor(0x1B, 0x2A, 0x21), RGBColor(0xD8, 0xD4, 0xCB), size=11, bold=True)
    add_pill(s, 178, 450, 140, 30, "Open Source · MIT", RGBColor(0x1B, 0x2A, 0x21), RGBColor(0xD8, 0xD4, 0xCB), size=11, bold=True)
    add_pill(s, 328, 450, 104, 30, "100% PT-BR", RGBColor(0x1B, 0x2A, 0x21), RGBColor(0xD8, 0xD4, 0xCB), size=11, bold=True)

    add_picture(s, ASSETS / "capivara.png", 840, 225, w=300, border=False)
    add_mini_card(s, 1020, 255, 150, "Job #42", "concluído")
    add_mini_card(s, 810, 490, 140, "06:00", "seg a sex")
    add_mini_card(s, 980, 545, 165, "••••••••", "senha no cofre")
    add_footer(s, "github.com/capivara-rpa/capivara", 1, dark=True)


def add_mini_card(s, x, y, w, titulo, sub):
    add_rect(s, x, y, w, 52, fill=RGBColor(0x14, 0x1C, 0x17), line=RGBColor(0x2A, 0x3A, 0x30), radius=0.18)
    add_text(s, x + 13, y + 10, w - 26, 18, titulo, size=13, color=RGBColor(0xF2, 0xEE, 0xE7), font=MONO, bold=True)
    add_text(s, x + 13, y + 28, w - 26, 14, sub, size=9, color=CINZA_CLARO)


def slide_problema(prs):
    s = slide_base(prs)
    add_header(s, "O problema", "Trabalho repetitivo não precisa ser manual.", y=79, sub="Planilha, portal, e-mail, conferência. O time gasta horas em tarefas que não mudam de um dia para o outro.")
    y = 209
    w = 373
    add_card(s, 64, y, w, 230, "01", "Horas perdidas", "Copiar, colar e conferir dados consome o dia de quem poderia estar analisando, vendendo ou atendendo.")
    add_card(s, 453, y, w, 230, "02", "Ferramentas caras", "RPA tradicional cobra por robô, por licença e por consultoria. A conta não fecha para times pequenos.")
    add_card(s, 842, y, w, 230, "03", "Pouco controle", "Quando o robô roda escondido, ninguém sabe se falhou, quanto demorou ou quem acessou o quê.")

    add_rect(s, 64, 457, 520, 67, fill=FUNDO_ALT, line=BORDA, radius=0.16)
    add_text(s, 84, 469, 80, 12, "ANTES", size=9, color=TEXTO_SUAVE, font=MONO, bold=True)
    add_text(s, 84, 486, 480, 28, "Ctrl+C, Ctrl+V, planilha, e-mail e “alguém confere depois”.", size=13, color=TEXTO_SUAVE)
    add_text(s, 595, 475, 30, 30, "→", size=21, color=TEXTO_SUAVE, align=PP_ALIGN.CENTER)
    add_rect(s, 636, 457, 580, 67, fill=RGBColor(0xE8, 0xF4, 0xED), line=RGBColor(0xB7, 0xDD, 0xC8), radius=0.16)
    add_text(s, 656, 469, 160, 12, "COM CAPIVARA", size=9, color=VERDE, font=MONO, bold=True)
    add_text(s, 656, 486, 540, 28, "Um robô roda, registra cada passo e avisa quando termina.", size=13, color=RGBColor(0x2E, 0x6B, 0x4E))

    add_rect(s, 64, 542, 1152, 55, fill=RGBColor(0xFF, 0xF2, 0xC2), line=None, radius=0.0)
    add_text(s, 84, 558, 1110, 26, "“Automação não é sobre demitir. É sobre parar de contratar trabalho repetitivo.”", size=14, color=RGBColor(0x6B, 0x53, 0x10), bold=True)
    add_footer(s, "Capivara · Deixa que a Capivara faz.", 2)


def slide_oque(prs):
    s = slide_base(prs)
    add_header(s, "O que é", "RPA em Python, do jeito brasileiro.", y=84)
    add_text(s, 64, 182, 610, 95, "A Capivara transforma bibliotecas complexas em funções descritivas em português. Você escreve o processo; ela cuida do Selenium, pandas, requests e da orquestração.", size=19, color=TEXTO_SUAVE, line_spacing=1.35)
    add_check_list(
        s,
        64,
        294,
        610,
        280,
        [
            "**Low-code de verdade:** `abrir_url`, `clicar_elemento`, `ler_csv`, `enviar_email`.",
            "**Open source (MIT):** sem licença por robô, sem caixa-preta.",
            "**Lagoa completa:** agentes, filas, agendamentos, cofre e auditoria.",
            "**Do notebook à produção:** roda local, em servidor ou com instaladores sem Python.",
        ],
        size=14.5,
        gap=13,
    )

    add_stat(s, 710, 182, 235, 145, "600", "devs na comunidade")
    add_stat(s, 957, 182, 259, 145, "63", "ações de navegador em português")
    add_stat(s, 710, 340, 235, 145, "156", "testes automatizados")
    add_stat(s, 957, 340, 259, 145, "0", "Python para instalar a Lagoa")
    add_footer(s, "Feito no Brasil · código aberto", 3)


def add_stat(s, x, y, w, h, numero, label):
    add_rect(s, x, y, w, h, fill=SUPERFICIE, line=BORDA, radius=0.14)
    add_text(s, x + 20, y + 24, w - 40, 45, numero, size=38, color=VERDE, font=TITULO, bold=True)
    add_text(s, x + 20, y + 82, w - 40, 45, label, size=12, color=TEXTO_SUAVE, line_spacing=1.15)


def slide_como(prs):
    s = slide_base(prs)
    add_header(s, "Como funciona", "Três passos. Zero estresse.", y=91, sub="Do primeiro script ao robô rodando sozinho de madrugada — sem virar refém de ferramenta cara.")
    y = 221
    w = 373
    add_passo(s, 64, y, w, 290, "01", "Escreva", "Use funções que falam a sua língua. O Selenium, o pandas e o requests ficam por baixo dos panos.", 'nav.clicar_elemento("#entrar")')
    add_passo(s, 453, y, w, 290, "02", "Agende", "Intervalo, horário, cron, dias da semana, feriados e fila de itens. Cada robô pode rodar na máquina certa.", "seg a sex · 06:00")
    add_passo(s, 842, y, w, 290, "03", "Acompanhe", "Jobs, passos, erros e tempo em tempo real. O Monitor mostra o trace e a Lagoa mostra o negócio.", "Job #42 · concluído")

    add_band(s, 64, 531, 1152, 50, ["Menos erro manual", "Mais tempo útil", "Rastreabilidade"], ["O mesmo processo, sempre igual.", "O time cuida do que exige cabeça.", "Cada passo fica registrado."])
    add_footer(s, "Escreva · Agende · Acompanhe", 4)


def add_passo(s, x, y, w, h, num, titulo, corpo, trecho):
    add_rect(s, x, y, w, h, fill=SUPERFICIE, line=BORDA, radius=0.12)
    add_oval(s, x + 22, y + 22, 36, 36, AMARELO)
    add_text(s, x + 22, y + 30, 36, 16, num, size=12, color=TEXTO, font=TITULO, bold=True, align=PP_ALIGN.CENTER)
    add_text(s, x + 22, y + 72, w - 44, 30, titulo, size=24, color=TEXTO, font=TITULO, bold=True)
    add_text(s, x + 22, y + 108, w - 44, 95, corpo, size=14.5, color=TEXTO_SUAVE, line_spacing=1.18)
    add_rect(s, x + 22, y + 218, w - 44, 34, fill=FUNDO_ALT, line=None, radius=0.12)
    add_text(s, x + 32, y + 226, w - 64, 18, trecho, size=11, color=TEXTO, font=MONO)


def add_band(s, x, y, w, h, titulos, textos):
    add_rect(s, x, y, w, h, fill=FUNDO_ALT, line=BORDA, radius=0.14)
    col = w / 3
    for i, (t, d) in enumerate(zip(titulos, textos, strict=True)):
        cx = x + col * i + 18
        add_text(s, cx, y + 9, col - 36, 16, t, size=12.5, color=TEXTO, bold=True)
        add_text(s, cx, y + 26, col - 36, 16, d, size=11.5, color=TEXTO_SUAVE)


def slide_recursos(prs):
    s = slide_base(prs)
    add_header(s, "Recursos", "O kit completo para automatizar.", y=96)
    y = 194
    w = 373
    recursos = [
        ("WEB", "Navegador", "63 ações em português: clicar, ler, arrastar, iframe, download, captura e abas."),
        ("ORQ", "Lagoa", "Onde a mágica das capivaras acontece. Máquinas, processos, jobs e agentes no mesmo painel."),
        ("FILA", "Filas", "Itens com prioridade, retentativa, pausa e round-robin entre executores."),
        ("CRON", "Agendamentos", "Intervalo, diário, cron, dias úteis, fins de semana e feriados nacionais."),
        ("SAFE", "Cofre", "Credenciais cifradas, versões, rotação, permissão por processo e auditoria."),
        ("LOG", "Monitor", "Trace de execução, passos, níveis de log e status de cada robô."),
    ]
    for i, (k, t, d) in enumerate(recursos):
        col = i % 3
        row = i // 3
        add_recurso(s, 64 + col * 386, y + row * 158, w, 145, k, t, d)

    add_text(s, 64, 518, 700, 22, "Back office     Financeiro     Atendimento     Dados     Compliance", size=10.5, color=TEXTO_SUAVE, bold=True)
    add_rect(s, 64, 552, 1152, 50, fill=MATA, line=None, radius=0.14)
    add_text(s, 84, 568, 650, 20, "Sem licença por robô. Sem caixa-preta.", size=13, color=RGBColor(0xF2, 0xEE, 0xE7), font=TITULO, bold=True)
    add_text(s, 820, 568, 376, 20, "O motor é aberto; a operação é sua.", size=12, color=CINZA_CLARO, align=PP_ALIGN.RIGHT)
    add_footer(s, "Um motor, várias automações", 5)


def add_recurso(s, x, y, w, h, kicker, titulo, corpo):
    add_rect(s, x, y, w, h, fill=SUPERFICIE, line=BORDA, radius=0.12)
    add_pill(s, x + 19, y + 18, 42, 18, kicker, RGBColor(0xE8, 0xF4, 0xED), VERDE, size=8.5, bold=True)
    add_text(s, x + 19, y + 45, w - 38, 24, titulo, size=18, color=TEXTO, font=TITULO, bold=True)
    add_text(s, x + 19, y + 73, w - 38, h - 84, corpo, size=13, color=TEXTO_SUAVE, line_spacing=1.16)


def slide_codigo(prs):
    s = slide_base(prs, dark=True)
    add_header(s, "Código", "Python que se lê como português.", y=79, dark=True)
    add_text(s, 64, 188, 420, 85, "Sem decorar API. Sem 300 linhas de Selenium. O fluxo fica curto, legível e fácil de manter.", size=19, color=CINZA_CLARO, line_spacing=1.35)
    add_check_list(
        s,
        64,
        300,
        420,
        240,
        [
            "Funções em português com logs automáticos.",
            "Erros claros com `ErroRPA` e `ErroCriticoRPA`.",
            "Retry, espera e tratamento de exceção no motor.",
            "Roda igual no notebook e no servidor.",
        ],
        size=14.5,
        dark=True,
        gap=14,
    )
    linhas = [
        "# robô de login + captura",
        "from capivara_rpa import Navegador",
        "",
        "with Navegador() as nav:",
        '    nav.abrir_url("https://portal.exemplo.com")',
        '    nav.escrever_texto("#usuario", "ana")',
        '    nav.escrever_texto("#senha", senha)',
        '    nav.clicar_elemento("#entrar")',
        '    nav.aguardar_url_contem("/painel")',
        '    nav.capturar_tela("data/output/portal.png")',
        "",
        "# o log já registra cada passo",
    ]
    add_code_block(s, 520, 180, 696, 440, linhas, titulo="fluxos/portal.py", fonte=12)
    add_footer(s, "Menos código, mais processo", 6, dark=True)


def slide_tracktab(prs):
    s = slide_base(prs)
    add_header(s, "TrackTab", "Pare de caçar XPath no olho.", y=79)
    add_text(s, 64, 188, 440, 95, "Extensão de Chrome que grava os elementos enquanto você navega. Clique no que importa, exporte JSON e use direto no robô.", size=19, color=TEXTO_SUAVE, line_spacing=1.35)
    add_check_list(
        s,
        64,
        300,
        440,
        230,
        [
            "XPath completo, relativo e caminho customizado.",
            "JSON pronto para `core.rpa.tracktab`.",
            "Funciona com iframes e páginas dinâmicas.",
            "Instalação em `chrome://extensions`.",
        ],
        size=14.5,
        gap=13,
    )
    add_text(s, 64, 548, 440, 20, "Chrome Web Store em breve.", size=11, color=TEXTO_SUAVE, italic=True)

    # browser
    add_rect(s, 590, 190, 450, 340, fill=SUPERFICIE, line=BORDA, radius=0.12)
    add_browser_chrome(s, 590, 190, 450, "app.exemplo.com/login")
    add_text(s, 610, 238, 250, 24, "◎  Portal do time", size=16, color=TEXTO, font=TITULO, bold=True)
    add_text(s, 610, 278, 80, 14, "E-mail", size=9.5, color=TEXTO_SUAVE)
    add_rect(s, 610, 292, 350, 34, fill=SUPERFICIE, line=BORDA, radius=0.12)
    add_text(s, 620, 301, 330, 18, "ana@empresa.com", size=11.5, color=TEXTO)
    add_text(s, 610, 338, 80, 14, "Senha", size=9.5, color=TEXTO_SUAVE)
    add_rect(s, 610, 352, 350, 34, fill=SUPERFICIE, line=BORDA, radius=0.12)
    add_text(s, 620, 361, 330, 18, "••••••••", size=11.5, color=TEXTO)
    add_rect(s, 610, 402, 92, 36, fill=VERDE, line=None, radius=0.12)
    add_text(s, 610, 411, 92, 18, "Entrar", size=11.5, color=RGBColor(0xFF, 0xFF, 0xFF), bold=True, align=PP_ALIGN.CENTER)
    add_pill(s, 714, 408, 104, 24, "button.entrar", RGBColor(0xFC, 0xE8, 0xEB), TT_ACCENT, size=9.5, bold=True)

    # popup
    add_rect(s, 850, 350, 274, 230, fill=RGBColor(0x1A, 0x1A, 0x2E), line=RGBColor(0x2A, 0x2A, 0x4A), radius=0.12)
    add_text(s, 866, 366, 180, 20, "◎  TrackTab", size=13, color=RGBColor(0xE6, 0xE6, 0xE6), bold=True)
    add_pill(s, 1064, 366, 44, 16, "v1.0", RGBColor(0x16, 0x21, 0x3E), RGBColor(0xA0, 0xA0, 0xB0), size=8.5)
    add_rect(s, 866, 392, 242, 28, fill=RGBColor(0x16, 0x21, 0x3E), line=RGBColor(0x2A, 0x2A, 0x4A), radius=0.12)
    add_oval(s, 876, 402, 7, 7, TT_ACCENT)
    add_text(s, 890, 398, 200, 16, "Gravando elementos", size=9.5, color=RGBColor(0xA0, 0xA0, 0xB0))
    add_rect(s, 866, 428, 242, 28, fill=RGBColor(0x16, 0x21, 0x3E), line=RGBColor(0x2A, 0x2A, 0x4A), radius=0.12)
    add_text(s, 876, 434, 100, 16, "Capturados", size=8.5, color=RGBColor(0xA0, 0xA0, 0xB0))
    add_text(s, 1060, 431, 40, 20, "3", size=14, color=TT_ACCENT, bold=True, align=PP_ALIGN.RIGHT)
    add_rect(s, 866, 464, 242, 68, fill=RGBColor(0x16, 0x21, 0x3E), line=RGBColor(0x2A, 0x2A, 0x4A), radius=0.10)
    add_text(s, 876, 471, 220, 16, "INPUT    #email", size=9.5, color=RGBColor(0xE6, 0xE6, 0xE6), font=MONO)
    add_text(s, 876, 489, 220, 16, "INPUT    #senha", size=9.5, color=RGBColor(0xE6, 0xE6, 0xE6), font=MONO)
    add_text(s, 876, 507, 220, 16, "BUTTON   .entrar", size=9.5, color=RGBColor(0xE6, 0xE6, 0xE6), font=MONO)
    add_rect(s, 866, 542, 242, 28, fill=RGBColor(0x16, 0x21, 0x3E), line=RGBColor(0x2A, 0x2A, 0x4A), radius=0.12)
    add_text(s, 866, 548, 242, 16, "Exportar JSON", size=9.5, color=RGBColor(0xE6, 0xE6, 0xE6), bold=True, align=PP_ALIGN.CENTER)
    add_footer(s, "Seletores sem sofrimento", 7)


def slide_telas(prs):
    s = slide_base(prs)
    add_header(s, "Telas", "Tudo no mesmo lugar.", y=52, sub="Lagoa, agendamentos e monitor com a mesma identidade — tema claro e escuro.")
    add_browser_chrome(s, 64, 182, 700, "localhost:8765")
    add_picture(s, IMG / "cr_light.jpg", 64, 212, w=700, border=True)
    add_text(s, 64, 626, 700, 18, "Lagoa: máquinas, jobs, processos e filas.", size=9.5, color=TEXTO_SUAVE)

    add_picture(s, IMG / "agenda.jpg", 800, 212, h=168, border=True)
    add_text(s, 800, 388, 416, 18, "Agendamentos com dias e feriados.", size=9.5, color=TEXTO_SUAVE)
    add_picture(s, IMG / "cr_dark.jpg", 800, 428, h=168, border=True)
    add_text(s, 800, 604, 416, 18, "Tema escuro nativo.", size=9.5, color=TEXTO_SUAVE)
    add_footer(s, "Painel web · sem Flask · zero dependência extra", 8)


def slide_cloud(prs):
    s = slide_base(prs)
    add_header(
        s,
        "Capivara Cloud · beta",
        "Orquestre APIs, não só telas.",
        y=52,
        sub="Produto separado do framework: editor visual, webhook e execução de fluxos entre sistemas.",
    )
    add_pill(s, 1112, 54, 72, 22, "BETA", AMARELO, TEXTO, size=8.5, bold=True)

    cards = [
        ("API-FIRST", "Fluxos por HTTP", "Webhook, execução e catálogo de conectores com Swagger."),
        ("VISUAL", "Editor Drawflow", "Arraste conectores, conecte ramos e veja o trace."),
        ("SEGURO", "Credenciais Fernet", "Segredos cifrados e mascarados na API e na UI."),
        ("28 CONECTORES", "Do e-mail ao Graph", "SMTP/IMAP, Microsoft 365, Slack, HTTP, dados e mais."),
    ]
    for i, (kicker, titulo, corpo) in enumerate(cards):
        col = i % 2
        row = i // 2
        add_cloud_card(s, 64 + col * 290, 182 + row * 140, 270, 125, kicker, titulo, corpo)

    add_rect(s, 64, 470, 560, 82, fill=RGBColor(0xEC, 0xF7, 0xF0), line=RGBColor(0xB7, 0xDD, 0xC8), radius=0.12)
    add_text(s, 84, 484, 520, 18, "A Lagoa orquestra robôs. O Cloud orquestra APIs.", size=14, color=VERDE_FORTE, font=TITULO, bold=True)
    add_text(s, 84, 508, 520, 32, "Mesma identidade, outro produto: workflows entre sistemas, sem instalar agente.", size=11.5, color=TEXTO_SUAVE, line_spacing=1.2)

    add_browser_chrome(s, 664, 182, 552, "cloud.capivara.local")
    add_rect(s, 664, 212, 552, 400, fill=SUPERFICIE, line=BORDA, radius=0.04)
    add_text(s, 688, 228, 300, 16, "workflow · pedido aprovado", size=10, color=TEXTO_SUAVE, font=MONO)

    nos = [
        (700, 258, 150, 66, "GATILHO", "Webhook", "pedido.criado"),
        (890, 258, 150, 66, "REGRA", "Condição", "total > 500"),
        (1080, 258, 110, 66, "AÇÃO", "Slack", "#vendas"),
        (890, 372, 150, 66, "AÇÃO", "E-mail", "cliente"),
        (1080, 372, 110, 66, "AÇÃO", "Log", "trace"),
    ]
    for x, y, w, h, kicker, titulo, corpo in nos:
        add_rect(s, x, y, w, h, fill=FUNDO_ALT, line=BORDA, radius=0.10)
        add_text(s, x + 14, y + 10, w - 28, 12, kicker, size=7.5, color=VERDE, font=MONO, bold=True)
        add_text(s, x + 14, y + 25, w - 28, 18, titulo, size=14, color=TEXTO, font=TITULO, bold=True)
        add_text(s, x + 14, y + 46, w - 28, 14, corpo, size=9, color=TEXTO_SUAVE, font=MONO)

    add_line(s, 850, 291, 890, 291, color=VERDE, width=1.5)
    add_line(s, 1040, 291, 1080, 291, color=VERDE, width=1.5)
    add_line(s, 965, 324, 965, 372, color=VERDE, width=1.5)
    add_line(s, 1040, 405, 1080, 405, color=VERDE, width=1.5)

    add_rect(s, 700, 474, 490, 108, fill=CODIGO, line=BORDA_ESCURA, radius=0.08)
    add_text(s, 718, 484, 450, 14, "trace da execução", size=8.5, color=RGBColor(0x8A, 0x9A, 0x8F), font=MONO)
    linhas = [
        ("✓", "webhook recebido", VERDE_CLARO),
        ("✓", "condição: total > 500", VERDE_CLARO),
        ("→", "slack #vendas enviado", AMARELO),
        ("→", "e-mail para o cliente", AMARELO),
    ]
    for i, (icone, texto, cor) in enumerate(linhas):
        y = 506 + i * 17
        add_text(s, 718, y, 16, 14, icone, size=9.5, color=cor, font=MONO, bold=True)
        add_text(s, 738, y, 420, 14, texto, size=9.5, color=RGBColor(0xE6, 0xEF, 0xE9), font=MONO)

    add_footer(s, "Cloud em beta · FastAPI + Drawflow + SQLite", 9)


def add_cloud_card(s, x, y, w, h, kicker, titulo, corpo):
    add_rect(s, x, y, w, h, fill=SUPERFICIE, line=BORDA, radius=0.12)
    add_text(s, x + 20, y + 16, w - 40, 12, kicker, size=8.5, color=VERDE, font=MONO, bold=True)
    add_text(s, x + 20, y + 34, w - 40, 22, titulo, size=17, color=TEXTO, font=TITULO, bold=True)
    add_text(s, x + 20, y + 64, w - 40, h - 74, corpo, size=11.5, color=TEXTO_SUAVE, line_spacing=1.16)


def slide_seguranca(prs):
    s = slide_base(prs)
    add_header(s, "Segurança e governança", "Automação com controle.", y=107, sub="O que a empresa precisa para deixar um robô rodando em produção sem perder o sono.")
    y = 237
    w = 373
    itens = [
        ("RBAC", "Login e papéis", "Usuários locais, permissões por papel e sessão com cookie HttpOnly."),
        ("TOKEN", "Token por máquina", "Cada agente tem seu token; só o hash fica no banco. Revogou, acabou."),
        ("TLS", "HTTPS opcional", "Certificado e chave configuráveis para sair da rede local com segurança."),
        ("AUDIT", "Auditoria", "Quem acessou, quando, de onde e qual credencial. Exportação em CSV."),
        ("SLA", "Alertas", "Jobs estourados e tempo de execução aparecem no topo do painel."),
        ("VAULT", "Cofre", "Fernet, versões, rotação, permissão por processo e segredos mascarados no log."),
    ]
    for i, (k, t, d) in enumerate(itens):
        col = i % 3
        row = i // 3
        add_seg(s, 64 + col * 386, y + row * 138, w, 125, k, t, d)

    add_band(
        s,
        64,
        522,
        1152,
        60,
        ["Quem acessou?", "O que rodou?", "Quando parar?"],
        ["Auditoria por ator, processo e IP.", "Trace de cada passo no Monitor.", "Cancelamento cooperativo e alerta de SLA."],
    )
    add_footer(s, "Governança sem planilha paralela", 10)


def add_seg(s, x, y, w, h, kicker, titulo, corpo):
    add_rect(s, x, y, w, h, fill=SUPERFICIE, line=BORDA, radius=0.12)
    add_pill(s, x + 18, y + 17, 50, 18, kicker, RGBColor(0xE8, 0xF4, 0xED), VERDE, size=8.5, bold=True)
    add_text(s, x + 18, y + 43, w - 36, 22, titulo, size=17, color=TEXTO, font=TITULO, bold=True)
    add_text(s, x + 18, y + 69, w - 36, h - 78, corpo, size=12.5, color=TEXTO_SUAVE, line_spacing=1.14)


def slide_comecar(prs):
    s = slide_base(prs)
    add_header(s, "Começar", "Do zero ao primeiro robô.", y=52, sub="Escolha o caminho. O resultado é o mesmo: menos Ctrl+C, Ctrl+V.")
    linhas = [
        "# opção 1 — biblioteca",
        "pip install capivara-rpa",
        "",
        "# kit completo (Selenium + pandas + cofre)",
        'pip install "capivara-rpa[all]"',
        "",
        "# opção 2 — repositório",
        "git clone https://github.com/capivara-rpa/capivara.git",
        "",
        "# opção 3 — instaladores sem Python",
        "# Windows, macOS e TrackTab nas releases",
    ]
    add_code_block(s, 64, 182, 650, 440, linhas, titulo="começar", fonte=11)
    add_mini_passo(s, 736, 182, 480, 138, "PYPI", "Biblioteca", "Base leve em segundos. Use `[web]` ou `[all]`.")
    add_mini_passo(s, 736, 333, 480, 138, "GIT", "Repositório", "Clone, explore os exemplos e acompanhe as releases.")
    add_mini_passo(s, 736, 484, 480, 138, "EXE", "Instaladores", "Lagoa e agente para Windows e macOS, sem Python.")
    add_footer(s, "pypi.org/project/capivara-rpa", 11)


def add_mini_passo(s, x, y, w, h, kicker, titulo, corpo):
    add_rect(s, x, y, w, h, fill=SUPERFICIE, line=BORDA, radius=0.12)
    add_pill(s, x + 18, y + 17, 42, 18, kicker, RGBColor(0xE8, 0xF4, 0xED), VERDE, size=8.5, bold=True)
    add_text(s, x + 18, y + 43, w - 36, 22, titulo, size=16, color=TEXTO, font=TITULO, bold=True)
    runs = _inline_runs(corpo, 12.5, TEXTO_SUAVE)
    add_paras(s, x + 18, y + 70, w - 36, 50, [{"runs": runs, "line_spacing": 1.16}])


def slide_planos(prs):
    s = slide_base(prs)
    add_header(s, "Planos", "Comece grátis. Escale com quem fez.", y=79, sub="O código é aberto. Se a empresa quer ir para produção rápido e com segurança, a Capivara trabalha junto.")
    add_plano(
        s,
        64,
        209,
        567,
        310,
        "Comunidade",
        "Grátis",
        "pra sempre",
        [
            "Template completo + Lagoa",
            "Filas, agendamentos e cofre",
            "Instaladores macOS e Windows",
            "TrackTab para capturar seletores",
            "Suporte da comunidade",
        ],
        destaque=False,
    )
    add_plano(
        s,
        649,
        209,
        567,
        310,
        "Empresas",
        "Implantação",
        "+ suporte",
        [
            "Mapeamento dos processos que mais doem",
            "Instalação da Lagoa e dos agentes",
            "Desenvolvimento dos primeiros robôs",
            "Login, permissões, HTTPS e governança",
            "Treinamento do time e suporte direto",
        ],
        destaque=True,
    )
    add_band(
        s,
        64,
        541,
        1152,
        50,
        ["01  Baixe grátis", "02  Rode um piloto", "03  Escale com suporte"],
        ["Comece pela comunidade.", "Valide um processo real.", "Chame o time quando doer."],
    )
    add_footer(s, "Open source no core · implantação quando precisar", 12)


def add_plano(s, x, y, w, h, titulo, preco, preco_sub, itens, destaque=False):
    fill = RGBColor(0xEC, 0xF7, 0xF0) if destaque else SUPERFICIE
    line = RGBColor(0xB7, 0xDD, 0xC8) if destaque else BORDA
    add_rect(s, x, y, w, h, fill=fill, line=line, radius=0.12)
    if destaque:
        add_pill(s, x + w - 102, y + 18, 84, 20, "SOB MEDIDA", AMARELO, TEXTO, size=8.5, bold=True)
    add_text(s, x + 24, y + 22, 300, 22, titulo, size=24, color=TEXTO, font=TITULO, bold=True)
    add_text(s, x + 24, y + 56, 420, 28, preco, size=21, color=VERDE, font=TITULO, bold=True)
    add_text(s, x + 24 + (len(preco) * 12), y + 63, 200, 18, preco_sub, size=11, color=TEXTO_SUAVE)
    add_check_list(s, x + 24, y + 102, w - 48, 190, itens, size=13, gap=7)


def slide_cta(prs):
    s = slide_base(prs, dark=True)
    add_oval(s, 760, 80, 520, 520, MATA_2)
    add_oval(s, 900, 250, 360, 360, MATA_3)
    add_text(s, 64, 150, 600, 18, "VAMOS AUTOMATIZAR?", size=11, color=VERDE_CLARO, bold=True)
    add_paras(
        s,
        64,
        172,
        620,
        190,
        [
            {"runs": [{"text": "Deixa que a", "size": 68, "color": RGBColor(0xF2, 0xEE, 0xE7), "font": TITULO, "bold": True}], "line_spacing": 0.98},
            {"runs": [{"text": "Capivara", "size": 68, "color": VERDE_CLARO, "font": TITULO, "bold": True}, {"text": " faz.", "size": 68, "color": RGBColor(0xF2, 0xEE, 0xE7), "font": TITULO, "bold": True}], "line_spacing": 0.98},
        ],
    )
    add_text(s, 64, 360, 560, 70, "Comece grátis pelo PyPI, clone o repositório ou fale com o time para uma implantação sob medida.", size=19, color=CINZA_CLARO, line_spacing=1.35)
    links = [
        ("pypi.org/project/capivara-rpa", "https://pypi.org/project/capivara-rpa/"),
        ("github.com/capivara-rpa/capivara", "https://github.com/capivara-rpa/capivara"),
        ("github.com/capivara-rpa/capivara-community", "https://github.com/capivara-rpa/capivara-community"),
        ("arthurfaria.tech/capivara", "https://arthurfaria.tech/capivara/index.html"),
    ]
    paras = []
    for texto, url in links:
        paras.append({"runs": [{"text": texto, "size": 13, "color": CINZA_CLARO, "font": MONO, "link": url}], "space_after": 6})
    add_paras(s, 64, 448, 560, 120, paras)
    add_picture(s, ASSETS / "capivara.png", 900, 260, w=340, border=False)
    add_footer(s, "Capivara · Deixa que a Capivara faz.", 13, dark=True)


def main():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = "Capivara — Apresentação"
    prs.core_properties.author = "Capivara"
    prs.core_properties.subject = "RPA em Python, 100% em português"
    prs.core_properties.comments = "Gerado a partir da identidade visual da landing."

    slide_capa(prs)
    slide_problema(prs)
    slide_oque(prs)
    slide_como(prs)
    slide_recursos(prs)
    slide_codigo(prs)
    slide_tracktab(prs)
    slide_telas(prs)
    slide_cloud(prs)
    slide_seguranca(prs)
    slide_comecar(prs)
    slide_planos(prs)
    slide_cta(prs)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    prs.save(SAIDA)
    print(f"PPTX gerado: {SAIDA} ({SAIDA.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()

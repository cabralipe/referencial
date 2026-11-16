"""PDFs legíveis dos relatórios do diário, com os mesmos dados das planilhas."""

import io
from itertools import groupby
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)


def gerar_pdf(cabecalhos, linhas, *, frequencia=False):
    buffer = io.BytesIO()
    titulo = "Relatório de frequência" if frequencia else "Relatório do diário de bordo"
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm, title=titulo, author="AVA",
    )
    estilos = getSampleStyleSheet()
    texto = ParagraphStyle(
        "RelatorioTexto", parent=estilos["BodyText"], fontSize=9, leading=13,
        spaceAfter=5, wordWrap="LTR",
    )
    celula = ParagraphStyle("RelatorioCelula", parent=texto, fontSize=8, leading=11)
    cabecalho = ParagraphStyle("RelatorioCabecalho", parent=celula, textColor=colors.white)

    def par(valor, estilo=texto):
        conteudo = str(valor) if valor is not None and valor != "" else "-"
        return Paragraph(escape(conteudo).replace("\n", "<br/>"), estilo)

    def campos(valores, indices):
        for indice in indices:
            valor = valores[indice]
            valor = str(valor) if valor is not None and valor != "" else "-"
            elementos.append(Paragraph(
                f"<b>{escape(cabecalhos[indice])}:</b> "
                + escape(valor).replace("\n", "<br/>"), texto,
            ))

    def rodape(canvas, documento):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D5DDE5"))
        canvas.line(doc.leftMargin, 13 * mm, A4[0] - doc.rightMargin, 13 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#526171"))
        canvas.drawString(doc.leftMargin, 9 * mm, titulo)
        canvas.drawRightString(A4[0] - doc.rightMargin, 9 * mm, f"Página {documento.page}")
        canvas.restoreState()

    elementos = [par(titulo, estilos["Title"]), Spacer(1, 5 * mm)]
    if not linhas:
        elementos.append(par("Nenhum registro encontrado para os filtros aplicados."))
    elif frequencia:
        for numero, (_, grupo) in enumerate(groupby(linhas, key=lambda linha: linha[0])):
            if numero:
                elementos.append(PageBreak())
            participantes = list(grupo)
            primeira = participantes[0]
            elementos.append(par(primeira[3], estilos["Heading2"]))
            campos(primeira, [0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18])
            elementos.append(Spacer(1, 4 * mm))
            tabela = [[par(cabecalhos[i], cabecalho) for i in range(11, 16)]]
            detalhes = []
            for linha in participantes:
                valores = []
                for indice in range(11, 16):
                    valor = linha[indice]
                    if len(str(valor)) > 250:
                        referencia = len(detalhes) + 1
                        detalhes.append((referencia, cabecalhos[indice], linha[11], valor))
                        valor = f"Ver detalhamento {referencia} após a tabela."
                    valores.append(par(valor, celula))
                tabela.append(valores)
            tabela = LongTable(
                tabela, colWidths=[doc.width * p for p in (.25, .14, .16, .29, .16)],
                repeatRows=1, hAlign="LEFT",
            )
            tabela.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                ("LINEBELOW", (0, 1), (-1, -1), .3, colors.HexColor("#D5DDE5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            elementos.append(tabela)
            if detalhes:
                elementos.append(Spacer(1, 4 * mm))
                elementos.append(par("Detalhamento dos participantes", estilos["Heading3"]))
                for referencia, campo, participante, valor in detalhes:
                    elementos.append(par(f"{referencia}. {campo} - {participante}", estilos["Heading4"]))
                    elementos.append(par(valor))
    else:
        for numero, linha in enumerate(linhas):
            if numero:
                elementos.append(PageBreak())
            elementos.append(par(linha[2], estilos["Heading2"]))
            campos(linha, range(len(cabecalhos)))
    doc.build(elementos, onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()

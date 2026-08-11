import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.files import File
from django.template import Context, Template
from django.utils import timezone
from django.utils.html import conditional_escape, format_html, mark_safe

from ava.models import Certificado, ConfigCertificado, MatriculaCurso
from ava.models.certificate import DEFAULT_CERTIFICATE_VARIABLES


@dataclass(frozen=True)
class CertificateEligibility:
    approved: bool
    reasons: list[str]


def _safe_percent(value, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(100, value))


def _safe_color(value):
    if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value
    return "#1f2937"


def _file_uri(file_field):
    if not file_field:
        return ""
    try:
        return Path(file_field.path).resolve().as_uri()
    except (NotImplementedError, ValueError):
        return getattr(file_field, "url", "") or ""


def _student_name(user):
    return user.get_full_name() or getattr(user, "nome", "") or user.email


def _render_string(template_text, context):
    if not template_text:
        return ""
    return Template(template_text).render(Context(context))


class CertificacaoService:
    @staticmethod
    def avaliar_matricula(matricula: MatriculaCurso) -> CertificateEligibility:
        curso = matricula.curso
        reasons = []

        if not curso.permite_certificado:
            reasons.append("Curso nao emite certificado")
        if matricula.status != MatriculaCurso.Status.CONCLUIDA:
            reasons.append("Matricula ainda nao esta concluida")
        if int(matricula.progresso_percentual or 0) < int(curso.progresso_minimo or 0):
            reasons.append(f"Progresso {matricula.progresso_percentual}% abaixo de {curso.progresso_minimo}%")
        if Decimal(matricula.nota_final_obtida or 0) < Decimal(curso.nota_minima or 0):
            reasons.append(f"Nota {matricula.nota_final_obtida} abaixo de {curso.nota_minima}")

        return CertificateEligibility(approved=not reasons, reasons=reasons)

    @staticmethod
    def montar_variaveis(matricula: MatriculaCurso, certificado: Certificado | None = None, config: ConfigCertificado | None = None):
        aluno = matricula.aluno
        curso = matricula.curso
        data_emissao = timezone.localtime(certificado.data_emissao) if certificado else timezone.localtime(timezone.now())
        carga_horaria = (
            config.carga_horaria_impressa
            if config and config.carga_horaria_impressa
            else curso.carga_horaria
        )

        gts = ", ".join(aluno.grupos_trabalho.order_by("nome").values_list("nome", flat=True))
        aluno_eixos = ", ".join(aluno.eixos.order_by("ordem_exibicao", "nome").values_list("nome", flat=True))
        curso_eixos = ", ".join(curso.eixos.order_by("ordem_exibicao", "nome").values_list("nome", flat=True))

        return {
            "aluno_nome": _student_name(aluno),
            "aluno_email": aluno.email,
            "aluno_role": aluno.get_role_display() if hasattr(aluno, "get_role_display") else getattr(aluno, "role", ""),
            "aluno_tipo_cadastro": str(aluno.tipo_cadastro) if getattr(aluno, "tipo_cadastro_id", None) else "",
            "aluno_escola": str(aluno.escola) if getattr(aluno, "escola_id", None) else "",
            "aluno_gt": gts,
            "aluno_eixos": aluno_eixos,
            "curso_nome": curso.titulo,
            "curso_eixos": curso_eixos,
            "carga_horaria": carga_horaria,
            "nota_final": str(matricula.nota_final_obtida),
            "progresso_percentual": int(matricula.progresso_percentual or 0),
            "data_emissao": data_emissao.strftime("%d/%m/%Y"),
            "codigo_validacao": certificado.codigo_validacao if certificado else "",
        }

    @staticmethod
    def renderizar_html(certificado: Certificado | None, matricula: MatriculaCurso, config: ConfigCertificado, campos=None):
        campos = list(campos or config.campos_variaveis or DEFAULT_CERTIFICATE_VARIABLES)
        variaveis = CertificacaoService.montar_variaveis(matricula, certificado, config)
        tema = config.tema_padrao or ConfigCertificado.TemaPadrao.CLASSICO
        fundo_url = _file_uri(config.fundo)
        texto_x = _safe_percent(config.texto_x, 50)
        texto_y = _safe_percent(config.texto_y, 42)
        texto_largura = _safe_percent(config.texto_largura, 72)
        cor_texto = _safe_color(config.cor_texto)

        assinaturas = list(config.assinaturas.order_by("ordem", "id"))
        total_assinaturas = max(int(config.quantidade_assinaturas or 0), len(assinaturas), 0)
        assinatura_slots = []
        for index in range(total_assinaturas):
            assinatura = assinaturas[index] if index < len(assinaturas) else None
            auto_x = int(((index + 1) * 100) / (total_assinaturas + 1)) if total_assinaturas else 50
            assinatura_slots.append(
                {
                    "titulo": assinatura.titulo if assinatura else "",
                    "cargo": assinatura.cargo if assinatura else "",
                    "imagem_url": _file_uri(assinatura.imagem) if assinatura else "",
                    "x": _safe_percent(assinatura.x if assinatura and assinatura.x else auto_x, auto_x),
                    "y": _safe_percent(assinatura.y if assinatura else 78, 78),
                    "largura": _safe_percent(assinatura.largura if assinatura else 22, 22),
                }
            )

        subtitulo = _render_string(config.subtitulo, variaveis)
        corpo = _render_string(config.template_html, variaveis)
        if not corpo:
            linhas = [
                ("Cursista", variaveis.get("aluno_nome", "")),
                ("Curso", variaveis.get("curso_nome", "")),
            ]
            linhas.extend(
                (label, variaveis.get(key, ""))
                for key, label in DEFAULT_CERTIFICATE_VARIABLES_LABELS.items()
                if key in campos and key not in {"aluno_nome", "curso_nome"}
            )
            corpo = mark_safe(
                "".join(
                    format_html(
                        '<div class="cert-field"><span>{}</span><strong>{}</strong></div>',
                        label,
                        value or "-",
                    )
                    for label, value in linhas
                )
            )

        signature_html = mark_safe(
            "".join(
                format_html(
                    """
                    <div class="signature" style="left: {}%; top: {}%; width: {}%;">
                        {}
                        <div class="signature-line"></div>
                        <strong>{}</strong>
                        <span>{}</span>
                    </div>
                    """,
                    slot["x"],
                    slot["y"],
                    slot["largura"],
                    format_html('<img src="{}" alt="">', slot["imagem_url"]) if slot["imagem_url"] else "",
                    slot["titulo"] or "Assinatura",
                    slot["cargo"] or "",
                )
                for slot in assinatura_slots
            )
        )

        background_css = (
            f"background-image: url('{fundo_url}'); background-size: cover; background-position: center;"
            if fundo_url
            else ""
        )
        verso_fundo_url = _file_uri(config.verso_fundo) if config.verso_ativo else ""
        verso_background_css = (
            f"background-image: url('{verso_fundo_url}'); background-size: cover; background-position: center;"
            if verso_fundo_url
            else ""
        )
        tema_class = f"theme-{tema}"
        titulo = conditional_escape(_render_string(config.titulo, variaveis) or "Certificado")
        verso_titulo = conditional_escape(_render_string(config.verso_titulo, variaveis))
        verso_corpo = _render_string(config.verso_template_html, variaveis)
        verso_html = ""
        if config.verso_ativo:
            verso_html = f"""
            <main class="certificate certificate-back {tema_class}" style="{verso_background_css}">
                <div class="border"></div>
                <section class="back-content">
                    {f'<h1>{verso_titulo}</h1>' if verso_titulo else ''}
                    <div class="back-body">{verso_corpo}</div>
                </section>
                <div class="validation">Codigo de validacao: {conditional_escape(variaveis.get("codigo_validacao") or "PREVIEW")}</div>
            </main>
            """

        return f"""
        <!doctype html>
        <html lang="pt-br">
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 landscape; margin: 0; }}
                * {{ box-sizing: border-box; }}
                body {{ margin: 0; font-family: "DejaVu Sans", Arial, sans-serif; color: {cor_texto}; }}
                .certificate {{
                    width: 297mm;
                    height: 210mm;
                    position: relative;
                    overflow: hidden;
                }}
                .certificate + .certificate {{
                    break-before: page;
                    page-break-before: always;
                }}
                .certificate:not([style*="background-image"]).theme-classico {{
                    background: linear-gradient(135deg, #f8fafc 0%, #ffffff 54%, #e0f2fe 100%);
                }}
                .certificate:not([style*="background-image"]).theme-moderno {{
                    background: linear-gradient(135deg, #111827 0%, #1d4ed8 52%, #f8fafc 52.2%, #ffffff 100%);
                }}
                .certificate:not([style*="background-image"]).theme-institucional {{
                    background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
                }}
                .border {{
                    position: absolute;
                    inset: 12mm;
                    border: 1.5mm solid rgba(31, 41, 55, 0.18);
                }}
                .content {{
                    position: absolute;
                    left: {texto_x}%;
                    top: {texto_y}%;
                    width: {texto_largura}%;
                    transform: translate(-50%, -50%);
                    text-align: center;
                }}
                h1 {{
                    margin: 0 0 8mm;
                    font-size: {int(config.titulo_tamanho or 42)}px;
                    letter-spacing: 0;
                    text-transform: uppercase;
                }}
                .subtitle {{
                    font-size: {int(config.texto_tamanho or 18)}px;
                    line-height: 1.55;
                    margin-bottom: 7mm;
                }}
                .fields {{
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 3mm;
                    text-align: left;
                }}
                .cert-field {{
                    border-top: 1px solid rgba(31, 41, 55, 0.18);
                    padding-top: 2mm;
                    min-height: 14mm;
                }}
                .cert-field span {{
                    display: block;
                    font-size: 10px;
                    text-transform: uppercase;
                    color: rgba(31, 41, 55, 0.65);
                }}
                .cert-field strong {{
                    display: block;
                    font-size: 14px;
                    line-height: 1.35;
                }}
                .signature {{
                    position: absolute;
                    transform: translateX(-50%);
                    text-align: center;
                    font-size: 11px;
                }}
                .signature img {{
                    max-width: 100%;
                    max-height: 22mm;
                    object-fit: contain;
                    display: block;
                    margin: 0 auto -2mm;
                }}
                .signature-line {{
                    border-top: 1px solid rgba(31, 41, 55, 0.75);
                    margin: 0 auto 2mm;
                    width: 100%;
                    height: 2mm;
                }}
                .signature strong,
                .signature span {{ display: block; }}
                .validation {{
                    position: absolute;
                    left: 16mm;
                    bottom: 10mm;
                    font-size: 9px;
                    color: rgba(31, 41, 55, 0.66);
                }}
                .back-content {{
                    position: absolute;
                    inset: 20mm;
                    padding: 12mm;
                    overflow: hidden;
                }}
                .back-content h1 {{
                    margin-bottom: 10mm;
                    text-align: center;
                }}
                .back-body {{
                    font-size: {int(config.texto_tamanho or 18)}px;
                    line-height: 1.55;
                }}
                .back-body table {{ width: 100%; border-collapse: collapse; }}
                .back-body th, .back-body td {{
                    border: 1px solid rgba(31, 41, 55, 0.25);
                    padding: 2.5mm;
                }}
            </style>
        </head>
        <body>
            <main class="certificate {tema_class}" style="{background_css}">
                <div class="border"></div>
                <section class="content">
                    <h1>{titulo}</h1>
                    <div class="subtitle">{conditional_escape(subtitulo)}</div>
                    <div class="fields">{corpo}</div>
                </section>
                {signature_html}
                <div class="validation">Codigo de validacao: {conditional_escape(variaveis.get("codigo_validacao") or "PREVIEW")}</div>
            </main>
            {verso_html}
        </body>
        </html>
        """

    @staticmethod
    def gerar_pdf(certificado: Certificado, config: ConfigCertificado, campos=None):
        try:
            from weasyprint import HTML
        except ImportError as exc:
            raise RuntimeError("WeasyPrint nao esta instalado; nao foi possivel gerar o PDF.") from exc

        html = CertificacaoService.renderizar_html(certificado, certificado.matricula_curso, config, campos=campos)
        with NamedTemporaryFile(suffix=".pdf") as tmp:
            HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf(tmp.name)
            tmp.seek(0)
            nome = f"certificado-{certificado.codigo_validacao}.pdf"
            certificado.arquivo_pdf.save(nome, File(tmp), save=False)

    @staticmethod
    def emitir_para_matricula(
        matricula: MatriculaCurso,
        config: ConfigCertificado,
        *,
        emitido_por=None,
        campos=None,
        liberado_em=None,
        aprovar_pendente=False,
        gerar_pdf=True,
    ):
        elegibilidade = CertificacaoService.avaliar_matricula(matricula)
        if not elegibilidade.approved and not aprovar_pendente:
            return None, False, elegibilidade

        # A constraint unica do banco (ava_certificado_matricula_curso_id_key)
        # cobre a coluna matricula_curso_id independentemente do soft delete e do
        # escopo por cliente. Por isso a busca precisa passar por raw_objects, senao
        # um certificado previamente removido (is_deleted=True) ou de outro cliente
        # fica invisivel para o get() e o create() estoura IntegrityError.
        certificado = (
            Certificado.raw_objects.filter(matricula_curso=matricula).first()
        )
        created = certificado is None
        if created:
            certificado = Certificado(
                matricula_curso=matricula,
                cliente_id=matricula.cliente_id,
                aluno=matricula.aluno,
            )
        else:
            # Reaproveita o registro existente, reativando-o se estava removido e
            # garantindo o cliente correto para a matricula atual.
            certificado.is_deleted = False
            certificado.cliente_id = matricula.cliente_id
        certificado.config = config
        certificado.aluno = matricula.aluno
        certificado.emitido_por = emitido_por
        certificado.liberado_em = liberado_em
        certificado.nota_final = matricula.nota_final_obtida
        certificado.carga_horaria = (
            config.carga_horaria_impressa
            if config.carga_horaria_impressa
            else matricula.curso.carga_horaria
        )
        # Persiste a linha antes de montar o snapshot: um registro novo so ganha
        # codigo_validacao e data_emissao apos o save, e montar_variaveis depende
        # de ambos.
        certificado.save()
        certificado.dados_impressos = CertificacaoService.montar_variaveis(matricula, certificado, config)
        update_fields = [
            "config",
            "aluno",
            "emitido_por",
            "liberado_em",
            "nota_final",
            "carga_horaria",
            "dados_impressos",
        ]
        if gerar_pdf:
            CertificacaoService.gerar_pdf(certificado, config, campos=campos)
            update_fields.append("arquivo_pdf")
        certificado.save(update_fields=update_fields)
        return certificado, created, elegibilidade

    @staticmethod
    def avaliar_e_emitir(matricula: MatriculaCurso):
        try:
            config = ConfigCertificado.objects.get(curso=matricula.curso)
        except ConfigCertificado.DoesNotExist:
            return False, "Configuracao de certificado nao encontrada para este curso"

        certificado, _, elegibilidade = CertificacaoService.emitir_para_matricula(
            matricula,
            config,
            liberado_em=timezone.now(),
            aprovar_pendente=False,
        )
        if not certificado:
            return False, "; ".join(elegibilidade.reasons)
        return True, certificado


DEFAULT_CERTIFICATE_VARIABLES_LABELS = {
    "aluno_email": "E-mail",
    "aluno_role": "Tipo de usuario",
    "aluno_tipo_cadastro": "Tipo de cadastro",
    "aluno_escola": "Escola",
    "aluno_gt": "GTs",
    "aluno_eixos": "Eixos do usuario",
    "curso_eixos": "Eixos do curso",
    "carga_horaria": "Carga horaria",
    "nota_final": "Nota final",
    "progresso_percentual": "Progresso",
    "data_emissao": "Data de emissao",
    "codigo_validacao": "Codigo de validacao",
}

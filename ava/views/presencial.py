import csv
from io import BytesIO

from django import forms
from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from ava.models import RegistroSeminario, RepasseFrequencia
from ava.services.attendance_service import matriculas_do_curso
from ava.views.attendance import cursos_gerenciaveis
from ava.views.diario import diario_required


class RepasseForm(forms.ModelForm):
    class Meta:
        model = RepasseFrequencia
        fields = ['data_encontro', 'descricao', 'arquivo']
        widgets = {'data_encontro': forms.DateInput(attrs={'type': 'date'})}


class RegistroForm(forms.ModelForm):
    class Meta:
        model = RegistroSeminario
        fields = ['matricula', 'tipo', 'atividade', 'data_realizacao', 'nota', 'observacoes']
        widgets = {'data_realizacao': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, curso, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['matricula'].queryset = matriculas_do_curso(curso)
        self.fields['matricula'].label = 'Nome completo do cursista'


def curso_acessivel(request, curso_id):
    return get_object_or_404(cursos_gerenciaveis(request.user), pk=curso_id)


@diario_required
def painel(request):
    cursos = cursos_gerenciaveis(request.user).order_by('titulo')
    curso = get_object_or_404(cursos, pk=request.GET.get('curso')) if request.GET.get('curso') else cursos.first()
    repasses = RepasseFrequencia.raw_objects.filter(curso=curso, is_deleted=False) if curso else []
    registros = RegistroSeminario.raw_objects.filter(matricula__curso=curso, is_deleted=False).select_related('matricula__aluno') if curso else []
    return render(request, 'ava/management/presencial.html', {'cursos': cursos, 'curso': curso, 'repasses': repasses, 'registros': registros})


@diario_required
def repasse_form(request, curso_id, pk=None):
    curso = curso_acessivel(request, curso_id)
    obj = get_object_or_404(RepasseFrequencia.raw_objects, pk=pk, curso=curso, is_deleted=False) if pk else RepasseFrequencia(curso=curso, cliente=curso.cliente, enviado_por=request.user)
    form = RepasseForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Repasse salvo.')
        return redirect(f"{reverse('ava:presencial_painel')}?curso={curso.pk}")
    return render(request, 'ava/management/presencial_form.html', {'form': form, 'titulo': 'Repasse de frequência presencial', 'curso': curso})


@diario_required
def registro_form(request, curso_id, pk=None):
    curso = curso_acessivel(request, curso_id)
    obj = get_object_or_404(RegistroSeminario.raw_objects, pk=pk, matricula__curso=curso, is_deleted=False) if pk else RegistroSeminario(cliente=curso.cliente, registrado_por=request.user)
    form = RegistroForm(request.POST or None, instance=obj, curso=curso)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Registro salvo.')
        return redirect(f"{reverse('ava:presencial_painel')}?curso={curso.pk}")
    return render(request, 'ava/management/presencial_form.html', {'form': form, 'titulo': 'Seminário e prática dirigida', 'curso': curso})


@diario_required
@require_POST
def remover(request, curso_id, tipo, pk):
    curso = curso_acessivel(request, curso_id)
    if tipo == 'repasse':
        obj = get_object_or_404(RepasseFrequencia.raw_objects, pk=pk, curso=curso, is_deleted=False)
    elif tipo == 'registro':
        obj = get_object_or_404(RegistroSeminario.raw_objects, pk=pk, matricula__curso=curso, is_deleted=False)
    else:
        from django.http import Http404
        raise Http404
    obj.delete()
    return redirect(f"{reverse('ava:presencial_painel')}?curso={curso.pk}")


@diario_required
def arquivo(request, curso_id, pk):
    curso = curso_acessivel(request, curso_id)
    obj = get_object_or_404(RepasseFrequencia.raw_objects, pk=pk, curso=curso, is_deleted=False)
    return FileResponse(obj.arquivo.open('rb'), as_attachment=True)


@diario_required
def lista_pdf(request, curso_id):
    curso = curso_acessivel(request, curso_id)
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    from xml.sax.saxutils import escape
    cabecalho = Table([[
        [Image(str(settings.BASE_DIR / 'LOGO_PROLUC.png'), width=195, height=59), Spacer(1, 12), Paragraph(escape(curso.titulo.upper()), styles['Heading2'])],
        [Paragraph('AULA / ATIVIDADE: ___________________________________', styles['Normal']), Spacer(1, 12), Paragraph('OBJETIVO GERAL: ______________________________________', styles['Normal']), Spacer(1, 8), Paragraph('_______________________________________________________', styles['Normal']), Spacer(1, 12), Paragraph('TURMA: _______________________________________________', styles['Normal']), Paragraph('PROFESSOR(A) FORMADOR(A): ___________________________', styles['Normal']), Paragraph('Público-alvo: __________________________________________', styles['Normal']), Spacer(1, 8), Paragraph('Local: _____________________ Data: ___/___/______ Horário: ______', styles['Normal'])],
    ]], colWidths=[228, 405])
    cabecalho.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10)]))
    story = [cabecalho]
    rows = [['Nº', 'NOME', 'ESCOLA', 'CONTATO', 'ASSINATURA']]
    for i, m in enumerate(matriculas_do_curso(curso), 1):
        rows.append([str(i), Paragraph(escape(m.aluno.nome or m.aluno.email), styles['BodyText']), '', '', ''])
    table = Table(rows, colWidths=[28, 210, 125, 100, 170], repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey), ('BOTTOMPADDING', (0, 1), (-1, -1), 9), ('TOPPADDING', (0, 1), (-1, -1), 9)]))
    story.append(table)
    SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=71, rightMargin=71).build(story)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='frequencia-presencial.pdf')


@diario_required
def relatorio(request, curso_id):
    curso = curso_acessivel(request, curso_id)
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="seminarios-praticas.csv"'
    writer = csv.writer(response)
    writer.writerow(['Cursista', 'Tipo', 'Atividade', 'Data', 'Nota', 'Observações'])
    for r in RegistroSeminario.raw_objects.filter(matricula__curso=curso, is_deleted=False).select_related('matricula__aluno'):
        writer.writerow([r.matricula.aluno.nome, r.get_tipo_display(), r.atividade, r.data_realizacao, r.nota, r.observacoes])
    return response

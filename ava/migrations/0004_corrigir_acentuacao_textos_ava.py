from django.db import migrations


REPLACEMENTS = {
    "Formacão": "Formação",
    "formacão": "formação",
    "Formacao": "Formação",
    "formacao": "formação",
    "Educacão": "Educação",
    "educacão": "educação",
    "Educacao": "Educação",
    "educacao": "educação",
    "Computacão": "Computação",
    "computacão": "computação",
    "Computacao": "Computação",
    "computacao": "computação",
    "Implementacao": "Implementação",
    "implementacao": "implementação",
    "Elaboracao": "Elaboração",
    "elaboracao": "elaboração",
    "Atualizacao": "Atualização",
    "atualizacao": "atualização",
    "Gestao": "Gestão",
    "gestao": "gestão",
    "Construcao": "Construção",
    "construcao": "construção",
    "Vinculos": "Vínculos",
    "vinculos": "vínculos",
    "Avaliacao": "Avaliação",
    "avaliacao": "avaliação",
    "Continua": "Contínua",
    "continua": "contínua",
    "Praticas": "Práticas",
    "praticas": "práticas",
    "Pratica": "Prática",
    "pratica": "prática",
    "Apresentacao": "Apresentação",
    "apresentacao": "apresentação",
    "Modulo": "Módulo",
    "modulo": "módulo",
    "Conteudo": "Conteúdo",
    "conteudo": "conteúdo",
    "Video": "Vídeo",
    "video": "vídeo",
    "Orientacoes": "Orientações",
    "orientacoes": "orientações",
    "Duvidas": "Dúvidas",
    "duvidas": "dúvidas",
    "Espaco": "Espaço",
    "espaco": "espaço",
    "Certificacao": "Certificação",
    "certificacao": "certificação",
    "Navegacao": "Navegação",
    "navegacao": "navegação",
    "Participacao": "Participação",
    "participacao": "participação",
    "Observacoes": "Observações",
    "observacoes": "observações",
    "Organizacao": "Organização",
    "organizacao": "organização",
    "Politico-Pedagogico": "Político-Pedagógico",
    "politico-pedagogico": "político-pedagógico",
    "Diagnostico": "Diagnóstico",
    "diagnostico": "diagnóstico",
    "Atuacao": "Atuação",
    "atuacao": "atuação",
    "Competencias": "Competências",
    "competencias": "competências",
    "Pedagogicas": "Pedagógicas",
    "pedagogicas": "pedagógicas",
    "Pedagogica": "Pedagógica",
    "pedagogica": "pedagógica",
    "Estrategias": "Estratégias",
    "estrategias": "estratégias",
    "Mediacao": "Mediação",
    "mediacao": "mediação",
    "Alimentacao": "Alimentação",
    "alimentacao": "alimentação",
    "Nutricao": "Nutrição",
    "nutricao": "nutrição",
    "Principios": "Princípios",
    "principios": "princípios",
    "Especificas": "Específicas",
    "especificas": "específicas",
    "Referencias": "Referências",
    "referencias": "referências",
    "Criterios": "Critérios",
    "criterios": "critérios",
    "Emissao": "Emissão",
    "emissao": "emissão",
    "Informacoes": "Informações",
    "informacoes": "informações",
    "Publico": "Público",
    "publico": "público",
    "Basica": "Básica",
    "basica": "básica",
    "Introdutorio": "Introdutório",
    "introdutorio": "introdutório",
    "Introdutorios": "Introdutórios",
    "introdutorios": "introdutórios",
    "Territorio": "Território",
    "territorio": "território",
    "Curriculo": "Currículo",
    "curriculo": "currículo",
    "Acoes": "Ações",
    "acoes": "ações",
    "Consolidacao": "Consolidação",
    "consolidacao": "consolidação",
    "Conclusao": "Conclusão",
    "conclusao": "conclusão",
}


MODEL_FIELDS = {
    "Curso": [
        "titulo",
        "descricao_curta",
        "descricao_longa",
        "nivel",
        "publico_alvo",
        "ementa",
        "objetivos",
    ],
    "CursoModulo": ["titulo", "descricao"],
    "Aula": ["titulo", "resumo"],
    "ConteudoAula": ["titulo", "descricao", "conteudo_texto"],
    "Atividade": ["titulo", "descricao", "instrucoes"],
    "QuizQuestao": ["enunciado", "feedback_acerto", "feedback_erro"],
    "QuizAlternativa": ["texto", "feedback_especifico"],
    "CursoCategoria": ["nome", "descricao"],
    "TrilhaFormativa": ["nome", "descricao"],
}


def _corrigir_texto(value):
    if not isinstance(value, str) or not value:
        return value

    corrected = value
    for old, new in sorted(REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True):
        corrected = corrected.replace(old, new)
    return corrected


def corrigir_acentuacao_ava(apps, schema_editor):
    for model_name, fields in MODEL_FIELDS.items():
        model = apps.get_model("ava", model_name)
        for obj in model.objects.all().iterator():
            update_fields = []
            for field in fields:
                original = getattr(obj, field)
                corrected = _corrigir_texto(original)
                if corrected != original:
                    setattr(obj, field, corrected)
                    update_fields.append(field)
            if update_fields:
                obj.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("ava", "0003_alter_atividade_tipo_atividadeforummensagem_and_more"),
    ]

    operations = [
        migrations.RunPython(corrigir_acentuacao_ava, migrations.RunPython.noop),
    ]

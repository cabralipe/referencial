from django.contrib import admin
from .models import (
    TrilhaFormativa, CursoCategoria, Curso, CursoModulo, Aula, ConteudoAula,
    Atividade, QuizQuestao, QuizAlternativa, AtividadeTentativa,
    MatriculaCurso, MatriculaTrilha, ConfigCertificado, Certificado
)

@admin.register(TrilhaFormativa)
class TrilhaFormativaAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "is_active", "ordem_exibicao")
    list_filter = ("cliente", "is_active")

@admin.register(CursoCategoria)
class CursoCategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente")

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "slug", "cliente", "status", "is_aberto")
    list_filter = ("status", "cliente", "is_aberto")
    search_fields = ("titulo", "descricao_curta")
    prepopulated_fields = {"slug": ("titulo",)}

class AulaInline(admin.TabularInline):
    model = Aula
    extra = 1

@admin.register(CursoModulo)
class CursoModuloAdmin(admin.ModelAdmin):
    list_display = ("titulo", "curso", "ordem", "is_active")
    list_filter = ("curso", "is_active")
    inlines = [AulaInline]

class ConteudoAulaInline(admin.TabularInline):
    model = ConteudoAula
    extra = 1

class AtividadeInline(admin.StackedInline):
    model = Atividade
    extra = 0

@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "modulo", "ordem", "tipo", "is_active")
    list_filter = ("modulo__curso", "tipo", "is_active")
    inlines = [ConteudoAulaInline, AtividadeInline]

@admin.register(MatriculaCurso)
class MatriculaCursoAdmin(admin.ModelAdmin):
    list_display = ("aluno", "curso", "status", "progresso_percentual")
    list_filter = ("status", "curso")
    search_fields = ("aluno__username", "aluno__email")

@admin.register(MatriculaTrilha)
class MatriculaTrilhaAdmin(admin.ModelAdmin):
    list_display = ("aluno", "trilha", "status", "progresso_percentual")
    list_filter = ("status", "trilha")

@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ("aluno", "codigo_validacao", "data_emissao")
    search_fields = ("aluno__username", "codigo_validacao")
    readonly_fields = ("codigo_validacao", "dados_impressos", "data_emissao")

@admin.register(ConfigCertificado)
class ConfigCertificadoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "cliente")

"""Leitura, validação, importação e exportação de planilhas configuráveis.

O fluxo de importação tem quatro etapas independentes, para que a interface
possa mostrar o resultado de cada uma antes de gravar qualquer coisa:

1. :func:`ler_planilha` – extrai cabeçalhos e linhas do arquivo enviado;
2. :func:`sugerir_mapeamento` – casa cabeçalhos com as colunas configuradas;
3. :meth:`PlanilhaImportService.validar` – converte e valida linha a linha;
4. :meth:`PlanilhaImportService.gravar` – persiste apenas se não houver erro.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from ava.models.planilha import (
    ColunaPlanilha,
    ImportacaoPlanilha,
    ModeloPlanilha,
    RegistroPlanilha,
    ValorInvalido,
    ValorRegistroPlanilha,
    converter_valor,
)
from ava.services.audit_service import AVAAuditService
from core.models import Usuario
from curriculum.models import Escola


MAX_LINHAS_PREVIEW = 10
#: Teto de linhas por importação — evita estourar memória com arquivos enormes.
MAX_LINHAS_IMPORTACAO = 5000


class PlanilhaFormatoNaoSuportado(ValueError):
    """Arquivo cuja extensão não pode ser lida com as libs disponíveis."""


@dataclass
class ErroLinha:
    linha: int
    coluna: str
    mensagem: str

    def as_dict(self) -> dict:
        return {"linha": self.linha, "coluna": self.coluna, "mensagem": self.mensagem}


@dataclass
class LinhaPlanilha:
    numero: int
    valores: dict[str, object]


@dataclass
class ResultadoLeitura:
    cabecalhos: list[str]
    linhas: list[LinhaPlanilha]

    @property
    def preview(self) -> list[LinhaPlanilha]:
        return self.linhas[:MAX_LINHAS_PREVIEW]


@dataclass
class ResultadoValidacao:
    erros: list[ErroLinha] = field(default_factory=list)
    linhas_validas: list[tuple[int, dict]] = field(default_factory=list)

    @property
    def valida(self) -> bool:
        return not self.erros


# ----------------------------------------------------------------------
# Leitura dos arquivos
# ----------------------------------------------------------------------


def _normalizar(texto: str) -> str:
    """Remove acentos, pontuação e caixa para casar cabeçalhos."""

    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", texto.casefold())


def formatos_suportados() -> dict[str, bool]:
    """Extensões que este ambiente consegue ler, conforme as libs instaladas."""

    return {
        "xlsx": _tem_openpyxl(),
        "xlsm": _tem_openpyxl(),
        "csv": True,
        "xls": _tem_xlrd(),
        "ods": _tem_odfpy(),
    }


def _tem_openpyxl() -> bool:
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        return False
    return True


def _tem_xlrd() -> bool:
    try:
        import xlrd  # noqa: F401
    except ImportError:
        return False
    return True


def _tem_odfpy() -> bool:
    try:
        from odf.opendocument import load  # noqa: F401
    except ImportError:
        return False
    return True


def ler_planilha(arquivo, nome_arquivo: str | None = None) -> ResultadoLeitura:
    """Lê cabeçalhos e linhas do arquivo, seja qual for o formato suportado."""

    nome = nome_arquivo or getattr(arquivo, "name", "") or ""
    extensao = Path(nome).suffix.lower().lstrip(".")
    if hasattr(arquivo, "seek"):
        arquivo.seek(0)

    if extensao in {"xlsx", "xlsm"}:
        return _ler_xlsx(arquivo)
    if extensao == "csv":
        return _ler_csv(arquivo)
    if extensao == "xls":
        return _ler_xls(arquivo)
    if extensao == "ods":
        return _ler_ods(arquivo)
    raise PlanilhaFormatoNaoSuportado(
        f"Formato '{extensao or 'desconhecido'}' não suportado. "
        "Use XLSX, CSV ou outro formato habilitado no servidor."
    )


def _limpar(valor):
    if valor is None:
        return ""
    if isinstance(valor, (datetime, date)):
        return valor
    return str(valor).strip()


def _montar_resultado(cabecalhos_brutos, linhas_brutas) -> ResultadoLeitura:
    cabecalhos = [str(c).strip() for c in cabecalhos_brutos if str(c or "").strip()]
    linhas: list[LinhaPlanilha] = []
    for indice, bruta in enumerate(linhas_brutas, start=2):
        valores = {}
        vazia = True
        for posicao, cabecalho in enumerate(cabecalhos):
            valor = _limpar(bruta[posicao] if posicao < len(bruta) else "")
            valores[cabecalho] = valor
            if valor not in ("", None):
                vazia = False
        if vazia:
            continue
        linhas.append(LinhaPlanilha(numero=indice, valores=valores))
        if len(linhas) >= MAX_LINHAS_IMPORTACAO:
            break
    return ResultadoLeitura(cabecalhos=cabecalhos, linhas=linhas)


def _ler_xlsx(arquivo) -> ResultadoLeitura:
    import openpyxl

    conteudo = arquivo.read() if hasattr(arquivo, "read") else arquivo
    workbook = openpyxl.load_workbook(
        io.BytesIO(conteudo), read_only=True, data_only=True
    )
    try:
        sheet = workbook.active
        iterador = sheet.iter_rows(values_only=True)
        cabecalhos = next(iterador, ()) or ()
        return _montar_resultado(cabecalhos, list(iterador))
    finally:
        workbook.close()


def _ler_csv(arquivo) -> ResultadoLeitura:
    conteudo = arquivo.read() if hasattr(arquivo, "read") else arquivo
    if isinstance(conteudo, bytes):
        for codec in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                conteudo = conteudo.decode(codec)
                break
            except UnicodeDecodeError:
                continue
        else:  # pragma: no cover - latin-1 aceita qualquer byte
            conteudo = conteudo.decode("utf-8", errors="replace")
    amostra = conteudo[:4096]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t")
    except csv.Error:
        dialeto = csv.excel
        dialeto.delimiter = ";" if amostra.count(";") > amostra.count(",") else ","
    leitor = csv.reader(io.StringIO(conteudo), dialeto)
    linhas = list(leitor)
    if not linhas:
        return ResultadoLeitura(cabecalhos=[], linhas=[])
    return _montar_resultado(linhas[0], linhas[1:])


def _ler_xls(arquivo) -> ResultadoLeitura:
    try:
        import xlrd
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise PlanilhaFormatoNaoSuportado(
            "Leitura de .xls exige a biblioteca 'xlrd' instalada no servidor. "
            "Converta o arquivo para .xlsx ou .csv."
        ) from exc

    conteudo = arquivo.read() if hasattr(arquivo, "read") else arquivo
    workbook = xlrd.open_workbook(file_contents=conteudo)
    sheet = workbook.sheet_by_index(0)
    linhas = [sheet.row_values(indice) for indice in range(sheet.nrows)]
    if not linhas:
        return ResultadoLeitura(cabecalhos=[], linhas=[])
    return _montar_resultado(linhas[0], linhas[1:])


def _ler_ods(arquivo) -> ResultadoLeitura:
    try:
        from odf import table, text
        from odf.opendocument import load
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise PlanilhaFormatoNaoSuportado(
            "Leitura de .ods exige a biblioteca 'odfpy' instalada no servidor. "
            "Converta o arquivo para .xlsx ou .csv."
        ) from exc

    conteudo = arquivo.read() if hasattr(arquivo, "read") else arquivo
    documento = load(io.BytesIO(conteudo))
    planilhas = documento.spreadsheet.getElementsByType(table.Table)
    if not planilhas:
        return ResultadoLeitura(cabecalhos=[], linhas=[])
    linhas: list[list[str]] = []
    for linha in planilhas[0].getElementsByType(table.TableRow):
        celulas: list[str] = []
        for celula in linha.getElementsByType(table.TableCell):
            repeticoes = int(celula.getAttribute("numbercolumnsrepeated") or 1)
            conteudo_celula = "".join(
                str(paragrafo) for paragrafo in celula.getElementsByType(text.P)
            )
            celulas.extend([conteudo_celula] * min(repeticoes, 50))
        linhas.append(celulas)
    if not linhas:
        return ResultadoLeitura(cabecalhos=[], linhas=[])
    return _montar_resultado(linhas[0], linhas[1:])


# ----------------------------------------------------------------------
# Mapeamento de colunas
# ----------------------------------------------------------------------


def sugerir_mapeamento(modelo: ModeloPlanilha, cabecalhos: list[str]) -> dict[str, str]:
    """Casa cada cabeçalho da planilha com a chave da coluna configurada."""

    colunas = list(modelo.colunas_ativas())
    por_titulo = {_normalizar(coluna.titulo): coluna.chave for coluna in colunas}
    por_chave = {_normalizar(coluna.chave): coluna.chave for coluna in colunas}
    mapeamento: dict[str, str] = {}
    usadas: set[str] = set()
    for cabecalho in cabecalhos:
        normalizado = _normalizar(cabecalho)
        chave = por_titulo.get(normalizado) or por_chave.get(normalizado)
        if chave and chave not in usadas:
            mapeamento[cabecalho] = chave
            usadas.add(chave)
    return mapeamento


# ----------------------------------------------------------------------
# Serviço de importação
# ----------------------------------------------------------------------


class PlanilhaImportService:
    """Valida e grava os dados de uma :class:`ImportacaoPlanilha`."""

    def __init__(self, importacao: ImportacaoPlanilha, usuario):
        self.importacao = importacao
        self.modelo = importacao.modelo
        self.usuario = usuario
        self.colunas = {
            coluna.chave: coluna for coluna in self.modelo.colunas_ativas()
        }

    # -- leitura -------------------------------------------------------
    def ler(self) -> ResultadoLeitura:
        arquivo = self.importacao.arquivo
        arquivo.open("rb")
        try:
            return ler_planilha(arquivo, self.importacao.nome_original or arquivo.name)
        finally:
            arquivo.close()

    # -- validação -----------------------------------------------------
    def validar(self, leitura: ResultadoLeitura | None = None) -> ResultadoValidacao:
        leitura = leitura or self.ler()
        mapeamento = self.importacao.mapeamento or {}
        resultado = ResultadoValidacao()

        chaves_mapeadas = set(mapeamento.values())
        for chave, coluna in self.colunas.items():
            if coluna.obrigatorio and chave not in chaves_mapeadas and not coluna.valor_padrao:
                resultado.erros.append(
                    ErroLinha(
                        linha=1,
                        coluna=coluna.titulo,
                        mensagem=(
                            f"A coluna obrigatória '{coluna.titulo}' não foi mapeada "
                            "para nenhum cabeçalho da planilha."
                        ),
                    )
                )

        if self.importacao.modo == ImportacaoPlanilha.Modo.ATUALIZAR:
            if not self.importacao.coluna_chave:
                resultado.erros.append(
                    ErroLinha(
                        linha=1,
                        coluna="—",
                        mensagem="Escolha a coluna que identifica os registros a atualizar.",
                    )
                )
            elif self.importacao.coluna_chave not in chaves_mapeadas:
                resultado.erros.append(
                    ErroLinha(
                        linha=1,
                        coluna=self.importacao.coluna_chave,
                        mensagem="A coluna-chave precisa estar mapeada na planilha.",
                    )
                )

        if resultado.erros:
            return resultado

        for linha in leitura.linhas:
            convertidos, erros = self._converter_linha(linha, mapeamento)
            if erros:
                resultado.erros.extend(erros)
            else:
                resultado.linhas_validas.append((linha.numero, convertidos))
        return resultado

    def _converter_linha(
        self, linha: LinhaPlanilha, mapeamento: dict[str, str]
    ) -> tuple[dict, list[ErroLinha]]:
        convertidos: dict[str, object] = {}
        erros: list[ErroLinha] = []
        brutos: dict[str, object] = {}
        for cabecalho, chave in mapeamento.items():
            if chave in self.colunas:
                brutos[chave] = linha.valores.get(cabecalho, "")

        for chave, coluna in self.colunas.items():
            bruto = brutos.get(chave, "")
            try:
                valor = converter_valor(coluna, bruto)
            except ValorInvalido as exc:
                erros.append(ErroLinha(linha.numero, coluna.titulo, str(exc)))
                continue
            if valor is None:
                convertidos[chave] = None
                continue
            if coluna.tipo in ColunaPlanilha.TIPOS_RELACIONAIS:
                try:
                    convertidos[chave] = self._resolver_relacional(coluna, str(valor))
                except ValorInvalido as exc:
                    erros.append(ErroLinha(linha.numero, coluna.titulo, str(exc)))
                continue
            convertidos[chave] = valor
        return convertidos, erros

    def _resolver_relacional(self, coluna: ColunaPlanilha, texto: str):
        """Resolve professor/escola/participante dentro do município do modelo."""

        cliente_id = self.modelo.cliente_id
        if coluna.tipo == ColunaPlanilha.Tipo.ESCOLA:
            escola = Escola.raw_objects.filter(
                cliente_id=cliente_id, is_deleted=False, nome__iexact=texto
            ).first()
            if escola is None:
                raise ValorInvalido(
                    f"Escola '{texto}' não encontrada neste município."
                )
            return (escola.pk, escola.nome)

        user_model = get_user_model()
        filtro = user_model.objects.filter(cliente_id=cliente_id)
        if coluna.tipo == ColunaPlanilha.Tipo.PROFESSOR:
            filtro = filtro.filter(role=Usuario.Role.PROFESSOR)
        pessoa = filtro.filter(email__iexact=texto).first() or filtro.filter(
            nome__iexact=texto
        ).first()
        if pessoa is None:
            rotulo = "Professor" if coluna.tipo == ColunaPlanilha.Tipo.PROFESSOR else "Participante"
            raise ValorInvalido(f"{rotulo} '{texto}' não encontrado neste município.")
        return (pessoa.pk, pessoa.nome or pessoa.email)

    # -- gravação ------------------------------------------------------
    @transaction.atomic
    def gravar(self, validacao: ResultadoValidacao) -> ImportacaoPlanilha:
        """Persiste as linhas válidas. Nunca grava planilha com erro."""

        if not validacao.valida:
            raise ValueError("A importação possui erros e não pode ser gravada.")

        importacao = self.importacao
        criados = 0
        atualizados = 0
        for numero, valores in validacao.linhas_validas:
            registro, novo = self._obter_registro(valores, numero)
            self._gravar_valores(registro, valores)
            if novo:
                criados += 1
            else:
                atualizados += 1

        importacao.total_linhas = len(validacao.linhas_validas)
        importacao.total_criados = criados
        importacao.total_atualizados = atualizados
        importacao.total_ignorados = 0
        importacao.erros = []
        importacao.status = ImportacaoPlanilha.Status.CONCLUIDA
        importacao.concluida_em = timezone.now()
        importacao.save()

        AVAAuditService.registrar_planilha(
            importacao,
            self.usuario,
            acao="importacao_concluida",
            diff={
                "modelo": importacao.modelo_id,
                "modo": importacao.modo,
                "criados": criados,
                "atualizados": atualizados,
            },
        )
        return importacao

    def _obter_registro(self, valores: dict, numero: int) -> tuple[RegistroPlanilha, bool]:
        importacao = self.importacao
        chave_externa = ""
        if importacao.coluna_chave:
            bruto = valores.get(importacao.coluna_chave)
            chave_externa = _texto_da_chave(bruto)

        if (
            importacao.modo == ImportacaoPlanilha.Modo.ATUALIZAR
            and chave_externa
        ):
            existente = (
                RegistroPlanilha.raw_objects.filter(
                    is_deleted=False,
                    cliente_id=self.modelo.cliente_id,
                    modelo=self.modelo,
                    chave_externa=chave_externa,
                )
                .order_by("id")
                .first()
            )
            if existente is not None:
                existente.updated_by = self.usuario
                existente.importacao = importacao
                existente.linha_origem = numero
                existente.save()
                return existente, False

        registro = RegistroPlanilha(
            cliente_id=self.modelo.cliente_id,
            modelo=self.modelo,
            escola=self.modelo.escola,
            curso=self.modelo.curso,
            chave_externa=chave_externa,
            importacao=importacao,
            linha_origem=numero,
            created_by=self.usuario,
            updated_by=self.usuario,
        )
        registro.save()
        return registro, True

    def _gravar_valores(self, registro: RegistroPlanilha, valores: dict) -> None:
        for chave, coluna in self.colunas.items():
            bruto = valores.get(chave)
            valor, _ = ValorRegistroPlanilha.raw_objects.get_or_create(
                registro=registro,
                coluna=coluna,
                defaults={"cliente_id": registro.cliente_id},
            )
            aplicar_valor(valor, coluna, bruto)
            valor.is_deleted = False
            valor.save()


def _texto_da_chave(bruto) -> str:
    if bruto is None:
        return ""
    if isinstance(bruto, tuple):
        return str(bruto[1])
    if isinstance(bruto, (datetime, date)):
        return bruto.isoformat()
    return str(bruto).strip()[:150]


def aplicar_valor(valor: ValorRegistroPlanilha, coluna: ColunaPlanilha, bruto) -> None:
    """Guarda ``bruto`` no campo tipado correto de ``valor``."""

    valor.valor_texto = ""
    valor.valor_numero = None
    valor.valor_data = None
    valor.valor_booleano = None
    valor.valor_referencia_id = None

    if bruto is None or bruto == "":
        return

    tipo = coluna.tipo
    if tipo in (ColunaPlanilha.Tipo.INTEIRO, ColunaPlanilha.Tipo.DECIMAL):
        valor.valor_numero = bruto
    elif tipo == ColunaPlanilha.Tipo.DATA:
        valor.valor_data = bruto
    elif tipo == ColunaPlanilha.Tipo.BOOLEANO:
        valor.valor_booleano = bool(bruto)
    elif tipo in ColunaPlanilha.TIPOS_RELACIONAIS:
        referencia_id, rotulo = bruto if isinstance(bruto, tuple) else (None, bruto)
        valor.valor_referencia_id = referencia_id
        valor.valor_texto = str(rotulo)
    elif tipo == ColunaPlanilha.Tipo.ARQUIVO:
        valor.valor_texto = str(bruto)
    else:
        valor.valor_texto = str(bruto)


# ----------------------------------------------------------------------
# Exportação
# ----------------------------------------------------------------------


class PlanilhaExportService:
    """Exporta registros de um modelo de planilha para XLSX ou CSV."""

    @staticmethod
    def montar_linhas(modelo: ModeloPlanilha, registros) -> tuple[list[str], list[list[str]]]:
        colunas = list(modelo.colunas_visiveis())
        cabecalhos = [coluna.titulo for coluna in colunas]
        linhas: list[list[str]] = []
        for registro in registros:
            valores = registro.valores_por_chave()
            linhas.append(
                [
                    valores[coluna.chave].valor_exibicao()
                    if coluna.chave in valores
                    else ""
                    for coluna in colunas
                ]
            )
        return cabecalhos, linhas

    @classmethod
    def para_csv(cls, modelo: ModeloPlanilha, registros) -> bytes:
        cabecalhos, linhas = cls.montar_linhas(modelo, registros)
        buffer = io.StringIO()
        escritor = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
        escritor.writerow(cabecalhos)
        escritor.writerows(linhas)
        return buffer.getvalue().encode("utf-8-sig")

    @classmethod
    def para_xlsx(cls, modelo: ModeloPlanilha, registros) -> bytes:
        import openpyxl
        from openpyxl.styles import Font

        cabecalhos, linhas = cls.montar_linhas(modelo, registros)
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = (modelo.nome or "Planilha")[:31]
        sheet.append(cabecalhos)
        for celula in sheet[1]:
            celula.font = Font(bold=True)
        for linha in linhas:
            sheet.append(linha)
        for indice, cabecalho in enumerate(cabecalhos, start=1):
            largura = max(len(cabecalho) + 4, 14)
            sheet.column_dimensions[
                openpyxl.utils.get_column_letter(indice)
            ].width = min(largura, 50)
        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    @classmethod
    def modelo_em_branco_xlsx(cls, modelo: ModeloPlanilha) -> bytes:
        """Gera um arquivo modelo com os cabeçalhos configurados."""

        return cls.para_xlsx(modelo, [])

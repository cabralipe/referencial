"""Agrega modelos de documentos institucionais."""

from documents.ppp.models import PlanoMetaPPP
from documents.publication.models import DocumentoPublicacao
from documents.referencial.models import ReferencialHabilidade
from documents.versioning.models import DocumentoVersao

__all__ = [
    "PlanoMetaPPP",
    "ReferencialHabilidade",
    "DocumentoVersao",
    "DocumentoPublicacao",
]


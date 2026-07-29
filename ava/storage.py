from django.core.files.storage import storages


def private_ava_storage():
    """Retorna o storage privado sem expor uma URL pública para os arquivos."""

    return storages["private"]

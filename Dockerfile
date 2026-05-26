# Use uma imagem oficial do Python como base
FROM python:3.12-slim

# Define variáveis de ambiente para evitar arquivos .pyc e logs em buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias para o WeasyPrint e PostgreSQL
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o restante do código
COPY . /app/

# Coleta arquivos estáticos
RUN python manage.py collectstatic --noinput

# Expõe a porta que o Gunicorn usará
EXPOSE 8000

# Comando padrão (pode ser sobrescrito pelo render.yaml ou entrypoint)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]


import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from curriculum.models import Resposta
from api.v1.serializers import RespostaSerializer
from rest_framework.test import APIRequestFactory

# Create a dummy request
factory = APIRequestFactory()
request = factory.get('/')

# Fetch some responses
respostas = Resposta.objects.all()[:5]
print(f"Total entries: {len(respostas)}")

for r in respostas:
    serializer = RespostaSerializer(r, context={'request': request})
    print(f"ID: {r.id}, Autor: {r.autor_id}, Serialized Autor: {serializer.data.get('autor')}")

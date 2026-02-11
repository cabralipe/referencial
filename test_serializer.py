
from django.contrib.auth import get_user_model
from core.models import AuditLog
from api.v1.admin_serializers import AuditLogAdminSerializer

User = get_user_model()

# Create a test user if not exists
user, _ = User.objects.get_or_create(email="test@example.com", defaults={"nome": "Test User"})
print(f"User ID: {user.id}")

# Create a dummy audit log
log = AuditLog.objects.create(
    usuario_id=user.id,
    entidade="teste",
    entidade_id="1",
    acao="created",
    diff_json={}
)

# Serialize it
serializer = AuditLogAdminSerializer(log)
print(f"Serialized usuario_id: {serializer.data['usuario_id']}")

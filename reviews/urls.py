from django.urls import path

from .views_reviewer import reviewer_inbox, reviewer_mark_in_progress, reviewer_mural_download, reviewer_review_detail

urlpatterns = [
    path("revisor/inbox", reviewer_inbox, name="reviewer_inbox"),
    path("revisor/revisoes/<int:revisao_id>", reviewer_review_detail, name="reviewer_review_detail"),
    path("revisor/revisoes/<int:revisao_id>/em-andamento", reviewer_mark_in_progress, name="reviewer_mark_in_progress"),
    path("revisor/mural/<str:mural_id>/anexos/<int:anexo_index>/download", reviewer_mural_download, name="reviewer_mural_download"),
]

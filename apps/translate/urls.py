from django.urls import path

from translate.views import TranslateApiView, LanguageApiView, TranslateAdminApiView

urlpatterns = [
    path('<str:lang>', TranslateApiView.as_view()),
    path('', TranslateApiView.as_view()),
    path('admin/', TranslateAdminApiView.as_view()),
    path('language/', LanguageApiView.as_view()),
]
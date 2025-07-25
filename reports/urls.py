from django.urls import path
from django.http import JsonResponse

from .views import start_interview, submit_answers, save_report, get_all_reports

def home(request):
    return JsonResponse({"message": "MockTalk backend is working ✅"})

urlpatterns = [
    path('', home),  # This will serve the root path "/"
    path("api/start-interview/", start_interview),
    path("api/submit-answers/", submit_answers),
    path('api/save-report/', save_report),
    path('api/reports/', get_all_reports),
]

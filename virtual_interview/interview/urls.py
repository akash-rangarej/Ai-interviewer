from django.urls import path
from django.contrib import admin
from .views import interview_page, process_user_response,generate_feedback

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('login/', login_view, name='login'),
    # path('signup/', signup_view, name='signup'),
    path('', interview_page, name='interview_page'),  # Ensure this is correct
    path('submit/', process_user_response, name='submit'),
     path('generate-feedback/', generate_feedback, name='generate_feedback')  # Ensure this is correct
]
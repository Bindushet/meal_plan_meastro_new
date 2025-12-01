from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.index, name='index'),          # Home page with login/register popup
    #path('dashboard/', views.dashboard, name='dashboard'),
    path('contact/', views.contact_view, name='contact'),
    path('logout/', LogoutView.as_view(next_page='index'), name='logout'),

   
]
# Add this
urlpatterns += [
    path('forgot-password/', views.send_otp_email, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
]

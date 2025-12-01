from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
import re  # for regex validation
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.http import JsonResponse
import random

def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    login_form = AuthenticationForm(request, data=request.POST or None)
    login_error = ''
    register_error = ''

    if request.method == 'POST':
        # LOGIN
        if 'login_submit' in request.POST:
            if login_form.is_valid():
                login(request, login_form.get_user())
                return redirect('dashboard')
            else:
                login_error = 'Invalid username or password.'

        # REGISTER
        elif 'register_submit' in request.POST:
            first_name = request.POST['first_name'].strip()
            last_name = request.POST['last_name'].strip()
            username = request.POST['username'].strip()
            email = request.POST['email'].strip()
            password1 = request.POST['password1']
            password2 = request.POST['password2']

            # ---- Validation Rules ----
            if not re.match(r'^[A-Za-z]+$', first_name):
                register_error = "First name should contain only alphabets."
            elif not re.match(r'^[A-Za-z]+$', last_name):
                register_error = "Last name should contain only alphabets."
            elif not re.match(r'^[A-Za-z][A-Za-z0-9]*$', username):
                register_error = "Username must start with a letter and contain only letters or numbers."
            elif password1 != password2:
                register_error = "Passwords do not match."
            elif User.objects.filter(username=username).exists():
                register_error = "Username already exists."
            elif User.objects.filter(email=email).exists():
                register_error = "Email already exists."
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password1
                )
                login(request, user)
                return redirect('dashboard')

    return render(request, 'index.html', {
        'login_form': login_form,
        'login_error': login_error,
        'register_error': register_error
    })

def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message_text = request.POST.get('message')

        if name and email and message_text:
            try:
                send_mail(
                    subject=f"Contact Form Submission from {name}",
                    message=f"From: {name} <{email}>\n\nMessage:\n{message_text}",
                    from_email=settings.DEFAULT_FROM_EMAIL,   # Your email
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],  # Receive in same email
                    fail_silently=False,
                )
                messages.success(request, "Your message has been sent successfully!")
            except Exception as e:
                messages.error(request, f"Error sending message: {e}")
        else:
            messages.error(request, "Please fill in all fields.")

    return redirect('/')  # Redirect back to homepage (index)


# ---------------- FORGOT PASSWORD OTP SYSTEM ---------------- #

otp_storage = {}

def send_otp_email(request):
    email = request.POST.get("email")
    try:
        User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Email not registered"})

    otp = random.randint(100000, 999999)
    expiry = timezone.now() + timezone.timedelta(minutes=5)
    otp_storage[email] = {"otp": otp, "expiry": expiry}

    send_mail(
        "Password Reset OTP",
        f"Your OTP is {otp}. Valid for 5 minutes.",
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
    )
    return JsonResponse({"status": "success"})


def verify_otp(request):
    email = request.POST.get("email")
    otp = request.POST.get("otp")

    if email not in otp_storage:
        return JsonResponse({"status": "error", "message": "OTP expired or not generated"})

    data = otp_storage[email]
    if timezone.now() > data["expiry"]:
        otp_storage.pop(email)
        return JsonResponse({"status": "error", "message": "OTP expired"})

    if str(data["otp"]) == str(otp):
        return JsonResponse({"status": "success"})

    return JsonResponse({"status": "error", "message": "Invalid OTP"})


def reset_password(request):
    email = request.POST.get("email")
    password = request.POST.get("password")

    user = User.objects.get(email=email)
    user.password = make_password(password)
    user.save()

    otp_storage.pop(email, None)
    return JsonResponse({"status": "success"})

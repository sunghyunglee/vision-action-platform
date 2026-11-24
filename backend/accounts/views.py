from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .forms import SignUpForm
from .serializers import MeSerializer


def signup(request):
    """회원가입 화면(GET)과 처리(POST). 가입하면 바로 로그인시킨다."""
    if request.user.is_authenticated:
        return redirect("analyses:index")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"{user.username}님, 가입을 환영합니다.")
            return redirect("analyses:index")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


@api_view(["GET"])
def me(request):
    """GET /api/v1/auth/me/ : 로그인한 본인 정보."""
    return Response(MeSerializer(request.user).data)

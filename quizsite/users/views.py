from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.db.models import Count, Sum
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone

from quizzes.models import CompetitionEntry, Quiz, ReattemptRequest


class UserLoginView(LoginView):
    """Login view for regular quiz participants (non-staff users)."""
    template_name = 'users/login.html'

    def form_valid(self, form):
        user = form.get_user()
        if user.is_staff:
            form.add_error(None, "Please use the admin login page to sign in as an admin.")
            return self.form_invalid(form)
        messages.success(self.request, f"Welcome back, {user.username}!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Incorrect username or password.")
        return super().form_invalid(form)


class AdminLoginView(LoginView):
    """Separate login view for staff/admin users only."""
    template_name = 'users/admin_login.html'

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_staff:
            form.add_error(None, "Only admin/staff accounts can sign in here.")
            return self.form_invalid(form)
        messages.success(self.request, f"Signed in as admin {user.username}.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Incorrect username or password.")
        return super().form_invalid(form)


@login_required
def logout_view(request):
    """Log the user out with a friendly message."""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')


def register(request):
    """Public registration for regular quiz participants."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'users/register.html', {'form': form})


def _staff_check(user):
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(_staff_check)
def admin_dashboard(request):
    """
    Staff-only dashboard.

    - Regular users log in via /login and only see quizzes/results.
    - Admins log in via /admin-login or /admin/ and can manage quizzes and approvals.
    """
    # Aggregate per-user stats from competition entries
    user_stats = (
        CompetitionEntry.objects
        .values('user__username')
        .annotate(
            quizzes_taken=Count('id'),
            total_score=Sum('score'),
        )
        .order_by('-quizzes_taken')[:25]
    )

    # Aggregate per-quiz stats
    quiz_stats = (
        Quiz.objects
        .annotate(
            attempts=Count('entries', distinct=True),
            total_score=Sum('entries__score'),
        )
        .order_by('-start_time')[:25]
    )

    # Recent activity stream
    recent_entries = (
        CompetitionEntry.objects
        .select_related('user', 'quiz')
        .order_by('-joined_at')[:20]
    )

    # Pending re-attempt requests
    pending_reattempts = (
        ReattemptRequest.objects
        .select_related('user', 'quiz')
        .filter(status='pending')
        .order_by('-created_at')
    )

    # Approved and rejected lists for admin review/history
    approved_reattempts = (
        ReattemptRequest.objects.select_related('user', 'quiz')
        .filter(status='approved')
        .order_by('-processed_at')[:50]
    )

    rejected_reattempts = (
        ReattemptRequest.objects.select_related('user', 'quiz')
        .filter(status='rejected')
        .order_by('-processed_at')[:50]
    )

    context = {
        'user_stats': user_stats,
        'quiz_stats': quiz_stats,
        'recent_entries': recent_entries,
        'pending_reattempts': pending_reattempts,
        'approved_reattempts': approved_reattempts,
        'rejected_reattempts': rejected_reattempts,
    }
    return render(request, 'users/admin_dashboard.html', context)


@login_required
@user_passes_test(_staff_check)
@transaction.atomic
def handle_reattempt_request(request, pk):
    """Approve or reject a user's re-attempt request (admin only)."""
    if request.method != 'POST':
        return redirect('admin_dashboard')

    decision = request.POST.get('decision')
    reattempt = get_object_or_404(ReattemptRequest, pk=pk, status='pending')

    # Record who processed this request and when
    reattempt.processed_by = request.user
    reattempt.processed_at = timezone.now()

    if decision == 'approve':
        reattempt.status = 'approved'
        # Clear the stored entry reference before deleting the CompetitionEntry rows
        # This avoids a foreign-key constraint error in SQLite where the
        # ReattemptRequest would still reference an entry that is being deleted
        reattempt.entry = None
        # reset notification flag so user will see an in-site flash on next visit
        reattempt.user_notified = False
        # mark as not used yet (user still has to take the re-attempt)
        reattempt.used = False
        reattempt.save()

        # Now safely delete any previous attempts so the user can start fresh
        CompetitionEntry.objects.filter(quiz=reattempt.quiz, user=reattempt.user).delete()
    else:
        reattempt.status = 'rejected'
        # ensure user will be notified of the rejection
        reattempt.user_notified = False
        # rejected requests are not usable
        reattempt.used = False
        reattempt.save()

    return redirect('admin_dashboard')
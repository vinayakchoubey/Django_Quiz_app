from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Quiz(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed')
    )
    MODE_CHOICES = (
        ('practice', 'Practice'),
        ('test', 'Test'),
        ('competition', 'Competition'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.PositiveIntegerField(help_text='Duration in minutes', default=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='test')
    max_questions = models.PositiveIntegerField(null=True, blank=True, help_text='Limit number of questions in an attempt')
    access_token = models.CharField(max_length=64, null=True, blank=True, help_text='If set, users must enter this token to attempt')

    def __str__(self):
        return self.title

    def is_active(self):
        """Check if quiz is currently active based on schedule"""
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    def compute_status(self):
        """Derive status from current time and schedule."""
        now = timezone.now()
        if now < self.start_time:
            return 'scheduled'
        if now > self.end_time:
            return 'completed'
        return 'ongoing'
    
    def total_marks(self):
        """Calculate total marks for this quiz"""
        qs = self.questions.all().order_by('order')
        if self.max_questions:
            qs = qs[: self.max_questions]
        return sum(question.marks for question in qs)
    
    def get_question_count(self):
        """Get total number of questions"""
        count = self.questions.count()
        if self.max_questions:
            return min(count, self.max_questions)
        return count


class Question(models.Model):
    TYPE_CHOICES = (
        ('mcq', 'MCQ'),
        ('text', 'Text')
    )

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    qtype = models.CharField(max_length=10, choices=TYPE_CHOICES, default='mcq')
    marks = models.IntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}"


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:50]


class CompetitionEntry(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(default=0)

    # ✅ Timer-related fields
    allowed_finish_at = models.DateTimeField(null=True, blank=True)
    time_remaining = models.PositiveIntegerField(
        null=True, blank=True, help_text="Time remaining in seconds"
    )

    class Meta:
        unique_together = ('quiz', 'user')
        verbose_name_plural = "Competition entries"

    def time_taken(self):
        """Calculate actual time taken to complete quiz"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0

    def get_correct_answers_count(self):
        """Count number of correctly answered questions"""
        return self.answers.filter(marks_awarded__gt=0).count()

    def get_total_questions(self):
        """Get total number of questions in the quiz"""
        return self.quiz.get_question_count()

    def get_answered_questions_count(self):
        """Count how many questions have been answered"""
        return self.answers.count()

    def get_percentage_score(self):
        """Calculate percentage score"""
        total_marks = self.quiz.total_marks()
        return (self.score / total_marks) * 100 if total_marks > 0 else 0

    def is_time_up(self):
        """Check if time has expired for this quiz attempt"""
        if self.allowed_finish_at:
            return timezone.now() > self.allowed_finish_at
        return False

    def get_time_remaining_seconds(self):
        """Calculate time remaining in seconds (real-time)"""
        if self.allowed_finish_at and not self.finished_at:
            remaining = (self.allowed_finish_at - timezone.now()).total_seconds()
            return max(0, remaining)
        return 0

    def start_quiz_timer(self):
        """Initialize the quiz timer when user starts the quiz"""
        if not self.started_at:
            self.started_at = timezone.now()
            # Set allowed finish time based on quiz duration
            self.allowed_finish_at = self.started_at + timedelta(minutes=self.quiz.duration)
            self.save()

    def is_in_progress(self):
        """Check if quiz is currently in progress"""
        return self.started_at and not self.finished_at and not self.is_time_up()

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title}"


class Answer(models.Model):
    entry = models.ForeignKey(CompetitionEntry, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, null=True, blank=True, on_delete=models.SET_NULL)
    text_answer = models.TextField(blank=True)
    marks_awarded = models.FloatField(default=0)
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entry', 'question')

    def is_correct(self):
        """Check if answer is correct"""
        if self.question.qtype == 'mcq' and self.selected_option:
            return self.selected_option.is_correct
        return False

    def save(self, *args, **kwargs):
        """Auto-calculate marks for MCQ questions"""
        if self.question.qtype == 'mcq' and self.selected_option:
            if self.selected_option.is_correct:
                self.marks_awarded = self.question.marks
            else:
                self.marks_awarded = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Answer by {self.entry.user.username} for {self.question}"


class ReattemptRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='reattempt_requests')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reattempt_requests')
    entry = models.ForeignKey(CompetitionEntry, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='processed_reattempt_requests',
    )
    # Whether we've shown an in-site notification to the requesting user
    user_notified = models.BooleanField(default=False)
    # Whether the approved re-attempt has been consumed by the user
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Re-attempt request"
        verbose_name_plural = "Re-attempt requests"

    def __str__(self):
        return f"Re-attempt {self.quiz.title} for {self.user.username} ({self.status})"
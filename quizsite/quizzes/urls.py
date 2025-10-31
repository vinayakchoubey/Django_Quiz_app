from django.urls import path
from . import views

# NO app_name = 'quizzes' - removed or commented out

urlpatterns = [
	path('', views.home, name='home'),
	path('quiz/create/', views.create_quiz, name='create_quiz'),
	path('quiz/<int:pk>/', views.quiz_detail, name='quiz_detail'),
	path('quiz/<int:pk>/join/', views.join_quiz, name='join_quiz'),
	path('quiz/<int:pk>/start/', views.start_quiz, name='start_quiz'),
	path('quiz/<int:pk>/question/<int:qnum>/', views.quiz_question, name='quiz_question'),
	path('quiz/<int:pk>/finish/', views.finish_quiz, name='finish_quiz'),
	path('quiz/<int:pk>/leaderboard/', views.leaderboard, name='leaderboard'),
	path('quiz/<int:pk>/status/', views.quiz_status, name='quiz_status'),
	path('quiz/<int:pk>/not-active/', views.quiz_not_active, name='quiz_not_active'),
	path('quiz/<int:pk>/delete/', views.delete_quiz, name='delete_quiz'),
]
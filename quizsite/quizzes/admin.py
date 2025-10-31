from django.contrib import admin
from .models import Quiz, Question, Option, CompetitionEntry, Answer

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4

class QuestionAdmin(admin.ModelAdmin):
    inlines = [OptionInline]
    list_display = ('quiz', 'order', 'text', 'qtype')

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]
    list_display = ('title', 'start_time', 'end_time', 'status', 'duration')
    list_filter = ('status', 'start_time')

admin.site.register(CompetitionEntry)
admin.site.register(Answer)
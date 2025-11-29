import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Answer, CompetitionEntry, Option, Question, Quiz, ReattemptRequest
from .services import AIServiceError, generate_ai_quiz


def _session_access_key(quiz_id: int) -> str:
	return f"quiz_access_{quiz_id}"


def home(request):
	"""Home page showing all quizzes"""
	quizzes = Quiz.objects.none()
	if request.user.is_authenticated:
		quizzes = Quiz.objects.all().order_by('-start_time')
	# Refresh status for display (scheduled/ongoing/completed)
	for q in quizzes:
		new_status = q.compute_status()
		if new_status != q.status:
			q.status = new_status
			q.save(update_fields=['status'])
	return render(request, 'quizzes/home.html', {'quizzes': quizzes})


@login_required
def quiz_detail(request, pk):
	"""Quiz detail page before starting"""
	quiz = get_object_or_404(Quiz, pk=pk)
	# Refresh status for accuracy
	new_status = quiz.compute_status()
	if new_status != quiz.status:
		quiz.status = new_status
		quiz.save(update_fields=['status'])
	entry, created = CompetitionEntry.objects.get_or_create(
		quiz=quiz, 
		user=request.user
	)

	# Latest re-attempt request (if any)
	reattempt_request = None
	if request.user.is_authenticated:
		reattempt_request = (
			ReattemptRequest.objects
			.filter(quiz=quiz, user=request.user)
			.order_by('-created_at')
			.first()
		)

	# If the reattempt has been processed and the user hasn't been notified yet,
	# show a flash message once and mark it notified so it doesn't repeat.
	if reattempt_request and not reattempt_request.used and reattempt_request.status != 'pending' and not reattempt_request.user_notified:
		# Only notify the requesting user (defensive check)
		if reattempt_request.user == request.user:
			if reattempt_request.status == 'approved':
				messages.success(request, 'Your re-attempt request was approved by the admin. You may try the quiz again when it is active.')
			elif reattempt_request.status == 'rejected':
				messages.error(request, 'Your re-attempt request was rejected by the admin.')
			reattempt_request.user_notified = True
			reattempt_request.save(update_fields=['user_notified'])

	# Access token handling
	access_ok = False
	if quiz.access_token:
		access_ok = bool(request.session.get(_session_access_key(quiz.pk)))
		if request.method == 'POST' and 'access_token' in request.POST:
			posted_token = request.POST.get('access_token', '').strip()
			if posted_token and posted_token == quiz.access_token:
				request.session[_session_access_key(quiz.pk)] = True
				access_ok = True
				return redirect('quiz_detail', pk=quiz.pk)

	return render(request, 'quizzes/quiz_detail.html', {
		'quiz': quiz,
		'entry': entry,
		'has_access': access_ok if quiz.access_token else True,
		'current_time': timezone.now(),
		'reattempt_request': reattempt_request,
	})


@login_required
def join_quiz(request, pk):
	"""Join a quiz and create competition entry"""
	quiz = get_object_or_404(Quiz, pk=pk)

	# Check if user already has an entry
	entry, created = CompetitionEntry.objects.get_or_create(
		quiz=quiz,
		user=request.user
	)

	return redirect('start_quiz', pk=quiz.pk)


@login_required
def start_quiz(request, pk):
	"""Start the quiz and initialize timer"""
	quiz = get_object_or_404(Quiz, pk=pk)
	entry = get_object_or_404(CompetitionEntry, quiz=quiz, user=request.user)

	# Enforce access token if present
	if quiz.access_token:
		if not request.session.get(_session_access_key(quiz.pk)):
			return redirect('quiz_detail', pk=quiz.pk)
	
	# ✅ Check if quiz is active based on schedule
	if not quiz.is_active():
		return render(request, 'quizzes/quiz_not_active.html', {
			'quiz': quiz,
			'current_time': timezone.now()
		})
	
	# ✅ Set start time and calculate finish time if not already set
	if not entry.started_at:
		entry.started_at = timezone.now()
		# Set allowed finish time (quiz duration in minutes)
		entry.allowed_finish_at = entry.started_at + timedelta(minutes=quiz.duration)
		entry.save()
		print(f"Quiz started. Must finish by: {entry.allowed_finish_at}")

		# If this start corresponds to an approved re-attempt, mark it used
		try:
			ra = (
				ReattemptRequest.objects
				.filter(quiz=quiz, user=request.user, status='approved', used=False)
				.order_by('-created_at')
				.first()
			)
			if ra:
				ra.used = True
				ra.save(update_fields=['used'])
		except Exception:
			# Defensive: don't let notification logic block starting the quiz
			pass
	
	# ✅ Check if time is already up (in case page was reloaded)
	if entry.is_time_up():
		return redirect('finish_quiz', pk=quiz.pk)
	
	# Redirect to first question
	limit = quiz.max_questions or quiz.questions.count()
	first_question = quiz.questions.order_by('order')[:limit].first()
	if first_question:
		return redirect('quiz_question', pk=quiz.pk, qnum=first_question.order)
	else:
		return redirect('finish_quiz', pk=quiz.pk)


@login_required
def quiz_question(request, pk, qnum):
	"""Display and process individual quiz questions with timer"""
	quiz = get_object_or_404(Quiz, pk=pk)
	entry = get_object_or_404(CompetitionEntry, quiz=quiz, user=request.user)
	
	# ✅ CHECK IF TIME IS UP BEFORE PROCESSING ANYTHING
	if entry.is_time_up():
		return redirect('finish_quiz', pk=quiz.pk)
	
	# ✅ Check if quiz is still active based on schedule
	if not quiz.is_active():
		return redirect('finish_quiz', pk=quiz.pk)
	
	# Prepare ordered questions respecting max_questions
	limit = quiz.max_questions or quiz.questions.count()
	ordered_questions = list(Question.objects.filter(quiz=quiz).order_by('order')[:limit])
	question = next((q for q in ordered_questions if q.order == qnum), None)
	if not question:
		return redirect('finish_quiz', pk=quiz.pk)

	# Finish-now shortcut
	if request.method == 'POST' and request.POST.get('finish_now'):
		return redirect('finish_quiz', pk=quiz.pk)
	
	if request.method == 'POST':
		# ✅ CHECK TIME AGAIN BEFORE PROCESSING ANSWER
		if entry.is_time_up():
			return redirect('finish_quiz', pk=quiz.pk)
			
		if question.qtype == 'mcq':
			selected_option_id = request.POST.get('option')
			if selected_option_id:
				try:
					selected_option = Option.objects.get(id=selected_option_id)
					
					# Save or update answer
					answer, created = Answer.objects.update_or_create(
						entry=entry,
						question=question,
						defaults={'selected_option': selected_option}
					)
					
					# Auto-score MCQ
					if selected_option.is_correct:
						answer.marks_awarded = question.marks
					else:
						answer.marks_awarded = 0
					answer.save()
					
				except Option.DoesNotExist:
					pass
		else:  # Text question
			text_answer = request.POST.get('text_answer')
			if text_answer:
				Answer.objects.update_or_create(
					entry=entry,
					question=question,
					defaults={'text_answer': text_answer}
				)

		# If user explicitly submitted quiz from any question
		if request.POST.get('submit_quiz'):
			return redirect('finish_quiz', pk=quiz.pk)
		
		# Navigation within limited set
		idx = next((i for i, q in enumerate(ordered_questions) if q.order == question.order), None)
		if idx is None or idx == len(ordered_questions) - 1:
			return redirect('finish_quiz', pk=quiz.pk)
		else:
			next_question = ordered_questions[idx + 1]
			return redirect('quiz_question', pk=quiz.pk, qnum=next_question.order)
	
	# ✅ CALCULATE TIME REMAINING FOR TEMPLATE
	time_remaining = 0
	if entry.allowed_finish_at:
		time_remaining = max(0, (entry.allowed_finish_at - timezone.now()).total_seconds())
	# Progress counts
	total_questions = quiz.get_question_count()
	answered_count = entry.answers.count()
	current_answer = entry.answers.filter(question=question).select_related('selected_option').first()
	
	return render(request, 'quizzes/question.html', {
		'quiz': quiz,
		'question': question,
		'entry': entry,
		'time_remaining': int(time_remaining),  # ✅ Pass remaining time in seconds
		'answered_count': answered_count,
		'total_questions': total_questions,
		'current_answer': current_answer,
	})


@login_required
def finish_quiz(request, pk):
	"""
	Handle quiz completion - both manual submission and automatic time-up
	"""
	quiz = get_object_or_404(Quiz, pk=pk)
	entry = get_object_or_404(CompetitionEntry, quiz=quiz, user=request.user)
	
	# Mark as finished if not already
	if not entry.finished_at:
		entry.finished_at = timezone.now()
		# Aggregate total score and counts in one pass
		aggs = entry.answers.aggregate(
			total_score=Sum('marks_awarded'),
			answered_count=Count('id'),
			correct_count=Count('id', filter=Q(marks_awarded__gt=0))
		)
		entry.score = aggs.get('total_score') or 0
		entry.save(update_fields=['finished_at', 'score'])
	else:
		aggs = entry.answers.aggregate(
			total_score=Sum('marks_awarded'),
			answered_count=Count('id'),
			correct_count=Count('id', filter=Q(marks_awarded__gt=0))
		)
	
	# Check if quiz was finished due to time up
	time_up = False
	if entry.allowed_finish_at and entry.finished_at:
		time_up = entry.finished_at > entry.allowed_finish_at
	
	# Get quiz results data
	total_questions = quiz.get_question_count()
	answered_questions = aggs.get('answered_count') or 0
	correct_answers = aggs.get('correct_count') or 0
	incorrect_answers = max(0, answered_questions - correct_answers)
	percentage_score = 0
	max_marks = quiz.total_marks()
	if max_marks:
		percentage_score = (entry.score / max_marks) * 100

	# Build per-question details
	limit = quiz.max_questions or quiz.questions.count()
	ordered_questions = list(Question.objects.filter(quiz=quiz).order_by('order')[:limit])
	answers_by_qid = {a.question_id: a for a in entry.answers.select_related('selected_option').all()}
	answers_detail = []
	for q in ordered_questions:
		ans = answers_by_qid.get(q.id)
		selected_text = None
		selected_id = None
		is_correct = False
		correct_texts = []
		if q.qtype == 'mcq':
			if ans and ans.selected_option:
				selected_text = ans.selected_option.text
				selected_id = ans.selected_option_id
				is_correct = ans.selected_option.is_correct
			# collect correct options
			for opt in q.options.all():
				if opt.is_correct:
					correct_texts.append(opt.text)
		else:
			selected_text = ans.text_answer if ans else ''
			is_correct = False
		answers_detail.append({
			'order': q.order,
			'question': q.text,
			'qtype': q.qtype,
			'selected_text': selected_text,
			'selected_id': selected_id,
			'correct_options': correct_texts,
			'is_correct': is_correct,
			'marks': q.marks,
		})

	reattempt_request = None
	if request.user.is_authenticated:
		reattempt_request = (
			ReattemptRequest.objects
			.filter(quiz=quiz, user=request.user)
			.order_by('-created_at')
			.first()
		)

	return render(request, 'quizzes/result.html', {
		'quiz': quiz,
		'entry': entry,
		'score': entry.score,
		'total_questions': total_questions,
		'answered_questions': answered_questions,
		'correct_answers': correct_answers,
		'incorrect_answers': incorrect_answers,
		'time_up': time_up,
		'time_taken': entry.time_taken(),
		'percentage_score': percentage_score,
		'answers_detail': answers_detail,
		'reattempt_request': reattempt_request,
	})


def leaderboard(request, pk):
	"""Display quiz leaderboard with enhanced features"""
	quiz = get_object_or_404(Quiz, pk=pk)
	entries = quiz.entries.filter(finished_at__isnull=False).order_by('-score', 'finished_at')
	
	# Get user's entry and rank
	user_entry = None
	user_entry_rank = None
	if request.user.is_authenticated:
		try:
			user_entry = CompetitionEntry.objects.get(quiz=quiz, user=request.user)
			# Calculate rank
			for index, entry in enumerate(entries, 1):
				if entry.user == request.user:
					user_entry_rank = index
					break
		except CompetitionEntry.DoesNotExist:
			pass
	
	return render(request, 'quizzes/leaderboard.html', {
		'quiz': quiz,
		'entries': entries,
		'user_entry': user_entry,
		'user_entry_rank': user_entry_rank,
	})


# ✅ AJAX endpoint for real-time leaderboard updates
@login_required
def quiz_status(request, pk):
	"""AJAX endpoint for real-time quiz status and leaderboard"""
	quiz = get_object_or_404(Quiz, pk=pk)

	leaderboard_data = list(
		quiz.entries.filter(finished_at__isnull=False).order_by('-score', 'finished_at')[:10].values(
			'user__username', 'score'
		)
	)

	data = {
		'status': quiz.status,
		'leaderboard': leaderboard_data,
		'server_time': timezone.now().isoformat()
	}

	return JsonResponse(data)


@login_required
def quiz_not_active(request, pk):
	"""Display quiz not active page"""
	quiz = get_object_or_404(Quiz, pk=pk)
	return render(request, 'quizzes/quiz_not_active.html', {
		'quiz': quiz,
		'current_time': timezone.now()
	})


@login_required
def create_quiz(request):
	"""Create a quiz with questions and options, including schedule and access token"""
	if not request.user.is_staff:
		return redirect('home')
	if request.method == 'POST':
		# Quiz core fields
		title = request.POST.get('title', '').strip()
		description = request.POST.get('description', '').strip()
		mode = request.POST.get('mode', 'test')
		start_time_str = request.POST.get('start_time')
		end_time_str = request.POST.get('end_time')
		duration = int(request.POST.get('duration', '10') or 10)
		max_questions = request.POST.get('max_questions')
		access_token = request.POST.get('access_token', '').strip() or None

		# Basic validation
		if not title or not start_time_str or not end_time_str:
			return render(request, 'quizzes/create.html', {
				'error': 'Title, start time and end time are required.'
			})

		# Parse datetimes from input (datetime-local = naive local time) and make aware
		from django.utils.dateparse import parse_datetime
		start_dt = parse_datetime(start_time_str)
		end_dt = parse_datetime(end_time_str)
		if not start_dt or not end_dt:
			return render(request, 'quizzes/create.html', {
				'error': 'Invalid date/time format.'
			})
		# Make timezone-aware assuming current timezone for naive input to avoid date shifts
		if timezone.is_naive(start_dt):
			start_dt = timezone.make_aware(start_dt, timezone.get_current_timezone())
		if timezone.is_naive(end_dt):
			end_dt = timezone.make_aware(end_dt, timezone.get_current_timezone())
		# Validate order
		if end_dt <= start_dt:
			return render(request, 'quizzes/create.html', {
				'error': 'End time must be after start time.'
			})

		quiz = Quiz.objects.create(
			title=title,
			description=description,
			mode=mode,
			start_time=start_dt,
			end_time=end_dt,
			duration=duration,
			max_questions=int(max_questions) if max_questions else None,
			access_token=access_token,
		)

		# Collect dynamic questions
		index = 1
		while True:
			q_text = request.POST.get(f'question_text_{index}')
			if not q_text:
				break
			q_type = request.POST.get(f'question_type_{index}', 'mcq')
			q_marks = int(request.POST.get(f'question_marks_{index}', '1') or 1)
			question = Question.objects.create(
				quiz=quiz,
				text=q_text.strip(),
				qtype=q_type,
				marks=q_marks,
				order=index,
			)
			# options for mcq
			if q_type == 'mcq':
				opt_idx = 1
				while True:
					opt_text = request.POST.get(f'option_{index}_{opt_idx}')
					if not opt_text:
						break
					is_correct = request.POST.get(f'correct_{index}') == str(opt_idx)
					Option.objects.create(question=question, text=opt_text.strip(), is_correct=is_correct)
					opt_idx += 1
			index += 1

		return redirect('quiz_detail', pk=quiz.pk)

	return render(request, 'quizzes/create.html')


@login_required
def delete_quiz(request, pk):
	"""Delete a quiz (staff only). POST required."""
	quiz = get_object_or_404(Quiz, pk=pk)
	if not request.user.is_staff:
		return HttpResponseForbidden("Not allowed")
	if request.method == 'POST':
		quiz.delete()
		return redirect('home')
	return redirect('quiz_detail', pk=pk)


@login_required
@require_POST
def reset_quiz_attempt(request, pk):
	"""(Deprecated) Direct reset is now handled via admin-approved flow."""
	return redirect('quiz_detail', pk=pk)


@login_required
@require_POST
def request_reattempt(request, pk):
	"""User can request a single re-attempt which must be approved by an admin."""
	quiz = get_object_or_404(Quiz, pk=pk)
	entry = CompetitionEntry.objects.filter(quiz=quiz, user=request.user).first()
	if not entry or not entry.finished_at:
		messages.error(request, "You can only request a re-attempt after finishing the quiz.")
		return redirect('quiz_detail', pk=quiz.pk)

	# Block if already approved or pending
	existing = (
		ReattemptRequest.objects
		.filter(quiz=quiz, user=request.user)
		.exclude(status='rejected')
		.exists()
	)
	if existing:
		messages.info(request, "Your re-attempt request is already pending or approved.")
		return redirect('quiz_detail', pk=quiz.pk)

	reason = request.POST.get('reason', '').strip()
	ReattemptRequest.objects.create(
		quiz=quiz,
		user=request.user,
		entry=entry,
		reason=reason,
	)
	messages.success(request, "Re-attempt request sent to the admin.")
	return redirect('quiz_detail', pk=quiz.pk)


@login_required
@require_POST
def generate_quiz_ai(request):
	"""Generate quiz draft using Gemini AI based on provided parameters."""
	if not request.user.is_staff:
		return HttpResponseForbidden("Not allowed")
	try:
		payload = json.loads(request.body.decode('utf-8'))
	except json.JSONDecodeError:
		return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

	try:
		data = generate_ai_quiz(payload)
	except AIServiceError as exc:
		return JsonResponse({'error': str(exc)}, status=400)

	return JsonResponse(data)
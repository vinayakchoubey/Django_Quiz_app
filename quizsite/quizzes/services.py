import json
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings


GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
)


class AIServiceError(Exception):
    """Raised when the Gemini service cannot return quiz content."""


@dataclass
class AIQuizPrompt:
    topic: str
    title: str
    description: str
    difficulty: str
    duration: int
    question_count: int
    max_questions: int | None
    start_time: str | None
    end_time: str | None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "AIQuizPrompt":
        def _int(value: Any, default: int) -> int:
            try:
                return max(1, int(value))
            except (TypeError, ValueError):
                return default

        return cls(
            topic=(payload.get("topic") or "").strip(),
            title=(payload.get("title") or "").strip(),
            description=(payload.get("description") or "").strip(),
            difficulty=(payload.get("difficulty") or "medium").strip() or "medium",
            duration=_int(payload.get("duration"), 10),
            question_count=_int(payload.get("question_count"), 5),
            max_questions=_int(payload.get("max_questions"), 0) or None,
            start_time=(payload.get("start_time") or "").strip() or None,
            end_time=(payload.get("end_time") or "").strip() or None,
        )

    def build_prompt(self) -> str:
        base_title = self.title or f"{self.topic.title()} Challenge"
        summary_lines = [
            f"Topic: {self.topic or 'General Knowledge'}",
            f"Suggested Title: {base_title}",
            f"Description seed: {self.description or 'Create an engaging quiz'}",
            f"Difficulty: {self.difficulty}",
            f"Duration (minutes): {self.duration}",
            f"Question target: {self.question_count}",
        ]
        if self.max_questions:
            summary_lines.append(f"Max questions per attempt: {self.max_questions}")
        if self.start_time:
            summary_lines.append(f"Start schedule: {self.start_time}")
        if self.end_time:
            summary_lines.append(f"End schedule: {self.end_time}")

        summary = "\n".join(f"- {line}" for line in summary_lines)

        template = f"""
        You are an assistant tasked with drafting quizzes for an educational app.
        Based on the following parameters produce engaging, factual questions.

        Parameters:
        {summary}

        Respond ONLY with valid JSON following this schema:
        {{
            "title": "string",
            "description": "string",
            "duration": integer,
            "max_questions": integer,
            "questions": [
                {{
                    "text": "string",
                    "qtype": "mcq" or "text",
                    "marks": integer,
                    "options": [
                        {{"text": "string", "is_correct": boolean}}
                    ]
                }}
            ]
        }}

        Rules:
        - Provide at least {self.question_count} questions.
        - Use "mcq" when options are provided; only provide "text" when the answer is free-form.
        - Ensure exactly one option per question has "is_correct": true (unless qtype is "text").
        - Keep questions short and focused on the topic.
        - Marks should be 1 unless there is a good reason to vary them.
        - Do not include explanations, markdown fences, or trailing commentary.
        """
        return textwrap.dedent(template).strip()


def _extract_candidate_text(response_json: Dict[str, Any]) -> str:
    candidates = response_json.get("candidates") or []
    if not candidates:
        raise AIServiceError("Gemini response did not include any candidates.")
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    if not parts:
        raise AIServiceError("Gemini response is missing content parts.")
    text = parts[0].get("text")
    if not text:
        raise AIServiceError("Gemini response does not contain text content.")
    return text.strip()


def _load_json_blob(blob: str) -> Dict[str, Any]:
    cleaned = blob.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIServiceError("Gemini returned content that is not valid JSON.") from exc


def _normalize_questions(raw_questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for idx, question in enumerate(raw_questions, start=1):
        text_value = (question.get("text") or "").strip()
        if not text_value:
            continue
        qtype = question.get("qtype", "mcq")
        if qtype not in {"mcq", "text"}:
            qtype = "mcq"
        marks = question.get("marks")
        try:
            marks = int(marks)
            if marks <= 0:
                marks = 1
        except (TypeError, ValueError):
            marks = 1
        normalized_question: Dict[str, Any] = {
            "text": text_value,
            "qtype": qtype,
            "marks": marks,
            "order": idx,
        }
        if qtype == "mcq":
            options = question.get("options") or []
            cleaned_options = []
            has_correct = False
            for option in options:
                opt_text = (option.get("text") or "").strip()
                if not opt_text:
                    continue
                is_correct = bool(option.get("is_correct"))
                has_correct = has_correct or is_correct
                cleaned_options.append({"text": opt_text, "is_correct": is_correct})
            if not cleaned_options:
                continue
            if not has_correct:
                # Default first option to correct if none flagged
                cleaned_options[0]["is_correct"] = True
            normalized_question["options"] = cleaned_options
        normalized.append(normalized_question)
    return normalized


def generate_ai_quiz(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not settings.GEMINI_API_KEY:
        raise AIServiceError("Gemini API key is missing. Set GEMINI_API_KEY env variable.")

    prompt = AIQuizPrompt.from_payload(payload)
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt.build_prompt()}],
            }
        ],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
    }
    request_data = json.dumps(body).encode("utf-8")
    req = urllib_request.Request(
        f"{GEMINI_API_URL}?key={settings.GEMINI_API_KEY}",
        data=request_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=60) as response:
            payload_bytes = response.read()
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise AIServiceError(f"Gemini API error: {exc.code} {detail}") from exc
    except urllib_error.URLError as exc:
        raise AIServiceError("Unable to reach Gemini API.") from exc

    raw_response = json.loads(payload_bytes)
    text_blob = _extract_candidate_text(raw_response)
    structured = _load_json_blob(text_blob)

    questions = structured.get("questions") or []
    normalized_questions = _normalize_questions(questions)
    if not normalized_questions:
        raise AIServiceError("Gemini did not return any usable questions.")

    max_questions = structured.get("max_questions") or prompt.max_questions or len(
        normalized_questions
    )
    try:
        max_questions = int(max_questions)
    except (TypeError, ValueError):
        max_questions = len(normalized_questions)

    return {
        "title": structured.get("title") or prompt.title,
        "description": structured.get("description") or prompt.description,
        "duration": structured.get("duration") or prompt.duration,
        "max_questions": max_questions,
        "questions": normalized_questions,
    }


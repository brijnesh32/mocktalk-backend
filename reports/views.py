from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from dotenv import load_dotenv
from groq import Groq
from .mongo_models import Report
import os, json, re
from bson import ObjectId
from mongoengine.errors import DoesNotExist

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ─────────────────────────────────────────────
#  HELPER — safe JSON extractor
# ─────────────────────────────────────────────
def extract_json(text):
    """Try to extract valid JSON from messy AI output."""
    text = text.strip()
    # Remove markdown fences
    text = re.sub(r"```json|```", "", text).strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try extracting first JSON array
    match = re.search(r"(\[.*\])", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # Try extracting first JSON object
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────
#  VIEW 1 — Start Interview (generate questions)
# ─────────────────────────────────────────────
@csrf_exempt
def start_interview(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        data = json.loads(request.body)

        name        = data.get("name", "Candidate")
        role        = data.get("role", "")
        education   = data.get("education", "")
        experience  = data.get("experience", "")
        skills      = data.get("skills") or []
        question_count = int(data.get("question_count", 5))

        # Normalise skills
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]

        # ── IMPROVED PROMPT ──────────────────────────────────────────
        # More specific, role-aware, varied question types
        prompt = f"""
You are an expert technical and HR interviewer conducting a real job interview.

Candidate Profile:
- Name: {name}
- Applying for: {role}
- Education: {education}
- Experience: {experience}
- Skills: {', '.join(skills) if skills else 'Not specified'}

Your task: Generate exactly {question_count} high-quality, realistic interview questions for this candidate.

Question Guidelines:
1. Mix question types across these categories proportionally:
   - Technical/skill-based questions (test specific knowledge for the role)
   - Behavioral questions using STAR format (e.g. "Tell me about a time when...")
   - Situational questions (e.g. "What would you do if...")
   - Role-specific scenario questions
   - One culture fit / motivation question

2. Make questions:
   - Specific to the "{role}" role — not generic
   - Progressively challenging (start easy, get harder)
   - Tailored to the candidate's experience level
   - Clear and concise — one question per item

3. Do NOT include:
   - Question numbers or labels
   - Explanations or context
   - Duplicate or similar questions

Return ONLY a valid JSON array of {question_count} strings. Nothing else.
Example format: ["Question 1?", "Question 2?", ...]
"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,       # some creativity but not random
            max_tokens=2000,
        )

        content = response.choices[0].message.content
        print("🧠 Groq Questions Response:", content)

        questions = extract_json(content)

        if not isinstance(questions, list):
            return JsonResponse({
                "error": "Failed to parse questions from AI",
                "raw": content
            }, status=500)

        # Ensure we have the right count
        questions = [q.strip() for q in questions if isinstance(q, str) and q.strip()]

        return JsonResponse({
            "questions": questions,
            "temp_user_info": {
                "name": name,
                "role": role,
                "education": education,
                "experience": experience,
                "skills": skills
            }
        })

    except Exception as e:
        print("❌ Error in start_interview:", e)
        return JsonResponse({"error": str(e)}, status=500)


# ─────────────────────────────────────────────
#  VIEW 2 — Submit Answers (evaluate interview)
# ─────────────────────────────────────────────
@csrf_exempt
def submit_answers(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        data = json.loads(request.body)

        name      = data.get("name", "Candidate")
        role      = data.get("role", "")
        questions = data.get("questions", [])
        answers   = data.get("answers", [])

        if not questions or not answers or len(questions) != len(answers):
            return JsonResponse(
                {"error": "Questions and answers count must match"},
                status=400
            )

        # Build Q&A block
        qa_block = ""
        for i in range(len(questions)):
            answer = answers[i].strip() if answers[i] else "No answer provided"
            qa_block += f"Q{i+1}: {questions[i]}\nA{i+1}: {answer}\n\n"

        # ── IMPROVED EVALUATION PROMPT ───────────────────────────────
        prompt = f"""
You are a senior hiring manager evaluating a job interview for the role of "{role}".

Candidate: {name}

Here are all the interview questions and the candidate's answers:

{qa_block}

Evaluate the candidate thoroughly and return a JSON object with these exact keys:

1. "score" — integer from 0 to 100 based on:
   - Relevance and accuracy of answers (40%)
   - Communication clarity (20%)
   - Depth and examples provided (25%)
   - Confidence and professionalism (15%)

2. "strengths" — list of 3 to 5 specific strengths observed.
   Be specific — mention which answers were strong and why.
   Example: "Demonstrated strong understanding of React hooks in Q3"

3. "improvements" — list of 3 to 5 specific areas needing improvement.
   Be constructive and actionable.
   Example: "Answer to Q2 lacked concrete examples — use STAR method"

4. "summary" — 3 to 4 sentence overall assessment paragraph.
   Mention the role, overall performance, key strengths, and one key recommendation.

Scoring guide:
- 85-100: Exceptional — strong hire
- 70-84:  Good — recommend with minor reservations
- 50-69:  Average — needs improvement in key areas
- Below 50: Weak — significant gaps

Return ONLY raw valid JSON. No markdown, no explanation, no extra text.
Format: {{"score": 75, "strengths": [...], "improvements": [...], "summary": "..."}}
"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,       # low temp for consistent evaluation
            max_tokens=1500,
        )

        raw_content = response.choices[0].message.content
        print("🧠 AI Evaluation Response:", raw_content)

        feedback = extract_json(raw_content)

        if not feedback or not isinstance(feedback, dict):
            return JsonResponse({
                "error": "Could not parse evaluation from AI",
                "raw": raw_content
            }, status=500)

        # Validate and sanitise fields
        feedback["score"]        = int(feedback.get("score", 0))
        feedback["strengths"]    = feedback.get("strengths", [])
        feedback["improvements"] = feedback.get("improvements", [])
        feedback["summary"]      = feedback.get("summary", "")

        # Ensure lists are actually lists
        if not isinstance(feedback["strengths"], list):
            feedback["strengths"] = [str(feedback["strengths"])]
        if not isinstance(feedback["improvements"], list):
            feedback["improvements"] = [str(feedback["improvements"])]

        return JsonResponse({
            "message": "Interview evaluated successfully",
            "feedback": feedback
        })

    except Exception as e:
        print("❌ Error in submit_answers:", e)
        return JsonResponse({"error": str(e)}, status=500)


# ─────────────────────────────────────────────
#  VIEW 3 — Save Report
# ─────────────────────────────────────────────
@csrf_exempt
def save_report(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)

        name        = data.get("name")
        email       = data.get("email")
        role        = data.get("role")
        score       = data.get("score")
        summary     = data.get("summary", "")
        strengths   = data.get("strengths") or []
        improvements = data.get("improvements") or []

        # Normalise to lists
        if not isinstance(strengths, list):
            strengths = [str(strengths)]
        if not isinstance(improvements, list):
            improvements = [str(improvements)]

        if not name or not email:
            return JsonResponse({"error": "Missing required fields: name and email"}, status=400)

        report = Report(
            name=name,
            email=email,
            role=role,
            score=score,
            strengths=strengths,
            improvements=improvements,
            summary=summary
        )
        report.save()

        return JsonResponse({"message": "Report saved successfully"}, status=201)

    except Exception as e:
        print("❌ SAVE ERROR:", str(e))
        return JsonResponse({"error": str(e)}, status=500)


# ─────────────────────────────────────────────
#  VIEW 4 — Get All Reports for a user
# ─────────────────────────────────────────────
@csrf_exempt
def get_all_reports(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        email = request.GET.get("email")
        if not email:
            return JsonResponse({"error": "Email query param is required"}, status=400)

        reports = Report.objects(email=email).order_by("-created_at")
        report_list = []

        for report in reports:
            report_list.append({
                "id":           str(report.id),
                "name":         report.name,
                "role":         report.role,
                "score":        report.score,
                "strengths":    report.strengths,
                "improvements": report.improvements,
                "summary":      report.summary,
                "created_at":   report.created_at.strftime("%d-%m-%Y %H:%M:%S"),
            })

        return JsonResponse({"reports": report_list}, safe=False)

    except Exception as e:
        print("❌ Error fetching reports:", e)
        return JsonResponse({"error": str(e)}, status=500)
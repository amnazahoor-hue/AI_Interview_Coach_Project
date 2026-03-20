from flask import Flask, render_template, request, session, redirect, jsonify, make_response 
import os, json, re
from dotenv import load_dotenv
from groq import Groq
from prompts.interviewer import INTERVIEWER_PROMPT
from prompts.feedback_prompt import FEEDBACK_PROMPT
from datetime import datetime 
from weasyprint import HTML

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY is missing")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
if not client:
    raise ValueError("GROQ_API_KEY is missing")


#### Calling LLM ####
def call_llm(system_prompt, messages):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, *messages],
            temperature=0.7,
            max_tokens=500,
            timeout=30  # Add timeout
        )
        return response.choices[0].message.content
    except TimeoutError:
        print("LLM Timeout Error")
        return jsonify({
            "error": "timeout",
            "feedback": {
                "score": 0,
                "strengths": "Unable to evaluate",
                "weaknesses": "Request timed out",
                "ideal_answer": "Please try again"
            }
        })
    except Exception as e:
        error_str = str(e).lower()
        if "rate" in error_str or "limit" in error_str or "429" in error_str:
            return jsonify({
                "error": "rate_limit",
                "feedback": {
                    "score": 0,
                    "strengths": "Unable to evaluate",
                    "weaknesses": "Rate limit reached",
                    "ideal_answer": "Please wait a moment"
                }
            })
        elif "connection" in error_str or "network" in error_str:
            return jsonify({
                "error": "network",
                "feedback": {
                    "score": 0,
                    "strengths": "Unable to evaluate",
                    "weaknesses": "Network error",
                    "ideal_answer": "Check your connection"
                }
            })
        else:
            return jsonify({
                "error": "unknown",
                "feedback": {
                    "score": 0,
                    "strengths": "Unable to evaluate",
                    "weaknesses": "Technical error",
                    "ideal_answer": "Please try again"
                }
            })

#### To main page ###
@app.route('/',  methods=['GET'])
def index():
    return render_template("index.html")

### To Start the session ####
@app.route('/start', methods=['POST'])
def start():
    session['job_role'] = request.form.get('job_role')
    session['experience_level'] = request.form.get('experience_level')
    session['total_questions'] = int(request.form.get('questions'))
    session['current_question_index'] = 0
    session['conversation_history'] = []
    session['scores'] = []
    session['report_data'] = []
    session['questions_asked'] = []

    return redirect('/interview')

### Interview Page ###
@app.route('/interview', methods=['GET'])
def interview():
    if 'job_role' not in session:
        return redirect('/')

    # First question
    if session['current_question_index'] == 0:
        system_prompt = INTERVIEWER_PROMPT.format(
            job_role=session['job_role'],
            experience_level=session['experience_level'],
            questions_already_asked=session['questions_asked']
        )
        question = call_llm(system_prompt, [])
        session['conversation_history'].append({"role": "assistant", "content": question})
        session['questions_asked'].append(question)
        session['current_question_index'] = 1  # Keep this as is - first question asked

    current_question = session['conversation_history'][-1]['content']
    return render_template(
        "interview.html",
        question=current_question,
        current=session['current_question_index'],  # This shows "Question 1 of 3"
        total=session['total_questions']
    )

### Answer ###
@app.route('/answer', methods=['POST'])
def answer():
    data = request.get_json()
    user_answer = data.get("answer")

    # Get the current question
    current_question = session['questions_asked'][-1]

    # Append user's answer to conversation history
    session['conversation_history'].append({
        "role": "user",
        "content": user_answer
    })

    # Generate feedback using LLM
    feedback_prompt = FEEDBACK_PROMPT.format(
        job_role=session['job_role'],
        question=current_question,
        answer=user_answer
    )
    feedback = call_llm(feedback_prompt, session['conversation_history'])
    print("RAW LLM RESPONSE:\n", feedback)

    # Parse JSON safely
    try:
        json_match = re.search(r'\{.*\}', feedback, re.DOTALL)
        if json_match:
            feedback_json = json.loads(json_match.group())
        else:
            raise ValueError("No JSON found")
    except Exception as e:
        print("Parsing Error:", e)
        feedback_json = {
            "score": 0,
            "strengths": "Could not evaluate properly",
            "weaknesses": "Parsing error",
            "ideal_answer": "N/A"
        }

    # Ensure score is int
    feedback_json["score"] = int(feedback_json.get("score", 0))

    # Store data for report
    session['report_data'].append({
        "question": current_question,
        "score": feedback_json["score"],
        "strengths": feedback_json["strengths"],
        "weaknesses": feedback_json["weaknesses"],
        "summary": f"Good: {feedback_json['strengths']} | Improve: {feedback_json['weaknesses']}"
    })

    # Store scores
    session['scores'].append(feedback_json["score"])
    
    # IMPORTANT: Force session to be saved
    session.modified = True
    
    # DEBUG: Print the current state
    print(f"Current question index: {session['current_question_index']}")
    print(f"Total questions: {session['total_questions']}")
    print(f"Report data length: {len(session['report_data'])}")
    print(f"Scores length: {len(session['scores'])}")
    print(f"Questions asked length: {len(session['questions_asked'])}")

    # Check if this was the last question
    is_last_question = session['current_question_index'] == session['total_questions']

    if is_last_question:
        # Last question finished, show report button
        response_data = {
            "feedback": feedback_json,
            "finished": True
        }
    else:
        # Generate next question
        next_prompt = INTERVIEWER_PROMPT.format(
            job_role=session['job_role'],
            experience_level=session['experience_level'],
            questions_already_asked=session['questions_asked']
        )
        next_question = call_llm(next_prompt, session['conversation_history'])
        session['conversation_history'].append({
            "role": "assistant",
            "content": next_question
        })
        session['questions_asked'].append(next_question)
        
        # Increment the question index for the next question
        session['current_question_index'] += 1
        session.modified = True
        
        response_data = {
            "feedback": feedback_json,
            "next_question": next_question,
            "finished": False
        }
    
    # Force session to be saved before returning
    session.modified = True
    return jsonify(response_data)

### Report Page ###
@app.route('/report')
def report():
    if 'scores' not in session or len(session['scores']) == 0:
        return redirect('/')

    scores = session['scores']
    report_data = session.get('report_data', [])
    
    avg_score = round(sum(scores) / len(scores), 2)

    # Combine all strengths & weaknesses
    all_strengths = " ".join([item['strengths'] for item in report_data])
    all_weaknesses = " ".join([item['weaknesses'] for item in report_data])

    return render_template(
        "report.html",
        average=avg_score,
        report_data=report_data,
        strengths=all_strengths,
        improvements=all_weaknesses
    )



@app.route('/export-pdf')
def export_pdf():
    if 'scores' not in session or len(session['scores']) == 0:
        return redirect('/')
    
    # Get the same data as report page
    scores = session['scores']
    report_data = session.get('report_data', [])
    avg_score = round(sum(scores) / len(scores), 2)
    all_strengths = " ".join([item['strengths'] for item in report_data])
    all_weaknesses = " ".join([item['weaknesses'] for item in report_data])
    
    # Render HTML template for PDF
    html = render_template(
        "pdf_report.html",  # Create this template
        average=avg_score,
        report_data=report_data,
        strengths=all_strengths,
        improvements=all_weaknesses,
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    
    # Generate PDF
    pdf = HTML(string=html).write_pdf()
    
    # Create response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=interview_report_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response



### To reset the interview ###
@app.route('/reset')
def reset():
    session.clear()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
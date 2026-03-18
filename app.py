from flask import Flask, render_template, request, session, redirect, jsonify
import os, json
from dotenv import load_dotenv
from groq import Groq
from prompts.interviewer import INTERVIEWER_PROMPT
from prompts.feedback_prompt import FEEDBACK_PROMPT

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def call_llm(system_prompt, messages):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, *messages],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        print("LLM Error:", e)
        return "Error generating response"

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/start', methods=['POST'])
def start():
    session['job_role'] = request.form.get('job_role')
    session['experience_level'] = request.form.get('experience_level')
    session['total_questions'] = int(request.form.get('questions'))
    session['current_question_index'] = 0
    session['conversation_history'] = []
    session['scores'] = []
    session['questions_asked'] = []
    return redirect('/interview')

@app.route('/interview', methods=['GET'])
def interview():
    if 'job_role' not in session:
        return redirect('/')

    if session['current_question_index'] == 0:
        system_prompt = INTERVIEWER_PROMPT.format(
            job_role=session['job_role'],
            experience_level=session['experience_level'],
            questions_already_asked=session['questions_asked']
        )
        question = call_llm(system_prompt, [])
        session['conversation_history'].append({"role": "assistant", "content": question})
        session['questions_asked'].append(question)
        session['current_question_index'] = 1

    current_question = session['conversation_history'][-1]['content']
    return render_template(
        "interview.html",
        question=current_question,
        current=session['current_question_index'],
        total=session['total_questions']
    )

@app.route('/answer', methods=['POST'])
def answer():
    user_answer = request.form.get("answer")
    session['conversation_history'].append({"role": "user", "content": user_answer})
    current_question = session['questions_asked'][-1]

    feedback_prompt = FEEDBACK_PROMPT.format(
        job_role=session['job_role'],
        question=current_question,
        answer=user_answer
    )
    feedback = call_llm(feedback_prompt, session['conversation_history'])

    try:
        feedback_json = json.loads(feedback)
    except:
        feedback_json = {
            "score": 5,
            "strengths": "Could not evaluate properly",
            "weaknesses": "Parsing error",
            "ideal_answer": "N/A"
        }

    session['scores'].append(feedback_json["score"])

    if session['current_question_index'] < session['total_questions']:
        next_prompt = INTERVIEWER_PROMPT.format(
            job_role=session['job_role'],
            experience_level=session['experience_level'],
            questions_already_asked=session['questions_asked']
        )
        next_question = call_llm(next_prompt, session['conversation_history'])
        session['conversation_history'].append({"role": "assistant", "content": next_question})
        session['questions_asked'].append(next_question)
        session['current_question_index'] += 1
        return jsonify({"feedback": feedback_json, "next_question": next_question, "finished": False})
    else:
        return jsonify({"feedback": feedback_json, "finished": True})

@app.route('/report')
def report():
    if 'scores' not in session or len(session['scores']) == 0:
        return redirect('/')
    scores = session['scores']
    avg_score = round(sum(scores) / len(scores), 2)
    return render_template("report.html", scores=scores, average=avg_score)

@app.route('/reset')
def reset():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)
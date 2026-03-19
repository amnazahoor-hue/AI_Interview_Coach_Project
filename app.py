from flask import Flask, render_template, request, session, redirect, jsonify
import os, json, re
from dotenv import load_dotenv
from groq import Groq
from prompts.interviewer import INTERVIEWER_PROMPT
from prompts.feedback_prompt import FEEDBACK_PROMPT

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY is missing")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
if not client:
    raise ValueError("GROQ_API_KEY is missing")


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
    session['report_data'] = []
    session['questions_asked'] = []

    return redirect('/interview')


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
# @app.route('/answer', methods=['POST'])
# def answer():
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
    print("Scores so far:", session['scores'])

    # Check if this was the last question
    # session['current_question_index'] currently equals the number of questions asked so far
    # For example, after question 1, it's 1; after question 2, it's 2; etc.
    is_last_question = session['current_question_index'] == session['total_questions']

    if is_last_question:
        # Last question finished, show report button
        return jsonify({
            "feedback": feedback_json,
            "finished": True
        })
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

        return jsonify({
            "feedback": feedback_json,
            "next_question": next_question,
            "finished": False
        })


# @app.route('/interview', methods=['GET'])
# def interview():
#     if 'job_role' not in session:
#         return redirect('/')

#     # First question
#     if session['current_question_index'] == 0:
#         system_prompt = INTERVIEWER_PROMPT.format(
#             job_role=session['job_role'],
#             experience_level=session['experience_level'],
#             questions_already_asked=session['questions_asked']
#         )
#         question = call_llm(system_prompt, [])
#         session['conversation_history'].append({"role": "assistant", "content": question})
#         session['questions_asked'].append(question)
#         session['current_question_index'] = 1  # This is the issue - setting to 1 after first question

#     current_question = session['conversation_history'][-1]['content']
#     return render_template(
#         "interview.html",
#         question=current_question,
#         current=session['current_question_index'],
#         total=session['total_questions']
#     )


# @app.route('/answer', methods=['POST'])
# def answer():
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
    print("Scores so far:", session['scores'])

    # IMPORTANT FIX: Check if this was the last question BEFORE incrementing
    is_last_question = session['current_question_index'] == session['total_questions'] - 1

    # Increment question index AFTER checking
    session['current_question_index'] += 1

    if is_last_question:
        # Last question finished, show report button
        return jsonify({
            "feedback": feedback_json,
            "finished": True
        })
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

        return jsonify({
            "feedback": feedback_json,
            "next_question": next_question,
            "finished": False
        })



# @app.route('/report')
# def report():
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

@app.route('/report')
def report():
    if 'scores' not in session or len(session['scores']) == 0:
        return redirect('/')

    scores = session['scores']
    report_data = session.get('report_data', [])
    
    # DEBUG: Print detailed information
    print("=" * 50)
    print("REPORT PAGE DEBUG")
    print(f"Scores: {scores}")
    print(f"Number of scores: {len(scores)}")
    print(f"Report data: {report_data}")
    print(f"Number of report items: {len(report_data)}")
    
    # Print each report item in detail
    for i, item in enumerate(report_data):
        print(f"Item {i + 1}:")
        print(f"  Question: {item.get('question', 'N/A')}")
        print(f"  Score: {item.get('score', 'N/A')}")
        print(f"  Strengths: {item.get('strengths', 'N/A')}")
        print(f"  Weaknesses: {item.get('weaknesses', 'N/A')}")
        print(f"  Summary: {item.get('summary', 'N/A')}")
    
    print("=" * 50)
    
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
@app.route('/reset')
def reset():
    session.clear()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
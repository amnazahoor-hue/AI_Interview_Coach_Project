document.addEventListener("DOMContentLoaded", function () {

const submitBtn = document.getElementById('submitBtn');
const nextBtn = document.getElementById('nextBtn');
const reportBtn = document.getElementById('reportBtn');
const textarea = document.getElementById('answerBox');
const spinner = document.getElementById('spinner');
const feedbackBox = document.getElementById('feedbackBox');
const questionEl = document.getElementById('question');
const progressEl = document.getElementById('progress');

// Feedback fields
const scoreEl = document.getElementById('score');
const strengthsEl = document.getElementById('strengths');
const weaknessesEl = document.getElementById('weaknesses');
const idealEl = document.getElementById('ideal_answer');

// ✅ SAFE checks
if (!submitBtn || !textarea || !spinner) {
    console.error("Some elements not found");
    return;
}

// Safe values
const totalQuestions = progressEl && progressEl.dataset.total 
    ? parseInt(progressEl.dataset.total) 
    : 0;

let currentQuestionNumber = progressEl 
    ? parseInt(progressEl.textContent.split(' ')[1]) || 1 
    : 1;

let lastResponse = null;

// Submit Answer
submitBtn.addEventListener('click', () => {
    console.log("Button clicked ✅"); // DEBUG

    const answer = textarea.value.trim();
    if (!answer) return alert("Please type an answer.");

    textarea.disabled = true;
    submitBtn.disabled = true;
    spinner.style.display = 'inline-block';

    if (nextBtn) nextBtn.style.display = 'none';
    if (reportBtn) reportBtn.style.display = 'none';

    fetch("/answer", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ answer })
    })
    .then(res => res.json())
    .then(data => {
        spinner.style.display = 'none';
        textarea.disabled = false;
        submitBtn.disabled = false;

        lastResponse = data;

        // Fill feedback safely
        if (scoreEl) scoreEl.textContent = data.feedback.score;
        if (strengthsEl) strengthsEl.textContent = data.feedback.strengths;
        if (weaknessesEl) weaknessesEl.textContent = data.feedback.weaknesses;
        if (idealEl) idealEl.textContent = data.feedback.ideal_answer;

        if (feedbackBox) feedbackBox.style.display = 'block';

        if (!data.finished) {
            if (nextBtn) nextBtn.style.display = 'inline-block';
        } else {
            if (reportBtn) reportBtn.style.display = 'inline-block';
            submitBtn.style.display = 'none';
            textarea.disabled = true;
        }
    })
    .catch(err => {
        spinner.style.display = 'none';
        textarea.disabled = false;
        submitBtn.disabled = false;
        console.error(err);
        alert("Error submitting answer.");
    });
});

// Next Question
if (nextBtn) {
    nextBtn.addEventListener('click', () => {
        if (!lastResponse || !lastResponse.next_question) return;

        questionEl.textContent = lastResponse.next_question;
        textarea.value = '';

        if (feedbackBox) feedbackBox.style.display = 'none';
        nextBtn.style.display = 'none';

        currentQuestionNumber += 1;
        if (progressEl) {
            progressEl.textContent = `Question ${currentQuestionNumber} of ${totalQuestions}`;
        }
    });
}

});
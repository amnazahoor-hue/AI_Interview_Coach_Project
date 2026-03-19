// Function used to load page after html pages are loaded  //
document.addEventListener("DOMContentLoaded", function () {
    // These are all used to getting HTML elements //
    const submitBtn = document.getElementById('submitBtn');
    const nextBtn = document.getElementById('nextBtn');
    const reportBtn = document.getElementById('reportBtn');
    const textarea = document.getElementById('answerBox');
    const spinner = document.getElementById('spinner');
    const feedbackBox = document.getElementById('feedbackBox');
    const questionEl = document.getElementById('question'); 
    const progressEl = document.getElementById('progress');

    // These are used to display AI feedbacks //
    const scoreEl = document.getElementById('score');
    const strengthsEl = document.getElementById('strengths');
    const weaknessesEl = document.getElementById('weaknesses');
    const idealEl = document.getElementById('ideal_answer');
    // If any important element is missing it will stop //
    if (!submitBtn || !textarea || !spinner) {
        console.error("Required elements missing");
        return;
    }

    // Initial setup- Initially it will not display everything //
    spinner.style.display = "none";
    if (feedbackBox) feedbackBox.style.display = "none";
    if (nextBtn) nextBtn.style.display = "none";
    if (reportBtn) reportBtn.style.display = "none";
    // Read total questions from HTML Question 1 of 5 //
    const totalQuestions = progressEl?.dataset.total
        ? parseInt(progressEl.dataset.total)
        : 0;
    // Extract current question number from text //
    let currentQuestionNumber = progressEl
        ? parseInt(progressEl.textContent.split(' ')[1]) || 1
        : 1;
    // Storing Last response //
    let lastResponse = null;

   
    // SUBMIT ANSWER- when Submit button click it will run //
    submitBtn.addEventListener('click', () => {
        // Get text from answer and remove spaces //
        const answer = textarea.value.trim();
        // Validation for user to write answer //
        if (!answer) {
            alert("Please type an answer.");
            return;
        }
        // Disable submit button and text box and  Show Spinner
        textarea.disabled = true;
        submitBtn.disabled = true;
        spinner.style.display = "inline-block";
        // Reset screen before new response //
        if (nextBtn) nextBtn.style.display = "none";
        if (reportBtn) reportBtn.style.display = "none";
        if (feedbackBox) feedbackBox.style.display = "none";
        // Now send data to backend //
        fetch("/answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answer })
        })
        // Convert that response into JSON //
        .then(res => res.json())
        .then(data => {

            // Again enable submit button and text-area //
            spinner.style.display = "none";
            textarea.disabled = false;
            submitBtn.disabled = false;
            // Used to procedd to next question //
            lastResponse = data;

           
            // It is now showing feedback , if exists it will show then moving backward//
        
            if (scoreEl) scoreEl.textContent = data.feedback?.score || "N/A";
            if (strengthsEl) strengthsEl.textContent = data.feedback?.strengths || "";
            if (weaknessesEl) weaknessesEl.textContent = data.feedback?.weaknesses || "";
            if (idealEl) idealEl.textContent = data.feedback?.ideal_answer || "";
            // Show feedback box //
            if (feedbackBox) feedbackBox.style.display = "block";

            // Next button logic- If questions completed 
            //it will finish otherwise procedd to next question
          
            if (!data.finished) {
                if (nextBtn) nextBtn.style.display = "inline-block";
            } else {
                if (reportBtn) reportBtn.style.display = "inline-block";
                submitBtn.style.display = "none";
                textarea.disabled = true;
            }

        })
        // If LLm will fail then it will enable input again //
        .catch(err => {
            spinner.style.display = "none";
            textarea.disabled = false;
            submitBtn.disabled = false;

        });
    });
    // Click on next button to proceed next question //
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {

            if (!lastResponse || !lastResponse.next_question) return;

            // Update question
            questionEl.textContent = lastResponse.next_question;

            // text area and submit button will enable again //
            textarea.value = '';
            textarea.disabled = false;
            submitBtn.disabled = false;
            // Hide previous feedbacks //
            if (feedbackBox) feedbackBox.style.display = "none";
            nextBtn.style.display = "none";

            // Update progress
            currentQuestionNumber += 1;
            if (progressEl) {
                progressEl.textContent =
                    // this will used to show total question out of current //
                    `Question ${currentQuestionNumber} of ${totalQuestions}`;
            }
        });
    }

});
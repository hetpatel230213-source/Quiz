
from flask import Flask, request, jsonify, render_template_string
import sqlite3
import random

app = Flask(__name__)

# ---------------- DATABASE ----------------

def connect():
    return sqlite3.connect("quizmaster.db")


def init_db():
    con = connect()

    con.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            difficulty TEXT,
            question TEXT,
            option1 TEXT,
            option2 TEXT,
            option3 TEXT,
            option4 TEXT,
            answer INTEGER,
            explanation TEXT
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            subject TEXT,
            score INTEGER,
            total INTEGER,
            percentage REAL,
            xp INTEGER
        )
    """)

    con.commit()
    con.close()


init_db()


# ---------------- ADD QUESTION ----------------

@app.route("/add", methods=["POST"])
def add_question():

    data = request.get_json()

    subject = data.get("subject", "").strip()
    difficulty = data.get("difficulty", "").strip()
    question = data.get("question", "").strip()
    options = data.get("options", [])
    answer = data.get("answer")
    explanation = data.get("explanation", "").strip()

    subjects = [
        "Python", "Java", "HTML", "CSS",
        "JavaScript", "Science", "Mathematics"
    ]

    if subject not in subjects:
        return jsonify({"error": "Invalid subject"}), 400

    if difficulty not in ["Easy", "Medium", "Hard"]:
        return jsonify({"error": "Invalid difficulty"}), 400

    if not question or len(options) != 4 or not all(
        isinstance(x, str) and x.strip() for x in options
    ):
        return jsonify({"error": "Enter a question and four options"}), 400

    if not isinstance(answer, int) or answer not in range(4):
        return jsonify({"error": "Invalid correct answer"}), 400

    con = connect()

    con.execute("""
        INSERT INTO questions
        (subject, difficulty, question, option1,
         option2, option3, option4, answer, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        subject, difficulty, question,
        options[0], options[1], options[2], options[3],
        answer, explanation
    ))

    con.commit()
    con.close()

    return jsonify({"message": "Question added successfully!"})


# ---------------- GET QUESTION COUNT ----------------

@app.route("/count")
def question_count():

    con = connect()

    rows = con.execute("""
        SELECT subject, COUNT(*)
        FROM questions
        GROUP BY subject
    """).fetchall()

    con.close()

    return jsonify({row[0]: row[1] for row in rows})


# ---------------- GENERATE QUIZ ----------------

@app.route("/quiz", methods=["POST"])
def generate_quiz():

    data = request.get_json()

    subject = data.get("subject")
    difficulty = data.get("difficulty")
    count = data.get("count", 10)

    if subject not in [
        "Python", "Java", "HTML", "CSS",
        "JavaScript", "Science", "Mathematics"
    ]:
        return jsonify({"error": "Invalid subject"}), 400

    if difficulty not in ["Easy", "Medium", "Hard"]:
        return jsonify({"error": "Invalid difficulty"}), 400

    try:
        count = int(count)
        if not 1 <= count <= 1000:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Enter a valid question count"}), 400

    con = connect()

    rows = con.execute("""
        SELECT id, question, option1, option2,
        option3, option4, answer, explanation
        FROM questions
        WHERE subject = ? AND difficulty = ?
    """, (subject, difficulty)).fetchall()

    con.close()

    if not rows:
        return jsonify({
            "error": "No questions available. Add questions first!"
        }), 400

    selected = random.sample(rows, min(count, len(rows)))

    questions = []

    for row in selected:

        questions.append({
            "id": row[0],
            "question": row[1],
            "options": list(row[2:6]),
            "answer": row[6],
            "explanation": row[7]
        })

    return jsonify({"questions": questions})


# ---------------- SAVE RESULT ----------------

@app.route("/save", methods=["POST"])
def save_result():

    data = request.get_json()

    name = str(data.get("name", "Player")).strip()[:30]
    subject = data.get("subject", "")
    score = data.get("score")
    total = data.get("total")

    if not name:
        name = "Player"

    if subject not in [
        "Python", "Java", "HTML", "CSS",
        "JavaScript", "Science", "Mathematics"
    ]:
        return jsonify({"error": "Invalid subject"}), 400

    try:
        score = int(score)
        total = int(total)
        if total < 1 or score < 0 or score > total:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid result"}), 400

    percentage = round((score / total) * 100, 2)
    xp = score * 10

    con = connect()

    con.execute("""
        INSERT INTO scores
        (name, subject, score, total, percentage, xp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, subject, score, total, percentage, xp))

    con.commit()
    con.close()

    return jsonify({
        "score": score,
        "total": total,
        "percentage": percentage,
        "xp": xp
    })


# ---------------- PERFORMANCE HISTORY ----------------

@app.route("/history")
def history():

    con = connect()

    rows = con.execute("""
        SELECT name, subject, score, total, percentage, xp
        FROM scores
        ORDER BY id DESC
        LIMIT 20
    """).fetchall()

    con.close()

    return jsonify([
        {
            "name": r[0],
            "subject": r[1],
            "score": r[2],
            "total": r[3],
            "percentage": r[4],
            "xp": r[5]
        }
        for r in rows
    ])


# ---------------- LEADERBOARD ----------------

@app.route("/leaderboard")
def leaderboard():

    con = connect()

    rows = con.execute("""
        SELECT name, SUM(xp)
        FROM scores
        GROUP BY name
        ORDER BY SUM(xp) DESC
        LIMIT 10
    """).fetchall()

    con.close()

    return jsonify([
        {"name": r[0], "xp": r[1]}
        for r in rows
    ])


# ---------------- FRONTEND ----------------

HTML = r"""
<!DOCTYPE html>
<html>
<head>

<title>QuizMaster AI</title>

<meta name="viewport" content="width=device-width, initial-scale=1">

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 25px;
    background: #101426;
    color: white;
    font-family: Arial, sans-serif;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 30px;
}

.logo {
    font-size: 28px;
    color: #a78bfa;
    font-weight: bold;
}

.xp {
    background: #252b43;
    padding: 13px 20px;
    border-radius: 12px;
    color: #facc15;
}

.container {
    max-width: 1000px;
    margin: auto;
}

.hero {
    padding: 35px;
    background: linear-gradient(120deg, #6439c8, #2563eb);
    border-radius: 20px;
    margin-bottom: 25px;
}

.hero h1 {
    font-size: 32px;
}

.panel {
    background: #1b2238;
    padding: 25px;
    border-radius: 18px;
    margin-bottom: 25px;
}

h2 {
    color: #c4b5fd;
}

label {
    display: block;
    margin: 15px 0 8px;
}

input, select {
    width: 100%;
    padding: 13px;
    border: 1px solid #414969;
    background: #101426;
    color: white;
    border-radius: 9px;
    margin-bottom: 8px;
}

button {
    padding: 13px 20px;
    border: none;
    border-radius: 9px;
    background: #8b5cf6;
    color: white;
    cursor: pointer;
    margin-top: 15px;
}

button:hover {
    background: #7041d5;
}

.secondary {
    background: #34415f;
}

.hidden {
    display: none;
}

.question {
    background: #252e49;
    padding: 20px;
    margin: 15px 0;
    border-radius: 12px;
}

.option {
    padding: 12px;
    background: #343e5d;
    border-radius: 8px;
    margin: 8px 0;
    cursor: pointer;
}

.option input {
    width: auto;
}

.correct {
    color: #4ade80;
}

.wrong {
    color: #fb7185;
}

.stat {
    padding: 20px;
    background: #252e49;
    margin: 12px 0;
    border-radius: 12px;
}

.bar {
    height: 15px;
    background: #374151;
    border-radius: 20px;
    overflow: hidden;
}

.fill {
    height: 100%;
    background: #a78bfa;
    width: 0%;
}

table {
    width: 100%;
    border-collapse: collapse;
}

td, th {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #414969;
}

.scroll {
    overflow-x: auto;
}

footer {
    text-align: center;
    color: #8b91a8;
    padding: 25px;
}

</style>
</head>

<body>

<header>
    <div class="logo">⚡ QuizMaster AI</div>
    <div class="xp">⭐ Total XP: <span id="xp">0</span></div>
</header>

<div class="container">

<section class="hero">
    <h1>Level Up Your Knowledge! 🚀</h1>
    <p>Learn more. Play more. Achieve more.</p>
</section>

<!-- ADD QUESTIONS -->

<section class="panel">

<h2>➕ Add Your Own Questions</h2>

<label>Subject</label>
<select id="addSubject"></select>

<label>Difficulty</label>
<select id="addDifficulty">
    <option>Easy</option>
    <option>Medium</option>
    <option>Hard</option>
</select>

<label>Enter Question</label>
<input id="newQuestion" placeholder="Write your question">

<label>Option 1</label>
<input id="op1">

<label>Option 2</label>
<input id="op2">

<label>Option 3</label>
<input id="op3">

<label>Option 4</label>
<input id="op4">

<label>Correct Answer</label>
<select id="correct">
    <option value="0">Option 1</option>
    <option value="1">Option 2</option>
    <option value="2">Option 3</option>
    <option value="3">Option 4</option>
</select>

<label>Explanation</label>
<input id="explanation" placeholder="Explain the correct answer">

<button onclick="addQuestion()">Save Question 💾</button>

<p id="addMessage"></p>

</section>


<!-- QUIZ GENERATOR -->

<section class="panel">

<h2>🎯 Generate Your Quiz</h2>

<label>Your Name</label>
<input id="player" placeholder="Enter your name">

<label>Subject</label>
<select id="subject"></select>

<label>Difficulty</label>
<select id="difficulty">
    <option>Easy</option>
    <option>Medium</option>
    <option>Hard</option>
</select>

<label>Number of Questions</label>
<input id="count" type="number" min="1" value="5">

<button onclick="startQuiz()">Start Quiz 🚀</button>

<p id="questionCount"></p>

</section>


<!-- QUIZ AREA -->

<section class="panel hidden" id="quizArea">

<h2>🧠 Answer the Questions</h2>

<div id="questions"></div>

<button onclick="submitQuiz()">Submit Quiz 🏆</button>

</section>


<!-- RESULT -->

<section class="panel hidden" id="result">

<h2>🏆 Your Performance Report</h2>

<div class="stat" id="score"></div>
<div class="stat" id="percentage"></div>
<div class="stat" id="performance"></div>
<div class="stat" id="earnedXP"></div>

<h3>📊 Accuracy</h3>

<div class="bar">
    <div class="fill" id="fill"></div>
</div>

<h3>📝 Answer Review</h3>
<div id="review"></div>

<button onclick="restart()">Try Another Quiz 🔄</button>

</section>


<!-- HISTORY -->

<section class="panel">

<h2>📈 Performance History</h2>

<div class="scroll">
<table>
<thead>
<tr>
<th>Name</th>
<th>Subject</th>
<th>Score</th>
<th>Percentage</th>
</tr>
</thead>

<tbody id="history"></tbody>
</table>
</div>

</section>


<!-- LEADERBOARD -->

<section class="panel">

<h2>🥇 Leaderboard</h2>

<ol id="leaderboard"></ol>

</section>

</div>

<footer>
QuizMaster AI | Learn • Play • Improve
</footer>


<script>

const subjects = [
    "Python", "Java", "HTML", "CSS",
    "JavaScript", "Science", "Mathematics"
];

let quiz = [];
let xp = 0;
let submitted = false;

// Fill subject lists

function setupSubjects() {

    let options = subjects.map(s =>
        `<option value="${s}">${s}</option>`
    ).join("");

    document.getElementById("subject").innerHTML = options;
    document.getElementById("addSubject").innerHTML = options;

}

setupSubjects();


// ADD QUESTION

async function addQuestion() {

    const options = [
        document.getElementById("op1").value.trim(),
        document.getElementById("op2").value.trim(),
        document.getElementById("op3").value.trim(),
        document.getElementById("op4").value.trim()
    ];

    const question = document.getElementById("newQuestion").value.trim();

    if (!question || options.some(x => !x)) {
        alert("Please fill in the question and all four options!");
        return;
    }

    const data = {
        subject: document.getElementById("addSubject").value,
        difficulty: document.getElementById("addDifficulty").value,
        question: question,
        options: options,
        answer: Number(document.getElementById("correct").value),
        explanation: document.getElementById("explanation").value.trim()
    };

    const response = await fetch("/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });

    const result = await response.json();

    if (!response.ok) {
        alert(result.error);
        return;
    }

    document.getElementById("addMessage").innerText =
        "✅ Question saved successfully!";

    document.getElementById("newQuestion").value = "";
    ["op1", "op2", "op3", "op4", "explanation"].forEach(id => {
        document.getElementById(id).value = "";
    });

    loadCounts();
}


// QUESTION COUNTS

async function loadCounts() {

    const response = await fetch("/count");
    const data = await response.json();

    document.getElementById("questionCount").innerText =
        "Available questions: " +
        subjects.map(s => s + ": " + (data[s] || 0)).join(" | ");

}

loadCounts();


// START QUIZ

async function startQuiz() {

    const count = Number(document.getElementById("count").value);

    if (!Number.isInteger(count) || count < 1 || count > 1000) {
        alert("Enter a question count between 1 and 1000.");
        return;
    }

    const response = await fetch("/quiz", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            subject: document.getElementById("subject").value,
            difficulty: document.getElementById("difficulty").value,
            count: count
        })
    });

    const data = await response.json();

    if (!response.ok) {
        alert(data.error);
        return;
    }

    quiz = data.questions;
    submitted = false;

    let html = "";

    quiz.forEach((q, index) => {

        html += `
        <div class="question">

        <h3>${index + 1}. ${escapeHTML(q.question)}</h3>
        `;

        q.options.forEach((option, i) => {

            html += `
            <label class="option">
            <input type="radio" name="q${index}" value="${i}">
            ${escapeHTML(option)}
            </label>
            `;

        });

        html += "</div>";

    });

    document.getElementById("questions").innerHTML = html;

    document.getElementById("quizArea").classList.remove("hidden");
    document.getElementById("result").classList.add("hidden");

    document.getElementById("quizArea").scrollIntoView({
        behavior: "smooth"
    });

}


// SAFE HTML TEXT

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, c => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[c]);
}


// SUBMIT QUIZ

async function submitQuiz() {

    if (submitted) return;

    submitted = true;

    let score = 0;
    let review = "";

    quiz.forEach((q, index) => {

        const selected = document.querySelector(
            `input[name="q${index}"]:checked`
        );

        const answer = selected ? Number(selected.value) : -1;

        const correct = answer === q.answer;

        if (correct) score++;

        review += `
        <div class="stat">

        <h3>${index + 1}. ${escapeHTML(q.question)}</h3>

        <p class="${correct ? "correct" : "wrong"}">
        ${correct ? "✅ Correct" : "❌ Incorrect"}
        </p>

        <p>Your answer: ${
            answer === -1 ? "Not answered" : escapeHTML(q.options[answer])
        }</p>

        <p>Correct answer: ${escapeHTML(q.options[q.answer])}</p>

        <p>Explanation: ${escapeHTML(q.explanation || "No explanation provided.")}</p>

        </div>
        `;

    });

    const total = quiz.length;
    const percentage = (score / total) * 100;

    let performance;

    if (percentage === 100) {
        performance = "🏆 Outstanding! Perfect score!";
    } else if (percentage >= 80) {
        performance = "🥇 Excellent performance!";
    } else if (percentage >= 60) {
        performance = "🥈 Good job! Keep improving!";
    } else if (percentage >= 40) {
        performance = "🌱 Keep practising!";
    } else {
        performance = "💪 Don't give up! Try again!";
    }

    const response = await fetch("/save", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            name: document.getElementById("player").value || "Player",
            subject: document.getElementById("subject").value,
            score: score,
            total: total
        })
    });

    const data = await response.json();

    if (!response.ok) {
        submitted = false;
        alert(data.error || "Could not save your score.");
        return;
    }

    xp += data.xp;

    document.getElementById("xp").innerText = xp;

    document.getElementById("score").innerHTML =
        `🎯 Score: ${score} / ${total}`;

    document.getElementById("percentage").innerHTML =
        `📊 Percentage: ${data.percentage}%`;

    document.getElementById("performance").innerHTML = performance;

    document.getElementById("earnedXP").innerHTML =
        `⭐ XP Earned: ${data.xp}`;

    document.getElementById("fill").style.width =
        data.percentage + "%";

    document.getElementById("review").innerHTML = review;

    document.getElementById("quizArea").classList.add("hidden");
    document.getElementById("result").classList.remove("hidden");

    document.getElementById("result").scrollIntoView({
        behavior: "smooth"
    });

    loadHistory();
    loadLeaderboard();

}


// PERFORMANCE HISTORY

async function loadHistory() {

    const response = await fetch("/history");
    const data = await response.json();

    document.getElementById("history").innerHTML =
        data.map(x => `
        <tr>
        <td>${escapeHTML(x.name)}</td>
        <td>${escapeHTML(x.subject)}</td>
        <td>${x.score}/${x.total}</td>
        <td>${x.percentage}%</td>
        </tr>
        `).join("") || "<tr><td colspan='4'>No history yet.</td></tr>";

}


// LEADERBOARD

async function loadLeaderboard() {

    const response = await fetch("/leaderboard");
    const data = await response.json();

    document.getElementById("leaderboard").innerHTML =
        data.map(x =>
            `<li>${escapeHTML(x.name)} — ${x.xp} XP</li>`
        ).join("") || "<li>No players yet.</li>";

}


function restart() {

    document.getElementById("result").classList.add("hidden");
    document.getElementById("quizArea").classList.add("hidden");

    document.getElementById("count").value = 5;

    document.getElementById("setup")?.scrollIntoView({
        behavior: "smooth"
    });

}

loadHistory();
loadLeaderboard();

</script>

</body>
</html>
"""


# ---------------- HOME PAGE ----------------

@app.route("/")
def home():
    return render_template_string(HTML)


# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)

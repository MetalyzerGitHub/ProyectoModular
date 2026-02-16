let currentUser = null;
let users = [];

let currentQuestion = 0;

const questions = [
{
    word: "Dog",
    options: ["Perro", "Gato", "Casa"],
    correct: "Perro"
},
{
    word: "House",
    options: ["Mesa", "Casa", "Carro"],
    correct: "Casa"
}
];

/* ---------- OCULTAR TODO ---------- */

function hideAll(){
    document.getElementById("welcomeSection").style.display = "none";
    document.getElementById("login").style.display = "none";
    document.getElementById("register").style.display = "none";
    document.getElementById("dashboard").style.display = "none";
    document.getElementById("quiz").style.display = "none";
}

/* ---------- MOSTRAR SECCIONES ---------- */

function showLogin(){
    hideAll();
    document.getElementById("login").style.display = "block";
}

function showRegister(){
    hideAll();
    document.getElementById("register").style.display = "block";
}

function goHome(){
    hideAll();
    document.getElementById("welcomeSection").style.display = "flex";
    toggleSidebar();
}

function openActivities(){
    if(!currentUser){
        alert("Debes iniciar sesión primero");
        return;
    }
    hideAll();
    document.getElementById("quiz").style.display = "block";
    toggleSidebar();
}

/* ---------- REGISTRO ---------- */

function register(){
    const newUser = document.getElementById("registerUser").value;
    const newPass = document.getElementById("registerPass").value;

    if(newUser === "" || newPass === ""){
        alert("Completa todos los campos");
        return;
    }

    const userExists = users.find(u => u.username === newUser);

    if(userExists){
        alert("El usuario ya existe");
        return;
    }

    users.push({
        username: newUser,
        password: newPass
    });

    alert("Cuenta creada correctamente");
    showLogin();
}

/* ---------- LOGIN ---------- */

function login(){
    const user = document.getElementById("loginUser").value;
    const pass = document.getElementById("loginPass").value;

    const foundUser = users.find(
        u => u.username === user && u.password === pass
    );

    if(foundUser){
        currentUser = user;
        updateNavbar();
        hideAll();
        document.getElementById("dashboard").style.display = "block";
        document.getElementById("welcome").innerText =
            "Bienvenido, " + currentUser;
    }else{
        alert("Usuario o contraseña incorrectos");
    }
}

/* ---------- NAVBAR ---------- */

function updateNavbar(){
    const authDiv = document.getElementById("authButtons");

    authDiv.innerHTML = `
        <span>Hola, ${currentUser}</span>
        <button onclick="logout()">Cerrar Sesión</button>
    `;
}

function logout(){
    currentUser = null;

    document.getElementById("authButtons").innerHTML = `
        <button onclick="showLogin()">Iniciar Sesión</button>
        <button onclick="showRegister()">Crear Cuenta</button>
    `;

    goHome();
}

/* ---------- QUIZ ---------- */

function startQuiz(){
    hideAll();
    document.getElementById("quiz").style.display = "block";
    currentQuestion = 0;
    loadQuestion();
}

function loadQuestion(){
    let q = questions[currentQuestion];

    document.getElementById("question").innerText =
        "Selecciona la traducción de: " + q.word;

    let optionsHTML = "";

    q.options.forEach(opt => {
        optionsHTML +=
        `<button onclick="checkAnswer('${opt}')">${opt}</button><br>`;
    });

    document.getElementById("options").innerHTML = optionsHTML;
    document.getElementById("result").innerText = "";
}

function checkAnswer(answer){
    let q = questions[currentQuestion];

    if(answer === q.correct){
        document.getElementById("result").innerText = "Correcto";
    }else{
        document.getElementById("result").innerText = "Incorrecto";
    }
}

function nextQuestion(){
    currentQuestion++;

    if(currentQuestion >= questions.length){
        alert("Actividad terminada");
        hideAll();
        document.getElementById("dashboard").style.display = "block";
        return;
    }

    loadQuestion();
}

/* ---------- SIDEBAR ---------- */

function toggleSidebar(){
    document.getElementById("sidebar").classList.toggle("active");
}

/* ---------- INICIO AUTOMÁTICO ---------- */

window.onload = function() {
    hideAll();
    document.getElementById("welcomeSection").style.display = "flex";
};

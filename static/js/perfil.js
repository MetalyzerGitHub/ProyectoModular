document.addEventListener("DOMContentLoaded", function () {
    const viewContent = document.getElementById("profile-view-content");
    const viewActions = document.getElementById("view-actions");
    const editForm    = document.getElementById("edit-form");
    const btnEditar   = document.getElementById("btn-editar");
    const btnCancelar = document.getElementById("btn-cancelar");

    function showEditMode() {
        viewContent.style.display = "none";
        viewActions.style.display = "none";
        editForm.style.display    = "block";
    }

    function showViewMode() {
        viewContent.style.display = "";
        viewActions.style.display = "";
        editForm.style.display    = "none";

        // Limpiar campos al cancelar
        editForm.querySelectorAll("input").forEach(function (inp) {
            inp.value = "";
        });
    }

    if (btnEditar)   btnEditar.addEventListener("click", showEditMode);
    if (btnCancelar) btnCancelar.addEventListener("click", showViewMode);
});

(function() {
    // Opcional: animación suave al cargar
    window.addEventListener('load', function() {
        const perfilCard = document.querySelector('.perfil-glass-card');
        if (perfilCard) {
            perfilCard.style.opacity = '0';
            perfilCard.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                perfilCard.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                perfilCard.style.opacity = '1';
                perfilCard.style.transform = 'translateY(0)';
            }, 100);
        }
    });
})();
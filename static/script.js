document.addEventListener("DOMContentLoaded", function () {
    const moodForm = document.querySelector("form");
    const cancelButton = document.getElementById("cancel-button");
    const cancelModal = document.getElementById("cancel-modal");
    const keepEditingButton = document.getElementById(
        "keep-editing-button"
    );
    const noteBox = document.querySelector('textarea[name="note"]');

    /*
    check whether the user has selected a mood or typed a note
    */
    function entryHasContent() {
        const selectedMood = document.querySelector(
            'input[name="mood"]:checked'
        );

        const noteHasText =
            noteBox && noteBox.value.trim() !== "";

        return selectedMood !== null || noteHasText;
    }

    /*
    show the cancel popup
    */
    function showCancelModal() {
        if (!cancelModal) {
            return;
        }

        cancelModal.classList.remove("hidden");

        if (keepEditingButton) {
            keepEditingButton.focus();
        }
    }

    /*
    hide the cancel popup
    */
    function hideCancelModal() {
        if (!cancelModal) {
            return;
        }

        cancelModal.classList.add("hidden");

        if (cancelButton) {
            cancelButton.focus();
        }
    }

    /*
    user cancels
    */
    if (cancelButton) {
        cancelButton.addEventListener("click", function () {
            if (entryHasContent()) {
                showCancelModal();
            } else {
                window.location.href = "/";
            }
        });
    }

    /*
    return to mood entry
    */
    if (keepEditingButton) {
        keepEditingButton.addEventListener("click", function () {
            hideCancelModal();
        });
    }

    /*
    non-yes or no choice: click off popup
    */
    if (cancelModal) {
        cancelModal.addEventListener("click", function (event) {
            if (event.target === cancelModal) {
                hideCancelModal();
            }
        });
    }

    /*
    non-yes or no choice: esc pressed
    */
    document.addEventListener("keydown", function (event) {
        if (
            event.key === "Escape" &&
            cancelModal &&
            !cancelModal.classList.contains("hidden")
        ) {
            hideCancelModal();
        }
    });

    /*
    prevents empty submission
    */
    if (moodForm) {
        moodForm.addEventListener("submit", function (event) {
            const selectedMood = document.querySelector(
                'input[name="mood"]:checked'
            );

            if (!selectedMood) {
                event.preventDefault();
                alert("Please select a mood before saving.");
            }
        });
    }
});
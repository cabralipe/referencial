(function () {
    "use strict";

    function insertAtCursor(field, value) {
        var start = typeof field.selectionStart === "number" ? field.selectionStart : field.value.length;
        var end = typeof field.selectionEnd === "number" ? field.selectionEnd : start;
        field.value = field.value.slice(0, start) + value + field.value.slice(end);
        var nextPosition = start + value.length;
        field.focus();
        field.setSelectionRange(nextPosition, nextPosition);
        field.dispatchEvent(new Event("input", { bubbles: true }));
        field.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function installPicker(field) {
        if (field.dataset.certificatePickerReady === "1") {
            return;
        }

        var choices;
        try {
            choices = JSON.parse(field.dataset.certificateVariables || "[]");
        } catch (error) {
            return;
        }
        if (!choices.length) {
            return;
        }

        var container = document.createElement("div");
        container.className = "certificate-variable-picker";

        var select = document.createElement("select");
        select.className = "certificate-variable-select";
        select.setAttribute("aria-label", "Variavel para inserir");
        choices.forEach(function (choice) {
            var option = document.createElement("option");
            option.value = "{{" + choice[0] + "}}";
            option.textContent = choice[1] + " — " + option.value;
            select.appendChild(option);
        });

        var button = document.createElement("button");
        button.type = "button";
        button.className = "button certificate-variable-button";
        button.textContent = "Inserir variavel";
        button.addEventListener("click", function () {
            insertAtCursor(field, select.value);
        });

        container.appendChild(select);
        container.appendChild(button);
        field.insertAdjacentElement("afterend", container);
        field.dataset.certificatePickerReady = "1";
    }

    function initialize() {
        document.querySelectorAll("[data-certificate-variable-picker='1']").forEach(installPicker);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
}());

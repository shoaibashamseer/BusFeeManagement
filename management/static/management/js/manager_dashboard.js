let html5QrcodeScanner = null;

function filterScannerRoster() {
    var input = document.getElementById("studentSearch");
    var filter = input.value.toLowerCase().trim();
    var table = document.getElementById("rosterTable");
    var tr = table.getElementsByTagName("tr");

    for (var i = 1; i < tr.length; i++) {
        var row = tr[i];
        if (row) {
            var textContent = row.innerText.toLowerCase();
            row.style.display = textContent.includes(filter) ? "" : "none";
        }
    }
}

// Keep track of the scanner object globally

// Renamed arguments to incomingId and incomingName to prevent naming collisions with HTML IDs
function selectStudentForMapping(studentId, studentName, currentQr) {

    // 1. Manage active styling highlights safely on rows
    var rows = document.querySelectorAll(".selectable-student-row");
    rows.forEach(r => r.classList.remove("selected-highlight"));

    var eventTargetRow = window.event.currentTarget;
    if(eventTargetRow) eventTargetRow.classList.add("selected-highlight");

    // 2. Clear old active scanner streams cleanly
    clearActiveScannerDevice();

    // 3. Open the hidden UI panels
    document.getElementById("emptyStatePrompt").style.display = "none";
    document.getElementById("mappingFormWrapper").style.display = "block";

    // 4. Map values safely using our unique incoming variable names
    // This explicitly forces the browser to write the string ID number!
    document.getElementById("selectedStudentId").value = studentId;
    document.getElementById("targetStudentName").innerText = studentName;

    var statusPill = document.getElementById("targetStudentCurrentPill");
    if(currentQr && currentQr !== "None" && currentQr !== "") {
        statusPill.innerHTML = "⚠️ Linked payload: <span class='current-card-badge has-card'>💳 " + currentQr + "</span>";
    } else {
        statusPill.innerHTML = "ℹ️ This profile is <span class='current-card-badge no-card'>Unlinked</span>";
    }

    var inputField = document.getElementById("qrCodeInput");
    inputField.value = "";

    // 5. Fire camera streams safely
    setTimeout(() => {
        initializeAutomatedScanner();
        inputField.focus();
    }, 250);
}



function initializeAutomatedScanner() {

    if (html5QrcodeScanner !== null) return;



    // Matches your working staff-side configuration exactly

    html5QrcodeScanner = new Html5QrcodeScanner(

        "reader",

        { fps: 10, qrbox: 250, rememberLastUsedCamera: true }

    );



    html5QrcodeScanner.render(

        function(decodedText, decodedResult) {

            // Write code value automatically into the input field

            document.getElementById("qrCodeInput").value = decodedText;

            if (navigator.vibrate) navigator.vibrate(100);



            // Pop a subtle green visual pulse to confirm the catch

            var entryBox = document.getElementById("qrCodeInput").parentElement;

            entryBox.style.borderColor = "#22c55e";

            setTimeout(() => { entryBox.style.borderColor = "#cbd5e1"; }, 1200);

        },

        function(error) {

            // Silence failure frames log pollution

        }

    );

}



function clearActiveScannerDevice() {

    if (html5QrcodeScanner) {

        try {

            html5QrcodeScanner.clear();

            html5QrcodeScanner = null;

        } catch (err) {

            console.warn("Handled camera detach gracefully:", err);

            html5QrcodeScanner = null;

        }

    }

    document.getElementById("reader").innerHTML = "";

}



function resetMappingWorkspace() {

    clearActiveScannerDevice();

    document.getElementById("mappingForm").reset();

    document.getElementById("mappingFormWrapper").style.display = "none";

    document.getElementById("emptyStatePrompt").style.display = "block";



    var rows = document.querySelectorAll(".selectable-student-row");

    rows.forEach(r => r.classList.remove("selected-highlight"));

}



document.addEventListener("DOMContentLoaded", function() {

    const toasts = document.querySelectorAll('.toast-card');

    toasts.forEach(toast => {

        // Automatically start fade out sequence after 4 seconds

        setTimeout(() => {

            dismissToast(toast.querySelector('.toast-close'));

        }, 4000);

    });

});



function dismissToast(buttonElement) {

    if(!buttonElement) return;

    const toastCard = buttonElement.closest('.toast-card');

    if (toastCard) {

        toastCard.style.animation = "toastFadeOut 0.25s ease forwards";

        setTimeout(() => {

            toastCard.remove();

        }, 250);

    }

}



function toggleDetailsRow(rowId) {

    var row = document.getElementById(rowId);

    if (row) {

        row.style.display = (row.style.display === "none") ? "table-row" : "none";

    }

}



// Upgraded accordion toggle to rotate the beautiful CSS arrow icon

function toggleAccordion(sectionId, headerElement) {

    var section = document.getElementById(sectionId);

    if (section) {

        if (section.style.display === "none") {

            section.style.display = "block";

            headerElement.classList.add('active');

        } else {

            section.style.display = "none";

            headerElement.classList.remove('active');

        }

    }

}

// Toggles display layout of extra parent details rows

function toggleDetailsRow(rowId) {

    var row = document.getElementById(rowId);

    if (row) {

        row.style.display = (row.style.display === "none") ? "table-row" : "none";

    }

}



// Upgraded accordion toggle to rotate the arrow icon

function toggleAccordion(sectionId, headerElement) {

    var section = document.getElementById(sectionId);

    if (section) {

        if (section.style.display === "none") {

            section.style.display = "block";

            headerElement.classList.add('active');

        } else {

            section.style.display = "none";

            headerElement.classList.remove('active');

        }

    }

}



// Option 1: Instant Hierarchy-Aware Search Filter
function filterDashboard() {
    var input = document.getElementById("dashboardSearch");
    var filter = input.value.toLowerCase().trim();

    // Get all Class Accordion blocks
    var accordionItems = document.querySelectorAll(".accordion-item");

    accordionItems.forEach(function(item) {
        var classHeader = item.querySelector(".accordion-header");
        var classBody = item.querySelector(".accordion-body");
        var busCards = item.querySelectorAll(".bus-container-card");
        var classHasMatches = false;

        // If search is empty, reset everything to original clean collapsed state
        if (filter === "") {
            classBody.style.display = "none";
            classHeader.classList.remove('active');
            busCards.forEach(card => card.style.display = "block");
            item.querySelectorAll(".student-row").forEach(row => row.style.display = "table-row");
            return;
        }

        // Loop through each bus group inside this class
        busCards.forEach(function(card) {
            var rows = card.querySelectorAll(".student-row");
            var busHasMatches = false;

            rows.forEach(function(row) {
                // Read text contents from the row columns
                var rowText = row.innerText.toLowerCase();

                if (rowText.includes(filter)) {
                    row.style.display = "table-row";
                    busHasMatches = true;
                    classHasMatches = true;
                } else {
                    row.style.display = "none";
                    // Also make sure to hide the expanded drawer if open
                    var detailsId = row.getAttribute("onclick").match(/'([^']+)'/)[1];
                    var detailsRow = document.getElementById(detailsId);
                    if (detailsRow) detailsRow.style.display = "none";
                }
            });

            // Hide or show the entire bus section based on matches
            card.style.display = busHasMatches ? "block" : "none";
        });

        // If a class contains a student that matches, automatically force open the accordion
        if (classHasMatches) {
            classBody.style.display = "block";
            classHeader.classList.add('active');
            item.style.display = "block";
        } else {
            item.style.display = "none"; // Hide the whole class accordion if no matches anywhere inside
        }
    });
}
// Toast Notification Dismiss Engine
document.addEventListener("DOMContentLoaded", function() {
    const toasts = document.querySelectorAll('.toast-card');
    toasts.forEach(toast => {
        setTimeout(() => { dismissToast(toast.querySelector('.toast-close')); }, 4000);
    });
});

function dismissToast(buttonElement) {
    if(!buttonElement) return;
    const toastCard = buttonElement.closest('.toast-card');
    if (toastCard) {
        toastCard.style.opacity = "0";
        setTimeout(() => { toastCard.remove(); }, 250);
    }
}
function toggleAccordion(targetId, buttonElement) {
    // 1. Locate the exact element by its unique ID string
    const targetTarget = document.getElementById(targetId);
    if (!targetTarget) return;

    // 2. Toggle visibility state safely
    if (targetTarget.style.display === "none" || targetTarget.style.display === "") {
        targetTarget.style.display = "block";
        if (buttonElement) buttonElement.classList.add("active");
    } else {
        targetTarget.style.display = "none";
        if (buttonElement) buttonElement.classList.remove("active");
    }

    // 3. Optional: Rotate chevron icon inside this specific button block only
    if (buttonElement) {
        const chevron = buttonElement.querySelector(".chevron-icon");
        if (chevron) {
            if (targetTarget.style.display === "block") {
                chevron.style.transform = "rotate(180deg)";
            } else {
                chevron.style.transform = "rotate(0deg)";
            }
        }
    }
}

function toggleDetailsRow(rowId) {
    // Isolated logic for inner student drawer panels
    const targetRow = document.getElementById(rowId);
    if (!targetRow) return;

    if (targetRow.style.display === "none" || targetRow.style.display === "") {
        targetRow.style.display = "table-row";
    } else {
        targetRow.style.display = "none";
    }
}
function filterReportRows() {
    // 1. Fetch the text from your input box precisely by its ID
    const searchInput = document.getElementById('reportSearch');
    if (!searchInput) return;

    const filterText = searchInput.value.toLowerCase().trim();

    // ==================================================================
    // FILTER 1: Clean Dashboard Screen Accordion Rows
    // ==================================================================
    const screenRows = document.querySelectorAll('.screen-only .selectable-student-row');
    screenRows.forEach(row => {
        const nameElement = row.querySelector('.target-student-name');
        const admElement = row.querySelector('.admission-no');

        const nameText = nameElement ? nameElement.textContent.toLowerCase() : '';
        const admText = admElement ? admElement.textContent.toLowerCase() : '';

        // If search term matches the student's name or admission number, keep it visible
        if (nameText.includes(filterText) || admText.includes(filterText)) {
            row.style.setProperty('display', 'flex', 'important');
        } else {
            row.style.setProperty('display', 'none', 'important');
        }
    });

    // ==================================================================
    // FILTER 2: Simple High-Density Print Table Rows
    // ==================================================================
    const printRows = document.querySelectorAll('.print-only-container tbody tr');
    printRows.forEach(row => {
        const textContent = row.textContent.toLowerCase();

        // If search term matches, preserve native table layout row settings
        if (textContent.includes(filterText)) {
            row.style.setProperty('display', 'table-row', 'important');
        } else {
            row.style.setProperty('display', 'none', 'important');
        }
    });
}

function toggleAccordionSection(header) {
    const contentPanel = header.nextElementSibling;
    const arrow = header.querySelector('.accordion-arrow');

    if (contentPanel.style.display === "none" || contentPanel.style.display === "") {
        contentPanel.style.display = "block";
        header.style.background = "#f1f5f9";
        if (arrow) arrow.style.transform = "rotate(90deg)";
    } else {
        contentPanel.style.display = "none";
        header.style.background = "#f8fafc";
        if (arrow) arrow.style.transform = "rotate(0deg)";
    }
}
/* ==========================================================================
   Smart Inventory Management System — Frontend behaviour
   Pure vanilla JS — safe to include with any Django template.
   ========================================================================== */

document.addEventListener("DOMContentLoaded", function () {
  initDeleteConfirm();
  initTableFilter();
  initPasswordToggle();
  initPrintBill();
  initSidebarActiveState();
});

/* Ask for explicit confirmation before any delete-product form submits,
   mirroring the console app's Y/N confirmation step. */
function initDeleteConfirm() {
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      var message = form.getAttribute("data-confirm") || "Are you sure?";
      if (!window.confirm(message)) {
        e.preventDefault();
      }
    });
  });
}

/* Instant client-side filter for the product table search box.
   Works alongside (not instead of) the server-side Search Product view. */
function initTableFilter() {
  var input = document.getElementById("liveFilter");
  var table = document.getElementById("productTable");
  if (!input || !table) return;

  input.addEventListener("input", function () {
    var query = input.value.trim().toLowerCase();
    var rows = table.querySelectorAll("tbody tr");
    var visibleCount = 0;

    rows.forEach(function (row) {
      var text = row.innerText.toLowerCase();
      var match = text.indexOf(query) !== -1;
      row.style.display = match ? "" : "none";
      if (match) visibleCount++;
    });

    var emptyState = document.getElementById("tableEmptyState");
    if (emptyState) {
      emptyState.style.display = visibleCount === 0 ? "block" : "none";
    }
  });
}

/* Show / hide password on the login and change-password screens. */
function initPasswordToggle() {
  document.querySelectorAll("[data-toggle-password]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var targetId = btn.getAttribute("data-toggle-password");
      var field = document.getElementById(targetId);
      if (!field) return;
      var isHidden = field.type === "password";
      field.type = isHidden ? "text" : "password";
      btn.textContent = isHidden ? "Hide" : "Show";
    });
  });
}

/* Print just the receipt card on the Sell Product page. */
function initPrintBill() {
  var printBtn = document.getElementById("printBillBtn");
  if (!printBtn) return;
  printBtn.addEventListener("click", function () {
    window.print();
  });
}

/* Highlight the current nav item based on the URL, as a fallback for
   pages that don't set the 'active' class via {% url %} comparison. */
function initSidebarActiveState() {
  var path = window.location.pathname;
  document.querySelectorAll(".nav-item[href]").forEach(function (link) {
    if (link.getAttribute("href") === path) {
      link.classList.add("active");
    }
  });
}

"use strict";
document.querySelectorAll("[data-copy]").forEach(function (button) {
  button.hidden = false;
  button.addEventListener("click", async function () {
    var source = document.getElementById(button.dataset.copy);
    var text = source.value === undefined ? source.textContent : source.value;
    var status = document.getElementById("copy-status");
    try {
      if (!navigator.clipboard) throw new Error("clipboard unavailable");
      await navigator.clipboard.writeText(text);
      status.textContent = "Copied. Paste into your email, attach files manually, then send. Nothing was submitted here.";
    } catch (_) {
      if (source.select) { source.focus(); source.select(); }
      status.textContent = "Automatic copy is unavailable. Select and copy the visible text, or download a template. Nothing was submitted.";
    }
  });
});

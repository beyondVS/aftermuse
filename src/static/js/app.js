document.addEventListener("htmx:responseError", () => {
  document.body.dataset.htmxError = "true";
});

document.addEventListener("htmx:beforeSwap", (event) => {
  const xhr = event.detail.xhr;
  const target = event.detail.target;
  if (
    !(target instanceof HTMLElement) ||
    target.id !== "reading-panel" ||
    xhr.status < 400 ||
    xhr.status >= 500 ||
    xhr.getResponseHeader("HX-Retarget") !== "#reading-panel" ||
    xhr.getResponseHeader("HX-Reswap") !== "outerHTML"
  ) {
    return;
  }

  event.detail.shouldSwap = true;
});

document.addEventListener("readingPanelSettled", () => {
  const panel = document.querySelector("#reading-panel");
  const focusTarget =
    panel?.querySelector("[data-reading-result]") ??
    panel?.querySelector("#reading-state-title");
  focusTarget?.focus();
});

function setReadingSubmissionBusy(event, isBusy) {
  const form = event.detail.elt;
  if (!(form instanceof HTMLFormElement) || !form.matches("[data-reading-submission]")) {
    return;
  }

  form.setAttribute("aria-busy", String(isBusy));
  form.closest("#reading-panel")?.setAttribute("aria-busy", String(isBusy));
}

document.addEventListener("htmx:beforeRequest", (event) => {
  setReadingSubmissionBusy(event, true);
});

document.addEventListener("htmx:afterRequest", (event) => {
  setReadingSubmissionBusy(event, false);
});

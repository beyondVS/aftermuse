document.addEventListener("htmx:responseError", () => {
  document.body.dataset.htmxError = "true";
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

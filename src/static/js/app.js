document.addEventListener("htmx:responseError", () => {
  document.body.dataset.htmxError = "true";
});

document.addEventListener("htmx:beforeSwap", (event) => {
  const xhr = event.detail.xhr;
  const target = event.detail.target;
  if (
    !(target instanceof HTMLElement) ||
    xhr.status < 400 ||
    xhr.getResponseHeader("HX-Retarget") !== `#${target.id}` ||
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

document.addEventListener("interviewTurnSettled", () => {
  document.querySelector("#interview-turn-region [data-interview-focus]")?.focus();
});

function setReadingSubmissionBusy(event, isBusy) {
  const form = event.detail.elt;
  if (!(form instanceof HTMLFormElement) || !form.matches("[data-reading-submission]")) {
    return;
  }

  form.setAttribute("aria-busy", String(isBusy));
  form.closest("#reading-panel")?.setAttribute("aria-busy", String(isBusy));
}

function setAnswerSubmissionBusy(event, isBusy) {
  const form = event.detail.elt;
  if (!(form instanceof HTMLFormElement) || !form.matches("[data-answer-submission]")) {
    return;
  }

  form.setAttribute("aria-busy", String(isBusy));
  const button = form.querySelector("button[type='submit']");
  if (button instanceof HTMLButtonElement) {
    button.disabled = isBusy;
  }
}

document.addEventListener("htmx:beforeRequest", (event) => {
  setReadingSubmissionBusy(event, true);
  setAnswerSubmissionBusy(event, true);
});

document.addEventListener("htmx:afterRequest", (event) => {
  setReadingSubmissionBusy(event, false);
  setAnswerSubmissionBusy(event, false);
});

document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || !form.matches("[data-answer-submission]")) {
    return;
  }

  form.setAttribute("aria-busy", "true");
  form.querySelector("button[type='submit']")?.setAttribute("disabled", "disabled");
});

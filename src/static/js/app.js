document.addEventListener("htmx:responseError", () => {
  document.body.dataset.htmxError = "true";
});

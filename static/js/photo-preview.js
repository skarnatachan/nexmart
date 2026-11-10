// Live preview for photo inputs rendered with a data-photo-preview container in the page templates.
(function () {
  document.querySelectorAll("[data-photo-preview]").forEach((container) => {
    const input = document.getElementById(container.dataset.photoPreview);
    if (!input) return;
    const img = container.querySelector("[data-photo-preview-img]");
    const placeholder = container.querySelector("[data-photo-preview-placeholder]");
    const clear = container.querySelector("[data-photo-preview-clear]");
    const status = container.querySelector("[data-photo-preview-status]");
    const savedSrc = img.dataset.savedSrc || "";
    let objectUrl = null;

    function show(src, isNew) {
      if (objectUrl && src !== objectUrl) {
        URL.revokeObjectURL(objectUrl);
        objectUrl = null;
      }
      if (src) img.src = src;
      img.hidden = !src;
      placeholder.hidden = Boolean(src);
      status.hidden = !isNew;
    }

    function render() {
      const file = input.files[0];
      // Non-images fall back to the saved photo; the server reports the error.
      if (file && file.type.startsWith("image/")) {
        // Uploading and "Remove photo" together is a form error; a new pick wins.
        if (clear) clear.checked = false;
        objectUrl = objectUrl || URL.createObjectURL(file);
        show(objectUrl, true);
      } else {
        show(clear?.checked ? "" : savedSrc, false);
      }
    }

    input.addEventListener("change", () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = null;
      render();
    });

    clear?.addEventListener("change", () => {
      // Ticking "Remove photo" drops any file picked since the page loaded.
      if (clear.checked) input.value = "";
      render();
    });

    // Browsers can restore a picked file on back/forward navigation.
    window.addEventListener("pageshow", render);
    render();
  });
})();

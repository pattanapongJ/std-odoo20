// The SCSS asset bundle on this instance intermittently fails to compile,
// so hiding this panel via CSS is unreliable. JS assets compile fine, so
// hide it (and its full-screen wrapper) directly via the DOM instead.

function hideExpirationPanel() {
    const panel = document.querySelector(".database_expiration_panel");
    if (!panel) {
        return;
    }
    panel.style.setProperty("display", "none", "important");

    // Only hide the immediate parent, and only if it's really Odoo's
    // full-screen absolute-positioned wrapper (inline style, as shipped by
    // web_enterprise) — never fall through to body or some larger container.
    const wrapper = panel.parentElement;
    if (!wrapper || wrapper === document.body || wrapper.style.position !== "absolute") {
        return;
    }
    wrapper.style.setProperty("display", "none", "important");
}

hideExpirationPanel();

// Observe <html>, not <body>: this script can run before <body> exists yet
// (assets_backend loads in <head>), and MutationObserver.observe(null, ...)
// throws — which, left uncaught at module top-level, can abort the whole
// asset bundle and blank the webclient.
const observer = new MutationObserver(hideExpirationPanel);
observer.observe(document.documentElement, { childList: true, subtree: true });

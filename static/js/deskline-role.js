/**
 * Deskline role helpers — hide CRUD UI for viewers.
 * Also used so Test opens the Drive demo video (no Retell credit burn).
 */
(function () {
  const DEMO_VIDEO_URL =
    "https://drive.google.com/file/d/1_bEuzB7uE2Hy5_4Ys7FgZBNtsLviUVrW/view?usp=drive_link";

  window.DESKLINE_DEMO_VIDEO_URL = DEMO_VIDEO_URL;
  window.DESKLINE_IS_ADMIN = true; // optimistic until profile loads

  if (!document.getElementById("deskline-role-style")) {
    const style = document.createElement("style");
    style.id = "deskline-role-style";
    style.textContent =
      "html.deskline-viewer [data-admin-only]{display:none!important;}" +
      "html.deskline-viewer [data-viewer-only]{display:revert!important;}";
    document.head.appendChild(style);
  }

  function getToken() {
    const t = localStorage.getItem("access_token") || sessionStorage.getItem("access_token") || "";
    return t && t !== "null" && t !== "undefined" && t.startsWith("eyJ") ? t : "";
  }

  function applyAdminUI(isAdmin) {
    window.DESKLINE_IS_ADMIN = !!isAdmin;
    document.documentElement.classList.toggle("deskline-viewer", !isAdmin);
    document.querySelectorAll("[data-admin-only]").forEach((el) => {
      if (isAdmin) {
        el.style.removeProperty("display");
        el.removeAttribute("aria-hidden");
      } else {
        el.style.display = "none";
        el.setAttribute("aria-hidden", "true");
      }
    });
    document.querySelectorAll("[data-viewer-only]").forEach((el) => {
      el.style.display = isAdmin ? "none" : "";
    });
  }

  window.openDesklineDemoVideo = function openDesklineDemoVideo() {
    window.open(DEMO_VIDEO_URL, "_blank", "noopener,noreferrer");
  };

  window.loadDesklineRole = async function loadDesklineRole() {
    const token = getToken();
    if (!token) {
      applyAdminUI(false);
      return false;
    }
    // Prefer login payload cache
    const cached = localStorage.getItem("deskline_is_admin");
    if (cached === "0" || cached === "1") {
      applyAdminUI(cached === "1");
    }
    try {
      const res = await fetch("/api/auth/profile/", {
        headers: { Authorization: "Bearer " + token },
      });
      const json = await res.json();
      const data = (json && json.data) || {};
      const isAdmin = data.is_admin !== false && data.role !== "viewer";
      localStorage.setItem("deskline_is_admin", isAdmin ? "1" : "0");
      localStorage.setItem("deskline_role", data.role || (isAdmin ? "admin" : "viewer"));
      applyAdminUI(isAdmin);
      return isAdmin;
    } catch (_) {
      applyAdminUI(cached !== "0");
      return cached !== "0";
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => window.loadDesklineRole());
  } else {
    window.loadDesklineRole();
  }
})();

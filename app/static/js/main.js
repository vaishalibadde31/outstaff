document.addEventListener("DOMContentLoaded", () => {
  const alerts = document.querySelectorAll("[data-flash]");
  alerts.forEach((alert) => {
    setTimeout(() => {
      alert.classList.add("opacity-0", "translate-y-2");
      setTimeout(() => alert.remove(), 400);
    }, 3800);
  });
});

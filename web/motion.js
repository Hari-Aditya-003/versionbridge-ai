let queued = false;
window.addEventListener("scroll", () => {
  if (queued) return;
  queued = true;
  requestAnimationFrame(() => {
    document.documentElement.style.setProperty("--shift", `${Math.min(window.scrollY, 700) * 0.21}px`);
    queued = false;
  });
}, { passive: true });

const reveals = new IntersectionObserver(entries => {
  for (const entry of entries) {
    if (entry.isIntersecting) {
      entry.target.classList.add("arriving");
      reveals.unobserve(entry.target);
    }
  }
}, { threshold: 0.15 });

document.querySelectorAll("main .section").forEach(section => reveals.observe(section));

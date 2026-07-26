document.addEventListener("DOMContentLoaded", function () {
  const headerInner = document.querySelector(".md-header__inner");
  if (!headerInner) return;

  // Create sponsor buttons container
  const sponsorContainer = document.createElement("div");
  sponsorContainer.className = "md-header__sponsor-container";
  sponsorContainer.style.display = "inline-flex";
  sponsorContainer.style.alignItems = "center";
  sponsorContainer.style.marginLeft = "auto";
  sponsorContainer.style.marginRight = "0.5rem";

  sponsorContainer.innerHTML = `
    <a href="https://github.com/sponsors/shitan198u" target="_blank" rel="noopener" class="header-sponsor-badge header-sponsor-badge--github" title="Sponsor shitan198u on GitHub">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
      <span>Sponsor</span>
    </a>
    <a href="https://www.buymeacoffee.com/shivashitan" target="_blank" rel="noopener" class="header-sponsor-badge header-sponsor-badge--coffee" title="Buy Me a Coffee">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M20 3H4v10c0 2.21 1.79 4 4 4h6c2.21 0 4-1.79 4-4v-3h2c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 5h-2V5h2v3zM4 19h16v2H4z"/></svg>
      <span>Buy Me a Coffee</span>
    </a>
  `;

  // Insert before the repository widget or search bar
  const repoWidget = headerInner.querySelector(".md-header__source");
  if (repoWidget) {
    headerInner.insertBefore(sponsorContainer, repoWidget);
  } else {
    headerInner.appendChild(sponsorContainer);
  }
});

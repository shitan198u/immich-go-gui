// Client-side dynamic GitHub repository statistics fetcher (stars & forks)
(function () {
  const REPO = "shitan198u/immich-go-gui";
  const CACHE_KEY = "igg_gh_stats_cache";
  const CACHE_TTL_MS = 10 * 60 * 1000; // 10 minutes

  function updateDOM(stars, forks) {
    // Update star count elements in header / repository pills
    const starEls = document.querySelectorAll(".md-source__fact--stars, [data-md-component='source'] .md-source__fact--stars");
    starEls.forEach(function (el) {
      if (stars !== undefined && stars !== null) {
        el.textContent = stars.toLocaleString();
      }
    });

    const forkEls = document.querySelectorAll(".md-source__fact--forks, [data-md-component='source'] .md-source__fact--forks");
    forkEls.forEach(function (el) {
      if (forks !== undefined && forks !== null) {
        el.textContent = forks.toLocaleString();
      }
    });
  }

  function fetchStats() {
    try {
      const cached = sessionStorage.getItem(CACHE_KEY);
      if (cached) {
        const parsed = JSON.parse(cached);
        if (Date.now() - parsed.timestamp < CACHE_TTL_MS) {
          updateDOM(parsed.stars, parsed.forks);
          return;
        }
      }
    } catch (e) {
      // Ignore sessionStorage errors (e.g. private browsing restrictions)
    }

    fetch("https://api.github.com/repos/" + REPO)
      .then(function (response) {
        if (!response.ok) return null;
        return response.json();
      })
      .then(function (data) {
        if (!data) return;
        const stars = data.stargazers_count;
        const forks = data.forks_count;
        updateDOM(stars, forks);
        try {
          sessionStorage.setItem(
            CACHE_KEY,
            JSON.stringify({ stars: stars, forks: forks, timestamp: Date.now() })
          );
        } catch (e) {}
      })
      .catch(function () {
        // Fallback silently to static build values on network error
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fetchStats);
  } else {
    fetchStats();
  }
})();

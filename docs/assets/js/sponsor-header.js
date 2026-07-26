document.addEventListener("DOMContentLoaded", function () {
  // Prevent duplicate insertion on instant navigation
  if (document.querySelector(".igg-sponsor-wrapper")) return;

  // Buy Me a Coffee official cup SVG (from brand assets)
  const bmcSVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 884 1279" width="17" height="17" fill="currentColor">
    <path d="M791.109 297.518C841.793 259.688 855.287 189.418 827.243 139.46C781.803 58.2483 663.281 49.0847 606.321 105.677L555.919 155.739C532.866 133.011 504.376 118.29 473.386 116.688C442.396 115.087 411.804 126.677 387.617 148.457C336.064 95.2978 254.578 77.9556 184.088 100.616C113.597 123.276 63.1445 184.948 55.8 258.319C21.9219 290.963 1.23907 337.516 1.23907 388.018C1.23907 442.399 24.3563 491.517 61.8197 525.898C82.3694 627.562 126.849 779.124 221.905 864.785C251.783 891.503 287.616 901.567 323.985 898.143C342.17 914.012 364.041 926.194 388.104 932.84V958.648C388.104 1032.74 449.295 1093.08 524.408 1093.08C529.148 1093.08 533.861 1092.74 538.553 1092.08L518.193 1268.48C516.702 1280.81 525.782 1278.65 531.437 1277.6C536.948 1276.58 541.476 1273.27 543.713 1268.48L602.573 1143.71L661.432 1268.48C663.669 1273.27 668.198 1276.58 673.709 1277.6C679.363 1278.65 688.444 1280.81 686.953 1268.48L660.583 1043.24C695.211 1021.88 717.944 983.922 717.944 940.672V908.148C717.944 858.844 694.061 815.061 657.14 787.174C687.875 733.787 707.441 663.16 716.876 579.392C757.879 541.56 783.201 487.484 783.201 426.969C783.201 380.949 768.449 338.375 743.034 304.003L791.109 297.518Z"/>
  </svg>`;

  // GitHub Sponsors heart SVG
  const sponsorSVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
    <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
  </svg>`;

  const wrapper = document.createElement("div");
  wrapper.className = "igg-sponsor-wrapper";
  wrapper.innerHTML = `
    <a href="https://github.com/sponsors/shitan198u"
       target="_blank" rel="noopener"
       class="igg-sponsor-btn igg-sponsor-btn--github"
       title="Sponsor on GitHub">
      ${sponsorSVG}
      <span>Sponsor</span>
    </a>
    <a href="https://www.buymeacoffee.com/shivashitan"
       target="_blank" rel="noopener"
       class="igg-sponsor-btn igg-sponsor-btn--bmc"
       title="Buy Me a Coffee">
      ${bmcSVG}
      <span>Coffee</span>
    </a>
  `;

  // Insert right before the GitHub source widget (top-right of header)
  const sourceWidget = document.querySelector(".md-header__source");
  if (sourceWidget && sourceWidget.parentNode) {
    sourceWidget.parentNode.insertBefore(wrapper, sourceWidget);
  }
});

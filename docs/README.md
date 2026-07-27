---
hide:
  - navigation
  - toc
---

<div class="hero" markdown="1">

<span class="hero-badge">Desktop GUI · Open Source · Cross-platform</span>

# Immich-Go GUI

<p class="hero-lead">
A beautiful desktop GUI for <a href="https://github.com/simulot/immich-go">immich-go</a> —
bulk upload, archive, and stack your media with <a href="https://immich.app/">Immich</a>.
</p>

<div class="hero-actions" markdown="1">

[Get Started](user-guide/getting-started.md){ .md-button .md-button--primary }
[Choose Your Workflow](user-guide/choose-your-workflow.md){ .md-button }
[Downloads](https://github.com/shitan198u/immich-go-gui/releases/latest){ .md-button }

</div>

<div class="hero-meta" markdown="1">
:fontawesome-brands-windows: Windows · :fontawesome-brands-apple: macOS · :fontawesome-brands-linux: Linux
</div>

</div>

Immich-Go GUI is a cross-platform desktop application (PySide6/Qt) that wraps the [immich-go](https://github.com/simulot/immich-go) CLI. Configure jobs with forms, preview the exact command, and launch bulk media operations against your [Immich](https://immich.app/) server — without memorizing a forest of flags.

## Why Immich-Go GUI?

<div class="feature-grid">
  <div class="feature-card">
    <div class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg></div>
    <h3>Full workflow coverage</h3>
    <p>Eleven tabs for every upload, archive, and stack path — folder, Google Photos, iCloud, Picasa, Immich-to-Immich, and more.</p>
  </div>
  <div class="feature-card">
    <div class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>
    <h3>Secrets done right</h3>
    <p>API keys live in the OS keyring, travel as environment variables, and stay masked in previews and logs.</p>
  </div>
  <div class="feature-card">
    <div class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg></div>
    <h3>Multi-server profiles</h3>
    <p>Home vs work, staging vs production — switch Immich targets without re-entering credentials each time.</p>
  </div>
  <div class="feature-card">
    <div class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>
    <h3>Pre-flight safety</h3>
    <p>Connection tests, dry-run, process locks, and SHA256-verified binary downloads before long jobs start.</p>
  </div>
  <div class="feature-card">
    <div class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg></div>
    <h3>Simple & advanced modes</h3>
    <p>Friendly defaults for common fields, with a full flag surface when you need power-user control.</p>
  </div>
  <div class="feature-card">
    <div class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg></div>
    <h3>Real terminal launches</h3>
    <p>Jobs open in your preferred terminal so progress, errors, and resumes stay visible and inspectable.</p>
  </div>
</div>

## See it in action

<div class="shot-gallery">
  <a href="assets/screenshot-1.png">
    <img src="assets/screenshot-1.png" alt="Immich-Go GUI main window" />
    <span class="shot-label">Main Window</span>
  </a>
  <a href="assets/screenshot-2.png">
    <img src="assets/screenshot-2.png" alt="Workflow configuration tab" />
    <span class="shot-label">Workflow Tab</span>
  </a>
  <a href="assets/screenshot-3.png">
    <img src="assets/screenshot-3.png" alt="Command preview pane" />
    <span class="shot-label">Command Preview</span>
  </a>
</div>

## Start here

<p class="section-intro">Pick the path that matches what you need right now.</p>

<div class="card-grid">
  <a class="link-card" data-accent="coral" href="user-guide/getting-started/">
    <span class="card-kicker">First run</span>
    <strong>Getting Started</strong>
    <span class="card-desc">Install binaries or run from source, then take the first-run tour.</span>
  </a>
  <a class="link-card" data-accent="indigo" href="user-guide/choose-your-workflow/">
    <span class="card-kicker">Decision help</span>
    <strong>Choose Your Workflow</strong>
    <span class="card-desc">Decision tree and recipes for folder, cloud takeouts, and server-to-server.</span>
  </a>
  <a class="link-card" data-accent="amber" href="user-guide/troubleshooting/">
    <span class="card-kicker">Stuck?</span>
    <strong>Troubleshooting</strong>
    <span class="card-desc">Locks, terminals, SSL, antivirus, and 403s — fix it fast.</span>
  </a>
  <a class="link-card" data-accent="emerald" href="user-guide/security-and-privacy/">
    <span class="card-kicker">Trust</span>
    <strong>Security & Privacy</strong>
    <span class="card-desc">Keyring, env secrets, SSL, and the threat model explained clearly.</span>
  </a>
  <a class="link-card" data-accent="violet" href="developer-guide/architecture/">
    <span class="card-kicker">Contributors</span>
    <strong>Architecture</strong>
    <span class="card-desc">UI vs core split, data flow, and how to extend the app safely.</span>
  </a>
  <a class="link-card" data-accent="sky" href="reference/cli-command-mapping/">
    <span class="card-kicker">Lookup</span>
    <strong>CLI Command Mapping</strong>
    <span class="card-desc">Every GUI tab mapped to immich-go subcommands and flags.</span>
  </a>
</div>

## System architecture

```mermaid
flowchart TB
    classDef userStyle fill:#6366f1,stroke:#4338ca,color:#fff,stroke-width:2px
    classDef coreStyle fill:#8b5cf6,stroke:#6d28d9,color:#fff,stroke-width:2px
    classDef runStyle fill:#f59e0b,stroke:#b45309,color:#fff,stroke-width:2px
    classDef extStyle fill:#10b981,stroke:#047857,color:#fff,stroke-width:2px

    User([User]):::userStyle

    subgraph GUILayer["Immich-Go GUI"]
        direction TB
        Config[Config Manager]:::coreStyle
        Builder[Command Builder]:::coreStyle
        Validator[Input Validator]:::coreStyle
        BinMgr[Binary Manager]:::coreStyle
        Process[Process Runner]:::runStyle
    end

    subgraph External["External"]
        direction TB
        Binary[immich-go CLI]:::extStyle
        Server[(Immich Server)]:::extStyle
    end

    User -->|configure| Config
    User -->|fill form| Builder
    Builder --> Validator
    Validator --> Process
    Builder --> Process
    Config --> Process
    BinMgr --> Binary
    Process -->|launch with argv + secrets| Binary
    Binary -->|upload / archive / stack| Server
```

## Suggested reading order

### New users

<ol class="reading-path">
  <li><a href="user-guide/getting-started/">Getting Started</a> — install and first launch</li>
  <li><a href="user-guide/platform-notes/">Platform Notes</a> — OS-specific paths and quirks</li>
  <li><a href="user-guide/configuration/">Configuration</a> — server, keys, binary, themes</li>
  <li><a href="user-guide/choose-your-workflow/">Choose Your Workflow</a> — pick the right tab</li>
  <li>Your workflow page — Upload / Archive / Stack</li>
  <li><a href="user-guide/troubleshooting/">Troubleshooting</a> &amp; <a href="user-guide/faq/">FAQ</a> — keep bookmarked</li>
</ol>

### Contributors

<ol class="reading-path">
  <li><a href="developer-guide/architecture/">Architecture</a></li>
  <li><a href="developer-guide/core-modules/">Core Modules</a></li>
  <li><a href="developer-guide/testing/">Testing</a></li>
  <li><a href="developer-guide/adding-tabs-and-flags/">Adding Tabs and Flags</a></li>
  <li><a href="developer-guide/ci-cd-and-releases/">CI/CD and Releases</a></li>
</ol>

---

## Documentation map

### User Guide

<div class="card-grid">
  <a class="link-card" data-accent="coral" href="user-guide/getting-started/">
    <span class="card-kicker">Setup</span>
    <strong>Getting Started</strong>
    <span class="card-desc">Install binaries or run from source; first-run tour.</span>
  </a>
  <a class="link-card" data-accent="indigo" href="user-guide/platform-notes/">
    <span class="card-kicker">OS</span>
    <strong>Platform Notes</strong>
    <span class="card-desc">Windows / macOS / Linux install quirks and paths.</span>
  </a>
  <a class="link-card" data-accent="sky" href="user-guide/choose-your-workflow/">
    <span class="card-kicker">Recipes</span>
    <strong>Choose Your Workflow</strong>
    <span class="card-desc">Decision tree and common library recipes.</span>
  </a>
  <a class="link-card" data-accent="violet" href="user-guide/configuration/">
    <span class="card-kicker">Settings</span>
    <strong>Configuration</strong>
    <span class="card-desc">Server, API keys, binary manager, themes, admin key.</span>
  </a>
  <a class="link-card" data-accent="emerald" href="user-guide/profiles/">
    <span class="card-kicker">Multi-env</span>
    <strong>Profiles</strong>
    <span class="card-desc">Multi-server and multi-environment setups.</span>
  </a>
  <a class="link-card" data-accent="coral" href="user-guide/upload-workflows/">
    <span class="card-kicker">Import</span>
    <strong>Upload Workflows</strong>
    <span class="card-desc">Folder, Google Photos, iCloud, Picasa, Immich-to-Immich.</span>
  </a>
  <a class="link-card" data-accent="amber" href="user-guide/archive-workflows/">
    <span class="card-kicker">Export</span>
    <strong>Archive Workflows</strong>
    <span class="card-desc">Local export tabs plus Archive from Immich.</span>
  </a>
  <a class="link-card" data-accent="violet" href="user-guide/stack/">
    <span class="card-kicker">Server</span>
    <strong>Stack</strong>
    <span class="card-desc">Burst / RAW / HEIC stacking on the Immich server.</span>
  </a>
  <a class="link-card" data-accent="indigo" href="user-guide/advanced-flags/">
    <span class="card-kicker">Power user</span>
    <strong>Advanced Flags</strong>
    <span class="card-desc">Simple vs advanced mode; per-tab flag reference.</span>
  </a>
  <a class="link-card" data-accent="emerald" href="user-guide/security-and-privacy/">
    <span class="card-kicker">Safety</span>
    <strong>Security & Privacy</strong>
    <span class="card-desc">Keyring, env secrets, SSL, threat model.</span>
  </a>
  <a class="link-card" data-accent="amber" href="user-guide/troubleshooting/">
    <span class="card-kicker">Support</span>
    <strong>Troubleshooting</strong>
    <span class="card-desc">Locks, terminals, SSL, antivirus, 403s.</span>
  </a>
  <a class="link-card" data-accent="sky" href="user-guide/faq/">
    <span class="card-kicker">Q&A</span>
    <strong>FAQ</strong>
    <span class="card-desc">Short answers to the most common questions.</span>
  </a>
  <a class="link-card" data-accent="violet" href="user-guide/glossary/">
    <span class="card-kicker">Terms</span>
    <strong>Glossary</strong>
    <span class="card-desc">Shared vocabulary for the project and Immich.</span>
  </a>
</div>

### Developer Guide

<div class="card-grid">
  <a class="link-card" data-accent="violet" href="developer-guide/architecture/">
    <span class="card-kicker">Overview</span>
    <strong>Architecture</strong>
    <span class="card-desc">UI vs core split, data flow, security model.</span>
  </a>
  <a class="link-card" data-accent="indigo" href="developer-guide/core-modules/">
    <span class="card-kicker">Code</span>
    <strong>Core Modules</strong>
    <span class="card-desc">Module-by-module <code>core/</code> reference.</span>
  </a>
  <a class="link-card" data-accent="coral" href="developer-guide/adding-tabs-and-flags/">
    <span class="card-kicker">Extend</span>
    <strong>Adding Tabs & Flags</strong>
    <span class="card-desc">Grow CLI parity without breaking safety.</span>
  </a>
  <a class="link-card" data-accent="emerald" href="developer-guide/testing/">
    <span class="card-kicker">Quality</span>
    <strong>Testing</strong>
    <span class="card-desc">pytest, fixtures, headless Qt, <code>_norm_argv</code>.</span>
  </a>
  <a class="link-card" data-accent="amber" href="developer-guide/ci-cd-and-releases/">
    <span class="card-kicker">Ship</span>
    <strong>CI/CD & Releases</strong>
    <span class="card-desc">Branching, Release Please, packaging.</span>
  </a>
  <a class="link-card" data-accent="sky" href="developer-guide/scripts/">
    <span class="card-kicker">Tooling</span>
    <strong>Scripts</strong>
    <span class="card-desc">CLI help capture and review utilities.</span>
  </a>
</div>

### Reference

<div class="card-grid">
  <a class="link-card" data-accent="indigo" href="reference/config-schema/">
    <span class="card-kicker">Config</span>
    <strong>Config Schema</strong>
    <span class="card-desc">TOML fields, OS paths, and overrides.</span>
  </a>
  <a class="link-card" data-accent="coral" href="reference/environment-variables/">
    <span class="card-kicker">Env</span>
    <strong>Environment Variables</strong>
    <span class="card-desc"><code>IMMICH_GO_*</code> secret and server env map.</span>
  </a>
  <a class="link-card" data-accent="sky" href="reference/cli-command-mapping/">
    <span class="card-kicker">CLI</span>
    <strong>CLI Command Mapping</strong>
    <span class="card-desc">Maps all 11 GUI tabs to immich-go subcommands.</span>
  </a>
  <a class="link-card" data-accent="emerald" href="reference/immich-go-compatibility/">
    <span class="card-kicker">Versions</span>
    <strong>immich-go Compatibility</strong>
    <span class="card-desc">Tested versions, download, SHA256 checks.</span>
  </a>
</div>

### Related project files

| File | Purpose |
|------|---------|
| [README](https://github.com/shitan198u/immich-go-gui/blob/master/README.md) | Project landing page |
| [CONTRIBUTING](CONTRIBUTING.md) | How to contribute |
| [CHANGELOG](CHANGELOG.md) | Version history |
| [LICENSE](https://github.com/shitan198u/immich-go-gui/blob/master/LICENSE) | MIT license |

<div class="version-banner">
  <strong>Version note:</strong>
  <span>Docs track the application as of <strong>v1.1.2</strong>, tested with <strong>immich-go 0.32.0</strong>. If something in the UI disagrees with a page, prefer the running app and open an issue or PR.</span>
</div>

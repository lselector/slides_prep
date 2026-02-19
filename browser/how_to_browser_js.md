
video: How My Claude Code Sonnet 4.6 AI Agent Navigates Chrome Autonomous
https://www.youtube.com/watch?v=j6POqm76Slg

It's a high-level walkthrough of using a custom browser.js 
script to let a Claude Code agent control Chrome via 
the Chrome DevTools Protocol (CDP).

The video doesn't actually explain the internal 
implementation in detail, and you currently can't 
directly download that exact browser.js anywhere; 
Kris only says they might publish it later 
if enough people are interested

How To Train Your AI Agent's Skills (Claude Code / OpenClaw)
https://www.youtube.com/watch?v=KkJZY5Klymw

=======================================================
## What the transcript explains

Kris runs Chrome in remote debugging mode 
(e.g. with `--remote-debugging-port=9222`) 
so it exposes a CDP socket on port 9222 that external 
tools can connect to

Kris has a local CLI tool called browser.js which connects 
to that CDP socket and sends commands like `list`, 
`open <url>`, `elements`, and `click <index>` 
to control tabs and click elements. 

The Claude Code agent calls this CLI from a skill 
(skill.md / X skill) so it can: 
list tabs, navigate to a URL, inspect clickable elements, 
and click a specific element (e.g., the first Hacker News post)

The workflow demo:  
  - Run `browser.js list` → see open tabs and indexes
  - Run `browser.js open <url>` → navigate current tab to e.g. Hacker News
  - Use `click` plus content inspection (via CDP and a 
  - screenshot/content-grab command) to select and click the first post
  - Combine this with another skill (“X skill”) to open 
    the X/Twitter compose page and inject a draft post 
    using CDP scripting instead of simulating mouse moves

Conceptually, Kris emphasizes that this approach is 
“nothing magical” but efficient because it uses CDP commands, 
not a virtual mouse, and works across arbitrary sites in Chrome

## How much it explains about browser.js internals

- You see that browser.js is a CLI wrapper around CDP commands: 
  it exposes subcommands like `open`, `list`, `elements`, `click`, 
  each mapped to a specific CDP call to Chrome
  
- The speaker briefly shows that each command corresponds 
  to TypeScript/JavaScript code that calls CDP with a URL 
  argument (for `open`) or enumerates tabs for `list`

- However, they don't show full source, architecture, 
  or how CDP is wired (no full code for connecting to 
  `ws://localhost:9222`, no error handling, etc.). 
  It's more “here's what it can do” than “here's how 
  to implement it.”

## Can you download browser.js?

- In the video, the speaker says they might upload browser.js 
  (with all commands) to their skills MD / skillsmd.store page 
  if enough people like the video and show interest
 
- There is no public repository or direct download link 
  for browser.js shown in the transcript or in related writeups; 
  it's described as a personal tool not yet released. 

- There are other open-source CDP-based control frameworks 
  and Claude/agent examples on GitHub and Reddit, 
  but those are distinct projects, not this exact script.

  Example: 370+ skills - MIT license
  https://github.com/aiskillstore/marketplace 

## What you can replicate yourself

Even though you can't grab browser.js today, you can recreate the pattern:

- Launch Chrome with `--remote-debugging-port=9222` so it exposes CDP

- Use a Node.js/TypeScript CDP client (e.g., `chrome-remote-interface` 
  or the official Chrome DevTools Protocol libraries) 
  to write a small CLI with subcommands: 
  `list`, `open`, `elements`, `click` that talk to CDP. 
  [reddit](https://www.reddit.com/r/ClaudeAI/comments/1p47gjd/open_source_controlling_chrome_with_natural/)

- Wrap that CLI in a Claude Code skill (skill.md) 
  that defines when/how to invoke these commands so your 
  agent can call them as tools. 
  https://code.claude.com/docs/en/skills

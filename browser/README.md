# Browser Automation CLI via CDP

Commander-based CLI with 12 commands for browser automation using Chrome DevTools Protocol (CDP). Designed for AI agent integration with Claude Code.

## Installation

```bash
npm install
```

This installs:
- `chrome-remote-interface` - CDP client library
- `commander` - CLI framework

## Setup

Chrome must be running with remote debugging enabled on port 9222 (default):

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=./chrome-profile
```

## Commands (12 Total)

### 1. list - List all open tabs
```bash
node browser.js list
```
Shows all Chrome tabs/targets with IDs and URLs.

### 2. content - Get text content from element
```bash
node browser.js content
node browser.js content -s "div.main"
```

### 3. content-all - Get all page text
```bash
node browser.js content-all
```
Returns entire page text content (useful for reading page state).

### 4. search - Search for text on page
```bash
node browser.js search "Sign in"
```
Finds elements containing the search term.

### 5. screenshot - Capture page screenshot
```bash
node browser.js screenshot
node browser.js screenshot output.png
```

### 6. open - Navigate to URL
```bash
node browser.js open "https://x.com"
```

### 7. click - Click element
```bash
node browser.js click "button[aria-label='Post']"
node browser.js click "#submit-btn"
```

### 8. type - Type into input field
```bash
node browser.js type "input[name='username']" "myusername"
node browser.js type "textarea" "Hello World"
```

### 9. elements - Find all matching elements
```bash
node browser.js elements "button"
node browser.js elements "input[type='text']"
```
Returns array of all matching elements with their properties.

### 10. html - Get HTML content
```bash
node browser.js html
node browser.js html "div.content"
```

### 11. desc - Describe page structure
```bash
node browser.js desc
```
Returns JSON with:
- Page title and URL
- All buttons (first 5)
- All input fields (first 5)
- All links (first 5)

**Very useful for AI agents to understand page layout!**

### 12. close - Close connection
```bash
node browser.js close
```

## Port Configuration

All commands accept `-p` or `--port` option:

```bash
node browser.js desc -p 9223
node browser.js open "https://example.com" --port 9223
```

## Usage from Claude Code

When Claude Code reads the file:

```
read @browser.js
```

It will understand:
- 12 available commands
- CDP connection on port 9222
- How to control Chrome for automation

### Example AI Agent Workflow (X/Twitter)

```bash
# 1. Describe the page
node browser.js open "https://x.com"
node browser.js desc

# 2. Search for compose button
node browser.js search "Post"

# 3. Click compose
node browser.js click "a[href='/compose/post']"

# 4. Type tweet
node browser.js type "div[role='textbox']" "Hello from AI agent!"

# 5. Click post button
node browser.js click "button[data-testid='tweetButton']"

# 6. Verify
node browser.js screenshot posted.png
```

## Integration with Claude Skills

Create `claude-skills/browser.skill.md`:

```markdown
# Browser Control Skill

## Tool Location
`./browser.js` - Commander-based CLI with 12 commands

## Commands
- list: Show all tabs
- content: Get page text
- content-all: Get all text
- search <query>: Find text
- screenshot [file]: Capture screen
- open <url>: Navigate
- click <selector>: Click element
- type <selector> <text>: Type text
- elements <selector>: Find elements
- html [selector]: Get HTML
- desc: Describe page structure
- close: Close connection

## Connection
Connects to Chrome via CDP on port 9222 by default.

## Usage Pattern
1. Open page: `node browser.js open <url>`
2. Describe: `node browser.js desc`
3. Interact: `node browser.js click/type`
4. Verify: `node browser.js content` or `screenshot`
```

## Key Features

✓ **12 Commands** - Complete browser control  
✓ **Commander Framework** - Professional CLI interface  
✓ **JSON Output** - Easy for AI agents to parse  
✓ **CSS Selectors** - Standard web element targeting  
✓ **Port Flexible** - Works with any CDP port  
✓ **No Session Management** - Stateless commands  
✓ **Error Handling** - Clear error messages  

## Typical Usage Pattern for AI Agents

```javascript
// 1. Understand the page
exec('node browser.js desc')

// 2. Find elements
exec('node browser.js search "Login"')

// 3. Interact
exec('node browser.js click "#login-btn"')
exec('node browser.js type "input[type=password]" "secret"')

// 4. Verify
exec('node browser.js content')
```

## File Location for Claude Code

Place in your project root:
```
~/your-agent/
├── browser.js          # This file
├── package.json
└── claude-skills/
    └── browser.skill.md
```

## Troubleshooting

**"Failed to connect"**: Make sure Chrome is running with `--remote-debugging-port=9222`

**"Element not found"**: Use `desc` or `elements` commands to find correct selectors

**Multiple Chrome instances**: Use different ports with `-p` flag

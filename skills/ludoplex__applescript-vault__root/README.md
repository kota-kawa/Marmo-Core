# AppleScript Vault

A curated collection of exceptional AppleScript and JXA (JavaScript for Automation) resources, libraries, and script collections for macOS power users.

---

## Script Collections

### [kevin-funderburg/AppleScripts](https://github.com/kevin-funderburg/AppleScripts)
Extensively documented collection of production-quality AppleScripts organized by application (Finder, Safari, Mail, System Preferences). Designed to work standalone or with Keyboard Maestro, Alfred, BetterTouchTool, and Hazel. Excellent educational resource with clear code structure and inline comments.

### [ChristoferK/AppleScriptive](https://github.com/ChristoferK/AppleScriptive)
Functional AppleScripts employing advanced techniques: chevron syntax, `use` imports, and Script Object patterns for OOP-style code organization. Operates through Keyboard Maestro, Alfred, and Automator. Demonstrates professional-grade refactoring patterns and semantic grouping.

### [unforswearing/applescript](https://github.com/unforswearing/applescript)
Versatile snippet library covering macOS Lion through High Sierra. Scripts can be used individually or composed into larger projects. Good breadth of basic-to-intermediate patterns.

### [extracts/mac-scripting](https://github.com/extracts/mac-scripting)
MIT-licensed AppleScript and JXA scripts targeting academic/research workflows: exporting notes and highlight annotations from Papers 3 to DEVONthink Pro, metadata transfer (color, dates, citekeys). Includes getting-started guides for scripting Papers 3 and Bookends 13.

### [Ryan-Adams57/macOS-Automation-Collection](https://github.com/Ryan-Adams57/macOS-Automation-Collection)
Practical daily-driver scripts: restart Safari with session restore, create folders from Finder selections, auto-process camera imports, mount network volumes at startup, auto-eject removable drives, and reset the Touch Bar. Focused on hardware integration and workflow automation.

### [temochka/macos-automation](https://github.com/temochka/macos-automation)
Alfred Workflows, AppleScript, and JXA combined. Highlights: copy browser tab URL+title as Markdown link, produce GitHub issue/PR shortlinks. Clean, minimal scripts that do one thing well.

### [abbeycode/AppleScripts](https://github.com/abbeycode/AppleScripts)
Features a custom library loader system where each library script contains a copy-paste loader comment. Demonstrates compiled vs. plain-text library patterns and modular AppleScript architecture.

### [aymec/apple_scripts](https://github.com/aymec/apple_scripts)
Focused automation tricks: pull the active Chrome tab and invoke macOS native side-by-side view, window management, and display positioning scripts.

### [steventheworker/applescripts](https://github.com/steventheworker/applescripts)
Personal automation toolkit integrating AppleScripts with BetterTouchTool configurations. Real-world daily-use scripts and app automation setups.

### [princelundgren/automator-collection](https://github.com/PrinceBalabis/Automator)
Automator + AppleScript workflows: one-click Safari private session launcher, right-click PDF compression services (90 MB to 200 KB), and assorted Finder quick actions.

---

## Libraries and Frameworks

### [kevin-funderburg/AppleScript-libraries](https://github.com/kevin-funderburg/AppleScript-libraries)
Reusable script libraries with OOP-style Workflow script objects (mimicking classes and constructors) for Alfred 3 workflow development. Includes a ScriptDebugger editor-function library.

### [JXA-Cookbook/JXA-Cookbook](https://github.com/JXA-Cookbook/JXA-Cookbook)
The definitive wiki-based cookbook for JavaScript for Automation (3,000+ stars). Covers ES6 features in JXA, Objective-C bridge usage, shell/CLI integration, debugging with Safari Inspector, and app-specific guides (iTunes, Keynote, Messages, System Events, Safari, Chrome). Community-editable.

### [a-bangk/JXA-Examples](https://github.com/a-bangk/JXA-Examples)
Tested JXA example code (macOS 10.15.4 Catalina). Focused reference snippets for learning JavaScript for Automation patterns.

---

## Tools and Infrastructure

### [steipete/macos-automator-mcp](https://github.com/steipete/macos-automator-mcp)
MCP server for executing AppleScript and JXA with 200+ pre-built automation recipes. AI-workflow integration lets LLMs perform actions on your Mac. Recipes range from "toggle dark mode" to "extract all URLs from Safari."

### [TooTallNate/node-applescript](https://github.com/TooTallNate/node-applescript)
Node.js module providing `execString` and `execFile` for executing arbitrary AppleScript from JavaScript. Enables server-side and CLI AppleScript integration.

---

## Reference and Learning

### [SKaplanOfficial/macOS-Automation-Resources](https://github.com/SKaplanOfficial/macOS-Automation-Resources)
Meta-collection of books, tutorials, and code examples organized by automation technology. Covers "AppleScript: The Comprehensive Guide," "Everyday AppleScriptObjC," and more.

### [JMichaelTX/JXA-Resources](https://gist.github.com/JMichaelTX/d29adaa18088572ce6d4)
Comprehensive gist listing JXA resources: beginner guides, the JXA-Cookbook wiki, 2014 WWDC session video, and the Mac Automation Scripting Guide.

### [josh-/automating-macOS-with-JXA-presentation](https://github.com/josh-/automating-macOS-with-JXA-presentation)
Slides and sample code from the MelbJS meetup talk "Automating macOS with JavaScript for Automation." Practical introduction with real examples.

### [Apple Developer: AppleScript Language Guide](https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/introduction/ASLR_intro.html)
Official reference covering script objects, handler definitions, inheritance, `load script`, `use` frameworks, and the Objective-C bridge (AppleScriptObjC).

### [Apple Developer: AppleScriptObjC Translation Guide](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/AppendixA-AppleScriptObjCQuickTranslationGuide.html)
Quick-reference for translating Objective-C patterns to AppleScript syntax. Essential for bridging Cocoa frameworks.

---

## Useful Gists

### [vitorgalvao/browser-tab-info](https://gist.github.com/vitorgalvao/5392178)
AppleScript and JXA to get the frontmost tab's URL and title across multiple browsers (Safari, Chrome, Firefox).

### [dustinknopoff/mail-auto-save](https://gist.github.com/dustinknopoff/e16040fd76df3b546a5fa7938445a08d)
Automatically save emails to a folder using Mail.app rules, AppleScript, and Bash.

---

## Related Awesome Lists

- [jaywcjlove/awesome-mac](https://github.com/jaywcjlove/awesome-mac) - Comprehensive macOS software catalog
- [iCHAIT/awesome-macOS](https://github.com/iCHAIT/awesome-macOS) - Curated macOS apps and tools
- [phmullins/awesome-macos](https://github.com/phmullins/awesome-macos) - Another curated macOS list with automation tools
- [smashism/awesome-macadmin-tools](https://github.com/smashism/awesome-macadmin-tools) - Mac admin automation tools

---

## Contributing

Found an exceptional AppleScript or JXA resource? Open a PR or issue.

## License

This collection is licensed under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/).

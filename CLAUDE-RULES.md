### 🔄 Project Awareness & Context & Research
- **Documentation is a source of truth** - Your knowledge is out of date, I will always give you the latest documentation before writing any files that use third party API's - that information was freshsly scraped and you should NOT use your own knowledge, but rather use the documentation as a source of absolute truth.
- **Stick to OFFICIAL DOCUMENTATION PAGES ONLY** - For all research ONLY use official documentation pages. Use a r.jina scrape on the documentation page given to you in intitial.md and then create a llm.txt from it in your memory, then choose the exact pages that make sense for this project and scrape them using your internal scraping tool.
- **Ultrathink** - Use Ultrathink capabilities to decide which pages to scrape, what informatoin to put into PRD etc.
- **Create 2 documents .md files** - Phase 1 and phase 2 - phase 1 is skeleton code, phase 2 is complete production ready code with all features and all necessary frontend and backend implementations to use as a production ready tool.
- **Always scrape around 30-100 pages in total when doing research** - If a page 404s or does not contain correct content, try to scrape again and find the actual page/content. Put the output of each SUCCESFUL Jina scrape into a new directory with the name of the technology researched, then inside it .md or .txt files of each output
- **For Maximum efficiency, whenever you need to perform multiple independent operations, such as research, invoke all relevant tools simultaneously, rather that sequentially.**

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Always refer to the specific Phase document you are on** - If you are on phase 1, use phase-1.md, if you are on phase 2, use phase-2.md
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
- **Use clear, consistent imports** (prefer relative imports within packages).

### 🧪 Testing & Reliability
- **Always create unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case
- For the frontend, simulate the browser in the terminal as we can not run a real browser in the current environment.

### MCP Server
- Use context7 to understand a module, package, library or API in more depth if you don't have enough information yourself.

### When Implementing New Features or Changing Code  
- All python files must pass Pylance linting and type checking and all JavaScript files must pass ESLint linting and type checking.

### 📎 Style & Conventions
- Write **docstrings for every function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.

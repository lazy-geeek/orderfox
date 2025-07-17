### 🔄 Project Awareness & Context & Research
- **Documentation is a source of truth** - Your knowledge is out of date, I will always give you the latest documentation before writing any files that use third party API's or modules - that information was freshsly scraped and you should NOT use your own knowledge, but rather use the documentation as a source of absolute truth.
- **Ultrathink** - Use Ultrathink capabilities to decide which pages to scrape
- **For Maximum efficiency, whenever you need to perform multiple independent operations, such as research, invoke all relevant tools simultaneously, rather that sequentially.**

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
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
- Do not git commit any changes yourself. Only commit changes when explicitly asked to do so.

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


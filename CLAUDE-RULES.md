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
- Each playright e2e test should monitor the browser console for errors and warnings, and fail if any are detected.

### MCP Server
- Use context7 to understand a module, package, library or API in more depth if you don't have enough information yourself.
- Use jina to do webresearch and fetch web content.

### When Implementing New Features or Changing Code  
- All python files must pass pyright linting and type checking and all JavaScript files must pass ESLint linting and type checking.
- Do not git commit any changes yourself. Only commit changes when explicitly asked to do so.
- When generating terminal outputs yourself or in the generated code, beautify the output using boxes, tables, symbols, colors and Terminal UI / ASCII-Art

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

### Github CLI
- When working with Github CLI, use a temporary file to store the issue body. This allows you to edit the issue body more easliy. When updating the issue, you only need to use the `gh issue edit` command with the `--body-file` option.

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified packages.


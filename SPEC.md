# SPEC.md — AI-Powered Code Debugger
## Complete Project Specification and Phased Implementation Plan

# MASTER INSTRUCTIONS

Build a complete, functional, secure, and maintainable AI-powered code debugging and automatic fix generation web application.

**Rules and addendum override the project specification on any conflict. Begin with Phase 1 only.**

Read this entire specification before starting implementation.

Develop the project in five strictly controlled phases. Complete and verify the current phase, report actual results, and stop for my explicit approval before proceeding to the next phase.

Do not generate the entire application in one response. Do not skip phases, fabricate results, replace functional requirements with mockups, or claim success without executing the relevant checks.

Preserve all completed work in project files. If your session ends, resume from the last verified phase without unnecessarily rebuilding completed functionality.

---

# PART 1 — PROJECT OVERVIEW

## 1.1 Project Objective

Build a web application called **AI Code Debugger** that allows developers to:

1. Paste or upload buggy source code.
2. Select the programming language.
3. Analyze the code using an AI model.
4. Detect and explain programming errors.
5. Generate corrected source code.
6. Compare original and corrected code visually.
7. Accept or reject proposed fixes.
8. Review previous debugging sessions.
9. Track debugging history and fix decisions.

The core AI reasoning engine must be **Qwen2.5 Coder 32B Instruct through the OpenRouter API**.

The application should identify, where possible:
- Syntax errors.
- Logical errors.
- Potential runtime errors.
- Common programming mistakes.
- Relevant code quality issues.

Explain problems in simple language so developers can understand why a problem occurs and how the correction works.

The application must be a real full-stack implementation, not just a static interface or frontend demonstration.

## 1.2 Fixed Technology Stack

Use this exact technology stack. Do not substitute alternative frameworks or databases.

### Frontend
- React.js.
- TypeScript.
- Vite.
- Tailwind CSS.
- Monaco Editor.
- Monaco Diff Editor.
- React Router.
- Lucide React.
- Fetch API or Axios.
- Vitest.
- React Testing Library.

### Backend
- Python 3.10 or another compatible, supported Python version.
- FastAPI.
- Pydantic.
- SQLAlchemy.
- HTTPX.
- Pytest.
- Environment-based configuration using `python-dotenv` or Pydantic Settings.

### Database
- SQLite.
- SQLAlchemy ORM.
- Reliable database schema initialization.
- Appropriate transaction and error handling.

### AI Provider
- OpenRouter REST API.
- Default model identifier: `qwen/qwen-2.5-coder-32b-instruct`.
- Configurable through the backend environment variable `OPENROUTER_MODEL`.

Verify the model identifier through the official OpenRouter model catalog or a suitable API request when internet access and the required credentials are available.

If verification is unavailable, report that it could not be verified and continue with the configured identifier.

If OpenRouter confirms that the model is unavailable, report the issue and wait for approval. Do not silently substitute a different model.

### Development Servers
- Vite frontend: `http://localhost:5173`.
- FastAPI backend: `http://localhost:8000`.
- Uvicorn for running FastAPI locally.

## 1.3 Fixed Resource Limits

Use these limits throughout the application:

- Maximum source size: 102,400 UTF-8 bytes (100 KiB).
- Maximum source length: 3,000 lines.
- OpenRouter request timeout: 60 seconds.
- Maximum automatic retry for malformed AI output: one retry.
- Supported programming languages: Python, Java, C, C++, JavaScript.

Measure source size using UTF-8 encoded bytes, not character count.

The backend must reject oversized submissions even if frontend validation is bypassed.

Return HTTP 413 when the submitted source exceeds the configured size limit. Return appropriate validation errors for other invalid input.

Apply an appropriate total request-body limit that accounts for JSON serialization overhead.

---

# PART 2 — APPLICATION FEATURES

## 2.1 Application Shell and Navigation

Create a polished, developer-focused application interface.

Include:
- Sidebar navigation.
- Top navigation bar.
- Dashboard.
- Code Debugger.
- Debugging History.
- Settings.
- Responsive layouts.
- Consistent typography, spacing, borders, and icons.
- Loading, success, error, and empty states.

Use React Router for page navigation.

Implement the application shell and basic routes during Phase 1. Later-phase pages may initially display simple placeholders, but must not contain fake functionality or fabricated statistics.

## 2.2 Dashboard

Implement a dashboard using real information calculated from persisted debugging sessions.

Display:
- Total debugging sessions.
- Total detected issues.
- Accepted fixes.
- Rejected fixes.
- Recent debugging activity.
- A primary action to start a debugging session.

Derive all metrics from the database.

Show a meaningful empty state when no sessions exist. Never hardcode fake statistics in the running application.

## 2.3 Code Input and Editor

Build a debugging workspace using Monaco Editor.

Required capabilities:
- Paste source code.
- Edit source code.
- Upload supported source files.
- Select a programming language.
- Syntax highlighting.
- Line numbers.
- Appropriate indentation.
- Clear Code.
- Load Example.
- Analyze Code.
- Copy Code where applicable.
- Download Corrected Code when a fix exists.

Supported source file extensions:

- `.py`
- `.java`
- `.c`
- `.cpp`
- `.js`

Also allow `.h` and `.hpp` as C/C++ header extensions.

Validate file types, empty submissions, source size, and line count. Read uploaded files into the editor without executing them.

Keep language selection consistent with the selected file extension. Allow the user to confirm or change the detected language.

## 2.4 AI Bug Detection

When the user clicks Analyze Code:

1. Validate the input.
2. Preserve the original source code exactly.
3. Add line-number references on the backend for analysis.
4. Construct a structured debugging prompt.
5. Call OpenRouter through the backend.
6. Validate the returned response.
7. Display the analysis.
8. Persist the successfully validated debugging session.
9. Set the session decision to `Pending`.
10. Return the session ID and analysis result to the frontend.

For each detected issue, display:
- Title.
- Severity: Critical, High, Medium, or Low.
- Category: Syntax, Logic, Runtime, or Code Quality.
- Line number or line range, if identifiable.
- Explanation.
- Why the issue occurs.
- Suggested correction.

Clearly distinguish confirmed problems from potential problems and uncertainties.

Never invent line numbers, claim code execution occurred when it did not, or present speculative runtime failures as verified results.

## 2.5 Automatic Fix Generation

Generate a complete corrected source file while preserving the program's intended functionality.

For each successful analysis, return:
- Summary.
- Detected issues.
- Complete corrected code.
- Change descriptions.
- Reasons for the changes.
- Remaining concerns.

Avoid unrelated refactoring and unnecessary changes.

If the original code is incomplete or ambiguous, explain the uncertainty instead of inventing missing requirements.

Preserve quotes, indentation, blank lines, multiline strings, and complete source content.

If the model output is truncated or incomplete, detect the issue and report an error instead of silently accepting the result.

## 2.6 AI Response Schema

Request structured JSON with this logical format:

    {
      "summary": "Brief analysis summary",
      "issues": [
        {
          "title": "Issue description",
          "severity": "High",
          "category": "Logic",
          "line": 5,
          "line_end": 5,
          "explanation": "Why the issue occurs",
          "suggestion": "How to correct it"
        }
      ],
      "fixed_code": "Complete corrected source code",
      "changes": [
        {
          "description": "What changed",
          "reason": "Why the change is necessary"
        }
      ],
      "remaining_concerns": []
    }

Implement proper Pydantic models for validation. Treat the example above as a schema illustration, not a response to hardcode.

The backend must validate:
- Required fields.
- Field types.
- Allowed severity values.
- Allowed issue categories.
- Line references against the submitted source.
- Completeness of the corrected code field.
- Overall response structure.

When line references cannot be validated, report the uncertainty rather than fabricating a location.

### Malformed Response Handling

If parsing or schema validation fails:

1. Retry the model request once with a focused correction instruction.
2. Validate the retry response again.
3. If the retry fails, return a recoverable error.
4. Preserve the original source code.
5. Allow the user to retry manually.

Do not create unlimited retry loops.

Handle authentication failures, rate limits, timeouts, network errors, and unavailable models appropriately.

## 2.7 Diff Viewer

Use Monaco Diff Editor to display:
- Original code on the left.
- Corrected code on the right.
- Added lines.
- Removed lines.
- Modified lines.
- Synchronized scrolling where supported.

Provide:
- Review Fix.
- Apply Fix.
- Reject Fix.
- Restore Original.
- Copy Corrected Code.
- Download Corrected Code.

### Apply Fix

Only replace the current editor contents after the user explicitly accepts the proposed fix.

Record the decision as `Accepted` through the backend decision endpoint.

### Reject Fix

Preserve the original editor contents and record the decision as `Rejected`.

Retain both original and proposed code in the session history.

### Restore Original

Restore the exact original source associated with the selected debugging session.

### Download Corrected Code

Download the proposed corrected source using an appropriate file extension for the selected language.

Clearly distinguish original code, proposed code, and accepted editor contents.

Do not silently apply AI-generated changes.

## 2.8 Debugging History

Persist successful debugging sessions in SQLite using SQLAlchemy.

Each session must include:
- Unique session ID.
- Timestamp.
- Programming language.
- Original source.
- Detected issues.
- Analysis summary.
- Corrected source.
- Change explanations.
- Remaining concerns.
- Decision status.
- Relevant model metadata without secrets.

Allowed decision states:
- `Pending`.
- `Accepted`.
- `Rejected`.

A successful validated analysis must create a persisted `Pending` session.

The session remains `Pending` until the user explicitly accepts or rejects the proposed fix.

Store original and corrected source separately. Preserve both regardless of the user's decision.

## 2.9 Settings

Provide settings for:
- Preferred theme.
- Default programming language.
- Configured AI model identifier.
- API connection status.
- Source-size and line-count limits.
- OpenRouter configuration guidance.

Never display the complete API key.

Read model configuration from the backend environment. Do not permit untrusted frontend requests to override server-side model settings.

When the API key is missing, display a clear configuration error.

---

# PART 3 — BACKEND API CONTRACT

## 3.1 `GET /api/health`

Return a successful health response when the backend is operational.

## 3.2 `POST /api/debug`

Accept source code and language, validate the request, call OpenRouter, validate the AI response, and persist the successful debugging session.

A successful response must include:
- Session ID.
- Analysis summary.
- Detected issues.
- Corrected code.
- Change explanations.
- Remaining concerns.
- Decision status `Pending`.

Failed analysis must not be reported as a successful debugging session.

## 3.3 `GET /api/history`

Retrieve debugging history.

Support bounded results and pagination or another reasonable mechanism to prevent unbounded responses.

Implement this endpoint in Phase 4.

## 3.4 `GET /api/history/{id}`

Retrieve a specific persisted debugging session.

Requirements:
- Return the session and its stored analysis.
- Return HTTP 404 if the session does not exist.
- Validate the session identifier.
- Do not expose API credentials.

**Implement this endpoint in Phase 2**, alongside the database persistence required by `POST /api/debug`.

## 3.5 `PATCH /api/history/{id}`

Update the user's decision for a debugging session.

Accept only:
- `Accepted`
- `Rejected`

Requirements:
- Update only the decision field.
- Return the updated session.
- Return HTTP 404 if the session does not exist.
- Return HTTP 422 for invalid decision values or invalid request data.
- Preserve original source code.
- Preserve corrected source code.
- Preserve the AI analysis and explanations.
- Do not permit this endpoint to modify stored source code or analysis results.
- Use database transaction handling.

**Implement this endpoint in Phase 2**, so Phase 3 can integrate and test the real Apply Fix and Reject Fix workflows.

## 3.6 `DELETE /api/history/{id}`

Delete a particular debugging session and return an appropriate response.

Implement this endpoint in Phase 4.

## 3.7 `GET /api/settings/model`

Return safe model configuration information without exposing credentials.

Implement this endpoint in Phase 4.

## 3.8 API Engineering Requirements

Use:
- Pydantic request and response schemas.
- Centralized exception handling.
- Appropriate HTTP status codes.
- Consistent error responses.
- Input validation.
- Configurable CORS.
- Database transactions.
- Appropriate request limits.

Ensure the frontend uses the real backend endpoints.

---

# PART 4 — SYSTEM ARCHITECTURE

## 4.1 Logical Layers

Implement four layers.

**Frontend Layer:** React, TypeScript, Vite, Tailwind CSS, Monaco Editor, diff viewer, routing, dashboard, issues, history, and settings.

**Backend Layer:** FastAPI routes, Pydantic validation, request handling, prompt construction, response parsing, history services, and settings.

**AI Layer:** Qwen2.5 Coder 32B Instruct through OpenRouter.

**Storage Layer:** SQLite and SQLAlchemy for persistent debugging sessions and user decisions.

Keep each layer modular.

Separate API routes, schemas, database models, database operations, AI client, debugging service, prompt construction, response validation, UI components, shared types, and tests.

## 4.2 Suggested Directory Structure

Create a structure similar to:

    ai-code-debugger/
    ├── frontend/
    │   ├── src/
    │   │   ├── components/
    │   │   ├── pages/
    │   │   ├── layouts/
    │   │   ├── hooks/
    │   │   ├── services/
    │   │   ├── types/
    │   │   ├── utils/
    │   │   ├── App.tsx
    │   │   └── main.tsx
    │   ├── package.json
    │   ├── vite.config.ts
    │   └── tsconfig.json
    ├── backend/
    │   ├── app/
    │   │   ├── api/
    │   │   ├── core/
    │   │   ├── models/
    │   │   ├── schemas/
    │   │   ├── services/
    │   │   ├── database.py
    │   │   └── main.py
    │   ├── tests/
    │   └── requirements.txt
    ├── .gitignore
    ├── .env.example
    └── SPEC.md

Keep the final implementation consistent with the actual directory structure and startup commands.

---

# PART 5 — SECURITY AND CONFIGURATION

## 5.1 Environment Variables

Provide a root or backend `.env.example` with the appropriate variables:

    OPENROUTER_API_KEY=
    OPENROUTER_MODEL=qwen/qwen-2.5-coder-32b-instruct
    OPENROUTER_TIMEOUT=60
    MAX_SOURCE_BYTES=102400
    MAX_SOURCE_LINES=3000
    DATABASE_URL=sqlite:///./debugger.db
    FRONTEND_ORIGIN=http://localhost:5173

Adapt the exact file location and configuration loading as needed, but keep variable names consistent.

Never put real API credentials in `.env.example`.

Create `.gitignore` during Phase 1, excluding:
- `.env`.
- Python virtual environments.
- Python cache files.
- `node_modules`.
- Frontend build outputs.
- Test and coverage artifacts.
- Local SQLite database files containing user source code.
- Logs and generated files.

Never expose the OpenRouter key through frontend code or browser environment variables.

## 5.2 OpenRouter Client

Create a dedicated backend service using HTTPX.

Requirements:
- Use the configured OpenRouter endpoint.
- Use the configured model identifier.
- Read the API key only from backend environment variables.
- Set a 60-second request timeout.
- Handle non-success HTTP responses.
- Validate returned assistant content.
- Handle malformed or incomplete responses.
- Retry malformed structured output at most once.
- Provide useful configuration and connectivity errors.
- Avoid logging credentials.

Verify the configured model when possible.

## 5.3 Security Boundaries

Never execute arbitrary user-submitted or AI-generated code on the server.

Treat all submitted code, uploaded files, and AI output as untrusted.

Validate request bodies, source sizes, file types, language choices, and response schemas.

Do not let instructions embedded inside submitted source override the debugging task.

Avoid unnecessary source-code logging. Explain that debugging history stores submitted and corrected source locally in SQLite.

Do not claim a fix was executed or tested unless actual execution or validation occurred.

---

# PART 6 — FIVE-PHASE DEVELOPMENT PLAN

## GENERAL PHASE RULES

At the end of each phase:

1. Run the relevant tests and builds.
2. Fix failures within that phase.
3. Rerun affected checks.
4. Report files created or modified.
5. Provide actual commands and results.
6. Identify unresolved issues.
7. Stop and wait for explicit approval.

Never fabricate terminal output, test results, API responses, or implementation status.

Do not advance to the next phase automatically.

If a dependency, API key, or external service prevents verification, state the limitation clearly and explain what remains to be tested.

## PHASE 1 — Project Skeleton and Connectivity

### Implement

- Initialize React, TypeScript, Vite, and Tailwind CSS.
- Initialize FastAPI and its dependencies.
- Create the project directory structure.
- Implement the application shell.
- Create sidebar and top navigation.
- Configure React Router.
- Create Dashboard, Code Debugger, History, and Settings routes.
- Implement basic placeholder pages for unfinished features.
- Implement `GET /api/health`.
- Configure frontend-to-backend communication.
- Configure CORS for `http://localhost:5173` through an environment setting.
- Create `.env.example`.
- Create `.gitignore`.
- Implement basic error handling.
- Provide initial installation and startup instructions.

Do not implement persistent debugging history or full AI debugging in Phase 1.

### Required Tests

- Pytest test for `GET /api/health`.
- Vitest smoke test verifying that the frontend renders.
- Frontend production build.
- Frontend-to-backend health connectivity check.

### Acceptance Criteria

- Frontend starts.
- Backend starts.
- Frontend can reach the health endpoint.
- Application shell and routes render.
- `.env.example` and `.gitignore` exist.
- Required checks are executed and reported honestly.

### Stop

Report the completed work, actual command results, exit statuses, and unresolved issues.

Wait for my explicit approval before Phase 2.

## PHASE 2 — OpenRouter, AI Debugging, and Session Foundation

### Implement

- Dedicated OpenRouter client.
- Configurable model identifier.
- Model availability verification when possible.
- Request validation.
- UTF-8 byte-size and line-count limits.
- Backend-generated line-number references.
- Structured debugging prompts.
- `POST /api/debug`.
- Pydantic response validation.
- One bounded retry for malformed output.
- Recoverable API errors.
- SQLite database schema initialization needed for session persistence.
- SQLAlchemy session model and database operations.
- Persistent creation of successfully analyzed sessions with `Pending` decisions.
- `GET /api/history/{id}`.
- `PATCH /api/history/{id}`.
- HTTP 404 behavior for missing sessions.
- HTTP 422 behavior for invalid decision data.
- Preservation of stored source code and analysis during decision updates.

**Do not defer database table initialization or either session endpoint to Phase 4.** Phase 3 depends on these capabilities.

### Required Tests

Use a mocked OpenRouter client in automated tests only, never in the running application.

Test:
- Successful AI response validation.
- Empty code.
- Unsupported languages.
- Input exceeding 102,400 UTF-8 bytes.
- Input exceeding 3,000 lines.
- Invalid JSON.
- Schema-validation failures.
- Successful bounded retry.
- Retry exhaustion.
- Authentication errors.
- Rate limits.
- Timeouts.
- Network failures.
- Database initialization.
- Successful analysis creating a `Pending` session.
- Retrieving an existing session.
- HTTP 404 for a missing session.
- Updating a session to `Accepted`.
- Updating a session to `Rejected`.
- HTTP 422 for invalid decision values.
- Decision updates preserving original source code.
- Decision updates preserving corrected source code and analysis results.
- Failed analysis not producing a false successful result.

### Live-Model Verification

When valid credentials and internet access are available, make a real request to OpenRouter using the configured model.

Use small buggy programs to assess:
- Accuracy of issue descriptions.
- Correctness of proposed fixes.
- Line-number accuracy.
- Response parsing and validation.
- Successful persistence of results.

Use the buggy examples introduced in Phase 3 as the shared sample set when they are available. Until then, use temporary minimal test programs within Phase 2 and preserve any useful results.

Clearly distinguish real API results from mocked automated tests.

If credentials or connectivity are unavailable, report that live-model verification could not be completed. Never substitute fabricated AI results.

### Acceptance Criteria

All required session endpoints exist and work before Phase 3 begins.

The database schema and session persistence are operational.

### Stop

Report test results and any unresolved issues.

Wait for my explicit approval before Phase 3.

## PHASE 3 — Editor, Issue Panel, Diff Viewer, and Sample Programs

### Implement

- Monaco Editor.
- Source-file upload.
- File extension validation.
- Language selection.
- Analyze Code.
- Clear Code.
- Load Example.
- Detected issues panel.
- Severity and category indicators.
- Explanations and suggested corrections.
- Monaco Diff Editor.
- Original and corrected source comparison.
- Apply Fix.
- Reject Fix.
- Restore Original.
- Copy Corrected Code.
- Download Corrected Code.
- Loading, error, empty, and successful states.
- Real backend integration.
- Real `PATCH /api/history/{id}` decision updates.

### Load Example — Required Sample Programs

Include at least one small buggy example for each supported programming language:
- Python.
- Java.
- C.
- C++.
- JavaScript.

Each example must:
- Contain an intentional, understandable bug.
- Include a brief description of the expected behavior.
- Be suitable for testing AI bug detection and fix generation.
- Be selectable through the Load Example action.
- Populate the editor with the example code without executing it.
- Be stored in a maintainable location, such as frontend example data files.

Phase 5 may refine these examples and add more comprehensive test cases.

Phase 2 may reuse temporary minimal buggy programs for live-model verification. Once the Phase 3 examples exist, use them as the shared sample set for further model verification.

**Do not wait until Phase 5 to implement Load Example or the five language examples.**

### Required Tests

- Editor rendering.
- Language selection.
- File upload and validation.
- Analysis request submission.
- Rendering issues from actual API responses.
- Diff viewer rendering.
- Apply Fix requiring explicit user approval.
- Reject Fix preserving the original source.
- Restore Original restoring the correct content.
- Decision persistence through the Phase 2 endpoint.
- Failed API calls displaying recoverable errors.
- Failed decision persistence not displaying false success.
- Load Example working for all five supported languages.

### Acceptance Criteria

A successful AI analysis can be reviewed and accepted or rejected through the UI, with the corresponding decision persisted by the backend.

All five example programs are selectable through Load Example.

### Stop

Report actual test results and provide exact commands to launch the application for manual inspection.

Wait for my explicit approval before Phase 4.

I will manually test the running application after this phase.

## PHASE 4 — Dashboard, History List, and Settings

### Implement

- `GET /api/history`.
- Pagination or bounded history results.
- `DELETE /api/history/{id}`.
- `GET /api/settings/model`.
- Database-backed dashboard statistics.
- Recent activity.
- History search.
- Sorting by date.
- Session detail views.
- Original and corrected code review from history.
- Theme settings.
- Default language settings.
- Model configuration information.
- Safe API connection status.
- Empty states and error handling.

Reuse the session database and decision endpoints implemented in Phase 2.

Do not recreate these endpoints or change their contracts without a demonstrated need.

### Required Tests

- History listing.
- Search and sorting.
- Session deletion.
- Model settings response.
- Dashboard statistics matching database contents.
- Empty database behavior.
- Persistence across application restarts.
- Correct handling of failed database operations.
- Existing Phase 2 and Phase 3 tests still passing.

### Stop

Report the implementation, tests, and unresolved issues.

Wait for my explicit approval before Phase 5.

## PHASE 5 — Integration, Final Testing, and Documentation

### Implement and Verify

- Full backend test suite.
- Full frontend test suite.
- Frontend production build.
- Frontend-to-backend communication.
- OpenRouter integration when credentials are available.
- Session creation and retrieval.
- Apply and Reject workflows.
- Decision persistence.
- History search, sorting, and deletion.
- Dashboard statistics.
- Settings.
- Environment configuration.
- Security and error handling.

Fix discovered failures and rerun affected tests.

### Refine Sample Programs

Refine the five sample programs created in Phase 3:
- Python.
- Java.
- C.
- C++.
- JavaScript.

Ensure they demonstrate understandable syntax errors, logical errors, or potential runtime issues where appropriate.

Document their expected behavior and intended bugs.

Do not execute arbitrary source code as part of the production debugging workflow.

### README

Document:
- Project overview.
- Architecture.
- Prerequisites.
- Project structure.
- Frontend installation.
- Backend installation.
- Virtual environment setup.
- Environment variables.
- OpenRouter configuration.
- Local startup commands.
- Testing commands.
- Production build.
- Troubleshooting.
- Security considerations.
- Known limitations.

### Final Acceptance Criteria

The project is complete only when:
- The frontend and backend communicate.
- Real OpenRouter integration works when valid credentials and model availability permit.
- AI responses are validated.
- Corrected source code is generated and displayed.
- Diff review works.
- Apply and Reject workflows work.
- Decisions persist in SQLite.
- History and dashboard use real stored data.
- Tests and builds have been executed.
- Documentation is complete.

### Stop

Provide a final report with actual commands, exit statuses, test results, failed checks, and checks that could not be performed.

Provide exact startup commands and manual verification steps.

Wait for my explicit approval before claiming that the project is fully verified.

I will manually inspect the application after this phase.

---

# PART 7 — TESTING AND AGENT HONESTY

## 7.1 Required Phase Report

At the end of each phase, provide:

### Phase Status
State the phase number and whether its acceptance criteria have been met.

### Files Created or Modified
List important files and their responsibilities.

### Commands Executed
For every relevant command, report:
- Exact command.
- Whether it was executed.
- Exit status.
- Actual relevant output or test summary.

### Tests and Build Results
Separate:
- Passed.
- Failed.
- Not run.
- Blocked by external dependencies.

### Manual Verification
Explain what I should launch, open, or test myself.

### Remaining Issues
List unresolved bugs, missing credentials, unavailable services, and unverified behavior.

### Next Step
State which phase comes next and wait for my approval.

## 7.2 Mocking Policy

Mock the OpenRouter client in automated tests only, never in the running application.

When credentials are unavailable, the real application must show a configuration error. It must not silently return hardcoded analysis, fake corrected code, fabricated statistics, or simulated API success.

## 7.3 Honest Verification

Never claim that a build, test, API call, model verification, or deployment succeeded unless it was actually executed and verified.

Do not invent:
- Terminal output.
- Test counts.
- Model responses.
- Debugging results.
- Dashboard statistics.
- File creation.
- Deployment status.

Clearly identify anything that could not be tested.

## 7.4 Approval Protocol

After completing each phase, stop and wait for explicit approval.

I will respond with a message such as:

`Approved, proceed to Phase 2.`

Proceed only when the approval corresponds to the next phase.

If the coding-agent session ends, preserve all completed files and report the last verified phase. On resumption, inspect the actual files and available verification evidence before continuing.

---

# FINAL EXECUTION INSTRUCTION

Read this entire `SPEC.md` before coding.

**Start Phase 1 only.**

Create the initial project structure, frontend application shell, navigation, FastAPI health endpoint, environment examples, `.gitignore`, CORS configuration, and required smoke tests.

Execute the relevant checks and report the actual results.

Do not start Phase 2 or generate the remaining phases until I explicitly approve continuation.
/**
 * Custom QA Agent for GitHub Enterprise
 *
 * Demonstrates an AI-powered QA agent that:
 * - Reviews Pull Requests (code quality, security, best practices)
 * - Analyzes open issues and suggests priorities
 * - Checks repo health (CI status, test coverage, stale branches)
 * - Posts AI-generated review comments on PRs
 *
 * Usage:
 *   ANTHROPIC_API_KEY=sk-... node qa-agent.mjs --repo owner/repo
 *   ANTHROPIC_API_KEY=sk-... node qa-agent.mjs --repo owner/repo --pr 42
 *   ANTHROPIC_API_KEY=sk-... node qa-agent.mjs --repo owner/repo --health
 */

import Anthropic from "@anthropic-ai/sdk";
import { execSync } from "child_process";

// ─── Config ───────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const repoFlag = args.indexOf("--repo");
const prFlag = args.indexOf("--pr");
const healthFlag = args.includes("--health");
const postFlag = args.includes("--post-review");

const REPO = repoFlag !== -1 ? args[repoFlag + 1] : "brainupgrade-in/ghentworkshop";
const PR_NUMBER = prFlag !== -1 ? args[prFlag + 1] : null;
// GitHub Enterprise: set GITHUB_API_URL=https://github.yourcompany.com/api/v3

if (!process.env.ANTHROPIC_API_KEY) {
  console.error("Error: ANTHROPIC_API_KEY environment variable required");
  console.error("Usage: ANTHROPIC_API_KEY=sk-... node qa-agent.mjs --repo owner/repo");
  process.exit(1);
}

const client = new Anthropic();

// ─── GitHub Tools ─────────────────────────────────────────────────────────────

function gh(endpoint, method = "GET", body = null) {
  try {
    const cmd = body
      ? `gh api ${endpoint} -X ${method} --input - <<'EOF'\n${JSON.stringify(body)}\nEOF`
      : `gh api ${endpoint}`;
    return JSON.parse(execSync(cmd, { encoding: "utf-8", timeout: 30000 }));
  } catch (e) {
    return { error: e.message.substring(0, 300) };
  }
}

const TOOLS = [
  {
    name: "list_pull_requests",
    description: "List open pull requests for a GitHub repo. Returns PR number, title, author, labels, and changed files count.",
    input_schema: {
      type: "object",
      properties: {
        repo: { type: "string", description: "owner/repo format" },
        state: { type: "string", enum: ["open", "closed", "all"], description: "PR state filter" },
      },
      required: ["repo"],
    },
  },
  {
    name: "get_pr_details",
    description: "Get detailed information about a specific PR including diff, commits, review status, and CI checks.",
    input_schema: {
      type: "object",
      properties: {
        repo: { type: "string", description: "owner/repo" },
        pr_number: { type: "integer", description: "PR number" },
      },
      required: ["repo", "pr_number"],
    },
  },
  {
    name: "get_pr_diff",
    description: "Get the full code diff for a pull request. Use this to review actual code changes.",
    input_schema: {
      type: "object",
      properties: {
        repo: { type: "string", description: "owner/repo" },
        pr_number: { type: "integer", description: "PR number" },
      },
      required: ["repo", "pr_number"],
    },
  },
  {
    name: "list_issues",
    description: "List open issues for a repo with labels, assignees, and creation dates.",
    input_schema: {
      type: "object",
      properties: {
        repo: { type: "string", description: "owner/repo" },
        labels: { type: "string", description: "Comma-separated label filter" },
        state: { type: "string", enum: ["open", "closed", "all"] },
      },
      required: ["repo"],
    },
  },
  {
    name: "get_repo_info",
    description: "Get repository metadata: language, stars, forks, default branch, license, topics, and recent activity.",
    input_schema: {
      type: "object",
      properties: { repo: { type: "string", description: "owner/repo" } },
      required: ["repo"],
    },
  },
  {
    name: "list_branches",
    description: "List branches with their last commit date to find stale branches.",
    input_schema: {
      type: "object",
      properties: { repo: { type: "string", description: "owner/repo" } },
      required: ["repo"],
    },
  },
  {
    name: "get_workflow_runs",
    description: "Get recent CI/CD workflow runs and their status (success, failure, in_progress).",
    input_schema: {
      type: "object",
      properties: {
        repo: { type: "string", description: "owner/repo" },
        limit: { type: "integer", description: "Number of runs to fetch (default 10)" },
      },
      required: ["repo"],
    },
  },
  {
    name: "get_file_content",
    description: "Read a specific file from the repo (e.g., README, config files, source code).",
    input_schema: {
      type: "object",
      properties: {
        repo: { type: "string", description: "owner/repo" },
        path: { type: "string", description: "File path in repo" },
        ref: { type: "string", description: "Branch or commit SHA (default: main)" },
      },
      required: ["repo", "path"],
    },
  },
  {
    name: "post_pr_review",
    description: "Post a review comment on a PR. Use APPROVE, REQUEST_CHANGES, or COMMENT.",
    input_schema: {
      type: "object",
      properties: {
        repo: { type: "string", description: "owner/repo" },
        pr_number: { type: "integer", description: "PR number" },
        body: { type: "string", description: "Review body in markdown" },
        event: { type: "string", enum: ["APPROVE", "REQUEST_CHANGES", "COMMENT"] },
      },
      required: ["repo", "pr_number", "body", "event"],
    },
  },
  {
    name: "search_code",
    description: "Search for code patterns across the repo (e.g., security anti-patterns, TODO comments).",
    input_schema: {
      type: "object",
      properties: {
        repo: { type: "string", description: "owner/repo" },
        query: { type: "string", description: "Search query (code pattern)" },
      },
      required: ["repo", "query"],
    },
  },
];

// ─── Tool Execution ───────────────────────────────────────────────────────────

function executeTool(name, input) {
  switch (name) {
    case "list_pull_requests": {
      const state = input.state || "open";
      return gh(`repos/${input.repo}/pulls?state=${state}&per_page=20`);
    }
    case "get_pr_details": {
      const pr = gh(`repos/${input.repo}/pulls/${input.pr_number}`);
      const reviews = gh(`repos/${input.repo}/pulls/${input.pr_number}/reviews`);
      const checks = gh(`repos/${input.repo}/commits/${pr.head?.sha}/check-runs`);
      return { pr, reviews, checks: checks.check_runs?.slice(0, 10) || [] };
    }
    case "get_pr_diff": {
      try {
        const diff = execSync(
          `gh api repos/${input.repo}/pulls/${input.pr_number} -H "Accept: application/vnd.github.v3.diff"`,
          { encoding: "utf-8", timeout: 30000 }
        );
        return { diff: diff.substring(0, 15000) }; // limit to 15K chars
      } catch (e) {
        return { error: e.message.substring(0, 300) };
      }
    }
    case "list_issues": {
      let endpoint = `repos/${input.repo}/issues?state=${input.state || "open"}&per_page=20`;
      if (input.labels) endpoint += `&labels=${encodeURIComponent(input.labels)}`;
      return gh(endpoint);
    }
    case "get_repo_info": {
      const repo = gh(`repos/${input.repo}`);
      const langs = gh(`repos/${input.repo}/languages`);
      const contributors = gh(`repos/${input.repo}/contributors?per_page=5`);
      return { repo, languages: langs, top_contributors: contributors };
    }
    case "list_branches": {
      return gh(`repos/${input.repo}/branches?per_page=30`);
    }
    case "get_workflow_runs": {
      const limit = input.limit || 10;
      return gh(`repos/${input.repo}/actions/runs?per_page=${limit}`);
    }
    case "get_file_content": {
      const ref = input.ref ? `?ref=${input.ref}` : "";
      const data = gh(`repos/${input.repo}/contents/${input.path}${ref}`);
      if (data.content) {
        data.decoded_content = Buffer.from(data.content, "base64").toString("utf-8");
        delete data.content; // save tokens
      }
      return data;
    }
    case "post_pr_review": {
      if (!postFlag) {
        return { skipped: true, message: "Dry-run mode. Use --post-review flag to actually post. Review body below.", body: input.body, event: input.event };
      }
      return gh(`repos/${input.repo}/pulls/${input.pr_number}/reviews`, "POST", {
        body: input.body,
        event: input.event,
      });
    }
    case "search_code": {
      const q = encodeURIComponent(`${input.query} repo:${input.repo}`);
      return gh(`search/code?q=${q}&per_page=10`);
    }
    default:
      return { error: `Unknown tool: ${name}` };
  }
}

// ─── Agent Loop ───────────────────────────────────────────────────────────────

async function runAgent(userPrompt) {
  console.log("\n╔══════════════════════════════════════════════════╗");
  console.log("║  🤖 GitHub QA Agent powered by Claude Opus 4.6  ║");
  console.log("╚══════════════════════════════════════════════════╝\n");
  console.log(`Repository: ${REPO}`);
  console.log(`Task: ${userPrompt.substring(0, 100)}...\n`);

  const messages = [{ role: "user", content: userPrompt }];

  const systemPrompt = `You are an expert QA Agent for GitHub Enterprise. You review code, analyze repositories, and provide actionable quality assessments.

Your capabilities:
- Review pull requests for code quality, security issues, and best practices
- Analyze repository health (CI/CD, test coverage, stale branches, issue backlog)
- Search for security anti-patterns (hardcoded secrets, SQL injection, XSS)
- Prioritize issues and suggest improvements
- Post structured review comments on PRs

When reviewing code:
1. Check for security vulnerabilities (OWASP Top 10)
2. Evaluate code quality (naming, complexity, duplication)
3. Verify error handling and edge cases
4. Check for test coverage gaps
5. Assess documentation completeness

Format your findings as a structured report with severity levels:
- 🔴 CRITICAL: Security vulnerabilities, data loss risks
- 🟠 HIGH: Bugs, missing error handling
- 🟡 MEDIUM: Code quality, maintainability
- 🔵 LOW: Style, documentation, minor improvements

Always be specific — reference file names, line numbers, and provide fix suggestions.`;

  let turnCount = 0;
  const MAX_TURNS = 15;

  while (turnCount < MAX_TURNS) {
    turnCount++;
    process.stdout.write(`\n--- Agent Turn ${turnCount} ---\n`);

    const response = await client.messages.create({
      model: "claude-opus-4-6",
      max_tokens: 8192,
      system: systemPrompt,
      thinking: { type: "adaptive" },
      tools: TOOLS,
      messages,
    });

    // Process response blocks
    for (const block of response.content) {
      if (block.type === "thinking") {
        process.stdout.write(`💭 Thinking... (${block.thinking.length} chars)\n`);
      } else if (block.type === "text") {
        console.log("\n" + block.text);
      } else if (block.type === "tool_use") {
        console.log(`🔧 Calling: ${block.name}(${JSON.stringify(block.input).substring(0, 80)}...)`);
      }
    }

    // Check if done
    if (response.stop_reason === "end_turn") {
      console.log("\n✅ QA Agent completed.");
      console.log(`   Turns: ${turnCount} | Input tokens: ${response.usage.input_tokens} | Output tokens: ${response.usage.output_tokens}`);
      break;
    }

    // Handle tool calls
    if (response.stop_reason === "tool_use") {
      const toolBlocks = response.content.filter((b) => b.type === "tool_use");
      messages.push({ role: "assistant", content: response.content });

      const toolResults = toolBlocks.map((tool) => {
        const result = executeTool(tool.name, tool.input);
        const resultStr = JSON.stringify(result);
        // Truncate large results
        const truncated = resultStr.length > 20000
          ? resultStr.substring(0, 20000) + "\n... [truncated]"
          : resultStr;
        console.log(`   ↳ Result: ${truncated.substring(0, 120)}...`);
        return {
          type: "tool_result",
          tool_use_id: tool.id,
          content: truncated,
        };
      });

      messages.push({ role: "user", content: toolResults });
    }
  }

  if (turnCount >= MAX_TURNS) {
    console.log("\n⚠️  Max turns reached. Agent stopped.");
  }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

let prompt;

if (PR_NUMBER) {
  prompt = `Review Pull Request #${PR_NUMBER} in repository ${REPO}.

Perform a thorough code review:
1. Get the PR details and diff
2. Analyze the code changes for quality, security, and best practices
3. Check if CI/CD checks passed
4. Look at the PR description and linked issues
5. Provide a structured review with findings by severity

If appropriate, prepare a review comment (but don't post unless --post-review is set).`;

} else if (healthFlag) {
  prompt = `Perform a comprehensive health check on repository ${REPO}.

Analyze:
1. Repository info (languages, activity, license)
2. Open pull requests — any stale PRs?
3. Open issues — any critical/high-priority unaddressed?
4. CI/CD workflow status — recent failures?
5. Branch hygiene — stale branches?
6. Look at README and key config files for completeness
7. Search for security anti-patterns (hardcoded credentials, TODO/FIXME/HACK comments)

Produce a "Repository Health Report" with a score (A-F) and actionable recommendations.`;

} else {
  prompt = `Analyze repository ${REPO} and provide a QA summary.

1. Get repo info and understand its purpose
2. List open PRs and issues
3. Check recent CI/CD runs
4. Review any open PRs for code quality
5. Provide a summary with key findings and recommendations`;
}

runAgent(prompt).catch((err) => {
  console.error("Agent error:", err.message);
  process.exit(1);
});

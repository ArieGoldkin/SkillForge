import type { Plugin } from "@opencode-ai/plugin";

interface Context {
  project: any;
  client: any;
  $: any;
  directory: string;
  worktree: string;
}

export const SkillForgeCorePlugin: Plugin = async (ctx: Context) => {
  const { project, client, $ } = ctx;

  // === CRITICAL: Git Branch Protection ===
  const gitBranchProtection = async (input: any, output: any) => {
    const { tool, args } = input;
    
    if (tool !== "bash") return;
    
    const command = args?.command || "";
    const branch = await $`git branch --show-current`.trim();
    
    if (
      (branch === "dev" || branch === "main") &&
      (command.startsWith("git commit") || command.startsWith("git push"))
    ) {
      client.toast({
        title: "🛑 Branch Protection",
        message: `Cannot commit directly to ${branch}`,
        duration: 5000
      });
      throw new Error(`Blocked: Cannot commit to ${branch}`);
    }
  };

  // === CRITICAL: Environment Protection ===
  const envProtection = async (input: any, output: any) => {
    const { tool, args } = input;
    
    if (tool !== "read") return;
    
    const filePath = args?.filePath || "";
    if (filePath.includes(".env") || filePath.includes(".key") || filePath.includes("secret")) {
      client.toast({
        title: "🔒 Env Protection",
        message: "Protected file access blocked",
        duration: 5000
      });
      throw new Error("Blocked: Cannot read protected files");
    }
  };

  // === HIGH: Pre-commit Validator ===
  const precommitValidator = async (input: any, output: any) => {
    const { tool } = input;
    
    if (tool !== "bash") return;
    
    // Check if this is a commit attempt
    const command = args?.command || "";
    if (command.includes("git commit") || command.includes("git push")) {
      console.log("[SkillForge] Pre-commit validation triggered");
      // In full implementation, run: ruff check, mypy, type checks
      // For now, just log the validation
    }
  };

  // === MEDIUM: Compaction Context Injection ===
  const compactionInjector = async (input: any, output: any) => {
    // Inject SkillForge-specific context during compaction
    output.context = output.context || [];
    output.context.push(`
## SkillForge Active Context
- Available agents: backend-architect, frontend-developer, llm-integrator, workflow-architect
- MCP servers: context7, langfuse
- Active hooks: git protection, env protection, pre-commit validation
- Project: ${project.name || 'unknown'}
      `);
  };

  // === LOW: Audit Logger ===
  const auditLogger = async (input: any, output: any) => {
    const { tool } = input;
    
    // Log critical tool executions for security audit
    if (["bash", "write", "edit", "read"].includes(tool)) {
      const logEntry = {
        timestamp: new Date().toISOString(),
        tool,
        result: JSON.stringify(output).substring(0, 200)
      };
      console.log(`[SkillForge Audit] ${JSON.stringify(logEntry)}`);
    }
  };

  // === Return All Hooks ===
  return {
    // === Pre-Tool Hooks ===
    "tool.execute.before": async (input, output) => {
      await gitBranchProtection(input, output);
      await envProtection(input, output);
      await precommitValidator(input, output);
    },
    
    // === Post-Tool Hooks ===
    "tool.execute.after": async (input, output) => {
      await auditLogger(input, output);
    },
    
    // === Session Hooks ===
    "session.created": async () => {
      console.log("[SkillForge] Session started");
    },
    
    "session.compacted": async (input, output) => {
      await compactionInjector(input, output);
    },
    
    "session.error": async (error: any) => {
      client.toast({
        title: "⚠️ SkillForge Error",
        message: error.message || "Unknown error occurred",
        duration: 5000
      });
    }
  };
};

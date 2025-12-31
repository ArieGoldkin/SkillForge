import type { Plugin } from "@opencode-ai/plugin";

interface Context {
  project: any;
  client: any;
  $: any;
  directory: string;
  worktree: string;
}

export const SkillForgePlugin: Plugin = async (ctx: Context) => {
  const { project, client, $ } = ctx;

  const gitBranchProtection = async (input: any, output: any) => {
    const { tool, args } = input;
    
    if (tool !== "bash") return;
    
    const command = args?.command || "";
    const branch = String(await $`git branch --show-current`).trim();
    
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

  const precommitValidator = async (input: any, output: any) => {
    const { tool } = input;
    
    if (tool !== "bash") return;
    
    if (tool === "bash") {
      const command = args?.command || "";
      if (command.includes("git commit") || command.includes("git push")) {
        console.log("[SkillForge] Pre-commit validation triggered");
      }
    }
  };

  const compactionInjector = async (input: any, output: any) => {
    const context = output.context || [];
    context.push(`
## SkillForge Active Context
- Available agents: backend-architect, frontend-developer, llm-integrator, workflow-architect
- MCP servers: context7, langfuse
- Active hooks: git protection, env protection, pre-commit validation
- Project: ${project.name || "unknown"}
- Using free models: ollama/llama3.1:8b
    `);
    output.context = context;
  };

  const auditLogger = async (input: any, output: any) => {
    const { tool } = input;
    
    if (["bash", "write", "edit", "read"].includes(tool)) {
      const logEntry = {
        timestamp: new Date().toISOString(),
        tool,
        result: JSON.stringify(output).substring(0, 200)
      };
      console.log(`[SkillForge Audit] ${JSON.stringify(logEntry)}`);
    }
  };

  return {
    "tool.execute.before": async (input: output) => {
      await gitBranchProtection(input, output);
      await envProtection(input, output);
      await precommitValidator(input, output);
    },
    
    "tool.execute.after": async (input: output) => {
      await auditLogger(input, output);
    },
    
    "session.created": async () => {
      console.log("[SkillForge] Session started");
    },
    
    "session.compacted": async (input: output) => {
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

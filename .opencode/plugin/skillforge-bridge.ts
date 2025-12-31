import type { Plugin, PluginInput, Hooks } from "@opencode-ai/plugin";
import { tool } from "@opencode-ai/plugin";

interface AgentConfig {
  name: string;
  display_name: string;
  model_preference?: {
    design?: string;
    simple_queries?: string;
  };
  capabilities: string[];
  tools: string[];
}

/**
 * SkillForge Bridge Plugin
 *
 * Bridges OpenCode's agent system with Claude's native Task tool.
 * Reads agent definitions from .claude/agent-registry.json and exposes
 * them as OpenCode tools.
 */
export const SkillForgeBridgePlugin: Plugin = async (input: PluginInput): Promise<Hooks> => {
  const { $, directory } = input;

  // Read agent registry from Claude's agent system
  const agentRegistryPath = `${directory}/.claude/agent-registry.json`;
  let registry: { agents?: Record<string, any>; description?: string } = { agents: {} };

  try {
    const registryData = await $`cat ${agentRegistryPath}`.text();
    registry = JSON.parse(registryData);
  } catch {
    console.warn("SkillForge Bridge: Could not load agent registry, using empty defaults");
  }

  // Build agent config map
  const agents = new Map<string, AgentConfig>();

  for (const [agentId, agentData] of Object.entries(registry.agents || {}) as [string, any][]) {
    agents.set(agentId, {
      name: agentId,
      display_name: agentData.display_name,
      model_preference: agentData.model_preference,
      capabilities: agentData.capabilities || [],
      tools: agentData.tools || [],
    });
  }

  console.log(`SkillForge Bridge: Loaded ${agents.size} agents from registry`);

  // Return plugin hooks
  return {
    tool: {
      "skillforge-list": tool({
        description: "List all available SkillForge agents",
        args: {},
        execute: async () => {
          const agentList = Array.from(agents.entries()).map(([id, config]) => ({
            id,
            name: config.display_name,
            capabilities: config.capabilities,
            tools: config.tools,
          }));

          return JSON.stringify(
            {
              success: true,
              agents: agentList,
            },
            null,
            2
          );
        },
      }),

      "skillforge-get": tool({
        description: "Get detailed agent configuration",
        args: {
          agent: tool.schema.string().describe("The agent ID to get details for"),
        },
        execute: async (args) => {
          const agentId = args.agent;
          if (!agents.has(agentId)) {
            return JSON.stringify({
              success: false,
              error: `Agent not found: ${agentId}`,
            });
          }

          const agent = agents.get(agentId)!;
          return JSON.stringify(
            {
              success: true,
              agent: {
                id: agentId,
                name: agent.display_name,
                model_preference: agent.model_preference,
                capabilities: agent.capabilities,
                tools: agent.tools,
              },
            },
            null,
            2
          );
        },
      }),

      "skillforge-spawn": tool({
        description: "Spawn a SkillForge agent with a task (returns spawn instructions)",
        args: {
          agent: tool.schema.string().describe("The agent ID to spawn"),
          task: tool.schema.string().describe("The task description for the agent"),
        },
        execute: async (args) => {
          const { agent: agentId, task } = args;

          if (!agents.has(agentId)) {
            return JSON.stringify({
              success: false,
              error: `Unknown agent: ${agentId}`,
            });
          }

          const agentConfig = agents.get(agentId)!;
          const displayName = agentConfig.display_name;
          const selectedModel =
            agentConfig.model_preference?.design || agentConfig.model_preference?.simple_queries;

          // Return spawn information (actual spawning handled by OpenCode agent system)
          return JSON.stringify(
            {
              success: true,
              spawn: {
                agentId,
                displayName,
                task,
                model: selectedModel,
                capabilities: agentConfig.capabilities,
                availableTools: agentConfig.tools,
                projectContext: registry.description,
              },
            },
            null,
            2
          );
        },
      }),
    },
  };
};

// Default export for OpenCode plugin loader
export default SkillForgeBridgePlugin;

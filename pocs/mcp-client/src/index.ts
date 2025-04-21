// openai sdk
import OpenAI from "openai";
import { ChatCompletionMessageParam } from "openai/resources/chat/completions";
// import { Anthropic } from "@anthropic-ai/sdk";
// import {
//   MessageParam,
//   Tool,
// } from "@anthropic-ai/sdk/resources/messages/messages.mjs";
import { Tool } from "@anthropic-ai/sdk/resources/messages/messages.mjs"; // Only for type compatibility, remove if not needed

// mcp sdk
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

import dotenv from "dotenv";
import readline from "readline/promises";
import { loadMcpServers, McpServerConfig } from "./mcps-loader";
import path from "path";

dotenv.config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
if (!OPENAI_API_KEY) {
  throw new Error("OPENAI_API_KEY is not set");
}

class MCPClient {
  public mcp: Client;
  public llm: OpenAI;
  private transport: StdioClientTransport | null = null;
  public tools: any[] = [];
  public name: string;
  public config: McpServerConfig;

  constructor(name: string, config: McpServerConfig) {
    this.llm = new OpenAI({
      apiKey: OPENAI_API_KEY,
    });
    this.mcp = new Client({ name: `mcp-client-cli-${name}`, version: "1.0.0" });
    this.name = name;
    this.config = config;
  }

  async connectToServer() {
    const serverScriptPath = this.config.path;
    const isJs = serverScriptPath.endsWith(".js");
    const isPy = serverScriptPath.endsWith(".py");
    if (!isJs && !isPy) {
      throw new Error("Server script must be a .js or .py file");
    }
    const command = isPy
      ? process.platform === "win32"
        ? "python"
        : "python3"
      : process.execPath;
    this.transport = new StdioClientTransport({
      command,
      args: [serverScriptPath, ...(this.config.args || [])],
    });
    await this.mcp.connect(this.transport, this.config.requestOptions);
    const toolsResult = await this.mcp.listTools();
    this.tools = toolsResult.tools.map((tool) => {
      return {
        type: "function",
        function: {
          name: tool.name,
          description: tool.description,
          parameters: tool.inputSchema,
        },
        __mcpServer: this.name, // Tag tool with server name
      };
    });
    console.log(
      `Connected to server [${this.name}] with tools:`,
      this.tools.map((t: any) => t.function.name)
    );
  }

  async cleanup() {
    await this.mcp.close();
  }
}

async function main() {
  const configPath = path.join(__dirname, "../mcps.json");
  const mcpConfigs = await loadMcpServers(configPath);
  const clients: Record<string, MCPClient> = {};
  const toolRegistry: Record<string, { client: MCPClient; tool: any }> = {};
  let allTools: any[] = [];
  for (const cfg of mcpConfigs) {
    const client = new MCPClient(cfg.name, cfg);
    await client.connectToServer();
    clients[cfg.name] = client;
    for (const tool of client.tools) {
      // If tool names overlap, last one wins (or handle as needed)
      toolRegistry[tool.function.name] = { client, tool };
      allTools.push(tool);
    }
  }

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  console.log("Available tools:", allTools.map((t) => t.function.name));
  while (true) {
    const query = await rl.question("\nQuery (or 'quit'): ");
    if (query.toLowerCase() === "quit") break;
    // LLM call with all tools
    const messages: ChatCompletionMessageParam[] = [
      { role: "user", content: query },
    ];
    const response = await clients[Object.keys(clients)[0]].llm.chat.completions.create({
      model: "gpt-4o",
      max_tokens: 1000,
      messages,
      tools: allTools,
    });
    const choice = response.choices[0];
    if (choice.message.tool_calls && choice.message.tool_calls.length > 0) {
      const toolCall = choice.message.tool_calls[0];
      const toolName = toolCall.function.name;
      let toolArgs = {};
      try {
        toolArgs = JSON.parse(toolCall.function.arguments);
      } catch (e) {
        console.log(`Error parsing tool arguments: ${e}`);
        continue;
      }
      // Route tool call to correct MCP server
      const reg = toolRegistry[toolName];
      if (!reg) {
        console.log(`Tool ${toolName} not found in registry.`);
        continue;
      }
      let toolResult;
      try {
        console.log(`making tool call: ${toolName} with args: ${JSON.stringify(toolArgs)} on server: ${reg.client.name}`);
        toolResult = await reg.client.mcp.callTool({ name: toolName, arguments: toolArgs });
      } catch (e) {
        console.log(`Error calling tool '${toolName}': ${e}`);
        continue;
      }
      // Send result back to LLM
      const followupMessages: ChatCompletionMessageParam[] = [
        ...messages,
        choice.message as ChatCompletionMessageParam,
        {
          role: "tool",
          tool_call_id: toolCall.id,
          content: JSON.stringify(toolResult),
        },
      ];
      const followup = await reg.client.llm.chat.completions.create({
        model: "gpt-4o",
        max_tokens: 1000,
        messages: followupMessages,
      });
      console.log("\n" + followup.choices[0].message.content);
    } else {
      // No tool call, just print model response
      console.log("\n" + choice.message.content);
    }
  }
  rl.close();
  for (const client of Object.values(clients)) {
    await client.cleanup();
  }
  process.exit(0);
}

main();
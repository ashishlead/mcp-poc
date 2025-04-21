// openai sdk
import OpenAI from "openai";
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

dotenv.config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
if (!OPENAI_API_KEY) {
  throw new Error("OPENAI_API_KEY is not set");
}

class MCPClient {
  public mcp: Client;
  private llm: OpenAI;
  private transport: StdioClientTransport | null = null;
  private tools: Tool[] = [];

  constructor() {
    this.llm = new OpenAI({
      apiKey: OPENAI_API_KEY,
    });
    this.mcp = new Client({ name: "mcp-client-cli", version: "1.0.0" });
  }

  // Connect to the MCP
  async connectToServer(serverScriptPath: string) {
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
      command, // python /path/to/server.py
      args: [serverScriptPath],
    });
    await this.mcp.connect(this.transport);

    // Register tools
    const toolsResult = await this.mcp.listTools();
    this.tools = toolsResult.tools.map((tool) => {
      return {
        name: tool.name,
        description: tool.description,
        input_schema: tool.inputSchema,
      };
    });

    console.log(
      "Connected to server with tools:",
      this.tools.map(({ name }) => name)
    );
  }

  // Process query
  async processQuery(query: string) {
    // Inline type for OpenAI chat messages
    const messages: Array<{ role: "user" | "assistant" | "system"; content: string }> = [
      {
        role: "user",
        content: query,
      },
    ];

    const response = await this.llm.chat.completions.create({
      model: "gpt-4o", // or another OpenAI model
      max_tokens: 1000,
      messages,
      // tools: this.tools, // OpenAI tool calling would need to be adapted
    });

    // For simplicity, just return the response text
    const finalText = [];
    if (response.choices && response.choices.length > 0) {
      finalText.push(response.choices[0].message.content);
    }
    return finalText.join("\n");
  }

  async chatLoop() {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    try {
      console.log("\nMCP Client Started!");
      console.log("Type your queries or 'quit' to exit.");

      while (true) {
        const message = await rl.question("\nQuery: ");
        if (message.toLowerCase() === "quit") {
          break;
        }
        const response = await this.processQuery(message);
        console.log("\n" + response);
      }
    } finally {
      rl.close();
    }
  }

  async cleanup() {
    await this.mcp.close();
  }
}

async function main() {
  if (process.argv.length < 3) {
    console.log("Usage: node index.ts <path_to_server_script>");
    return;
  }
  const mcpClient = new MCPClient();
  try {
    await mcpClient.connectToServer(process.argv[2]);

    // --- DEMO: Call extract_content tool from server ---
    const demoUrl = "https://example.com";
    console.log(`\n[Demo] Calling extract_content tool with url: ${demoUrl}`);
    try {
      const result = await mcpClient.mcp.callTool({
        name: "extract_content",
        arguments: { url: demoUrl },
      });
      console.log("[Demo] Extracted content result:", result);
    } catch (err) {
      console.error("[Demo] Error calling extract_content tool:", err);
    }
    // --- End DEMO ---

    await mcpClient.chatLoop();
  } finally {
    await mcpClient.cleanup();
    process.exit(0);
  }
}

main();
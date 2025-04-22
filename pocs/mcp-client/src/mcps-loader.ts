import fs from "fs/promises";

export type McpServerConfig = {
  name: string;
  path?: string;
  url?: string;
  args?: string[];
  requestOptions?: any;
};

export async function loadMcpServers(configPath: string): Promise<McpServerConfig[]> {
  const raw = await fs.readFile(configPath, "utf-8");
  return JSON.parse(raw);
}

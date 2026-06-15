import {
  definePluginEntry,
  type AnyAgentTool,
  type RX01PluginApi,
  type RX01PluginToolFactory,
} from "rx01/plugin-sdk/lobster";
import { createLobsterTool } from "./src/lobster-tool.js";

export default definePluginEntry({
  id: "lobster",
  name: "Lobster",
  description: "Optional local shell helper tools",
  register(api: RX01PluginApi) {
    api.registerTool(
      ((ctx) => {
        if (ctx.sandboxed) {
          return null;
        }
        return createLobsterTool(api) as AnyAgentTool;
      }) as RX01PluginToolFactory,
      { optional: true },
    );
  },
});

import type { Config, Context } from "@netlify/functions";
import { respond } from "./api.mts";

const default_response = "<br/><div style='text-align: center; width: 100%'>No skills detected.<br/>Did we miss a skill? Contribute ideas <a href='https://github.com/Longhorn-Riichi/InjusticeJudge/issues/10'>here</a>!</div>";

export const config: Config = {
  path: "/skill/:identifier/:player"
};

export default async (req: Request, context: Context) => {
  // unwrap the request
  const identifier = decodeURIComponent(context.params.identifier);
  let key = `${identifier}@skill`;
  return await respond(key, default_response, "skill");
}

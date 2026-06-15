import type { Config, Context } from "@netlify/functions";
import { respond } from "./api.mts";

const default_response = "<br/><div style='text-align: center; width: 100%'>No injustices detected.<br/>Did we miss an injustice? Contribute ideas <a href='https://github.com/Longhorn-Riichi/InjusticeJudge/issues/1'>here</a>!</div>";

export const config: Config = {
  path: "/:identifier/:player"
};

export default async (req: Request, context: Context) => {
  // unwrap the request
  const identifier = decodeURIComponent(context.params.identifier);
  const player = decodeURIComponent(context.params.player);
  let key = `${identifier}@${player}`;
  return await respond(key, default_response, "injustice");
}

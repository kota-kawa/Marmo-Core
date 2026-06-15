import type { Config, Context, Netlify } from "@netlify/functions";
import { Redis } from "@upstash/redis"
import fs from "node:fs";
import process from "node:process";
import { get_wisdom, to_table } from "./util.mts";

const redis = new Redis({
  url: Netlify.env.get("REDIS_ENDPOINT"),
  token: Netlify.env.get("UPSTASH_REDIS_REST_TOKEN"),
});

const default_stats = "<br/><div style='text-align: center; width: 100%'>No statistics logged so far.</div>";

export const config: Config = {
  path: ["/statistics"]
};

export default async (req: Request, context: Context) => {
  const header = "<span class='result-header'>Statistics across all submissions:</span><hr/>";
  const stats = await redis.hgetall("statistics");
  let statistics = default_stats;
  if (stats !== null) {
    console.log(stats);
    let stats_formatted = Object.keys(stats).reduce((acc, key) => {
        acc.push(`<td>${key}</td><td>${parseInt(stats[key], 10)}</td>`);
        return acc;
      }, []);
    stats_formatted.sort();
    statistics = to_table(stats_formatted);
  }
  let body = fs.readFileSync(process.cwd() + "/_site/statistics.html", "utf8")
               .replace(/<div class="statistics"><\/div>/, `<div class="statistics">${header}${statistics}</div>`)
               .replace(/<footer>/, `<footer><small>${get_wisdom()}</small><br/>`);

  return new Response(body, {
    "status": 302,
    "headers": {"Content-Type": "text/html"}
  });
}

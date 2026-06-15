#!/usr/bin/env bun
import { readFileSync, existsSync } from "fs";

interface Args {
  chart: string;
  focus: string;
}

function parseArgs(): Args {
  const args = process.argv.slice(2);
  const parsed: any = { focus: "general" };

  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace(/^--/, "");
    const value = args[i + 1];
    parsed[key] = value;
  }

  if (!parsed.chart) {
    console.log("Usage: bun interpret-chart.ts --chart <path.json> [--focus <career|marriage|general>]");
    process.exit(1);
  }

  return parsed as Args;
}

function analyzeChart(chartFile: string, focus: string) {
  if (!existsSync(chartFile)) {
    console.error(`❌ Chart file not found: ${chartFile}`);
    process.exit(1);
  }

  const chartData = readFileSync(chartFile, "utf-8");
  const data = JSON.parse(chartData);
  
  const p = data.person || {};
  const dob = p.birthDate || "N/A";
  
  console.log(`# Deep Astrological Analysis for ${p.name || "Native"}`);
  console.log(`**Focus:** ${focus.charAt(0).toUpperCase() + focus.slice(1)}`);
  console.log(`**Birth Details:** ${dob} UTC\n`);

  console.log(`## 1. Core Natal Promise (D1 Rasi Chart)`);
  const houses = data.d1Chart?.houses || [];
  const asc = houses.find((h: any) => h.number === 1);
  console.log(`**Ascendant (Lagna):** ${asc?.sign || "N/A"}`);
  
  const stelliums = houses.filter((h: any) => h.occupants?.filter((o:any)=>o).length >= 3);
  if (stelliums.length > 0) {
    console.log(`\n**Stellium Detected!** You have a powerful grouping of ${stelliums[0].occupants.filter((o:any)=>o).length} planets in House ${stelliums[0].number} (${stelliums[0].sign}). This house's themes dominate your life's karma and purpose.`);
  }

  console.log(`\n### Key Planetary Placements (Parashara)`);
  houses.forEach((h: any) => {
    const occs = h.occupants || [];
    occs.forEach((occ: any) => {
      if (occ) {
        let dig = occ.dignities?.dignity || "neutral";
        console.log(`- **${occ.celestialBody}**: House ${h.number} (${h.sign}) - ${Math.round(occ.signDegrees * 100) / 100}° [${dig.replace('_', ' ')}]`);
      }
    });
  });

  console.log(`\n## 2. KP System (Krishnamurthi Paddhati) Significators`);
  const kp = data.kp_data;
  if (!kp || kp.error) {
    console.log(`*KP Data requires Python 3.11+. Please upgrade to view sublords.*`);
  } else {
    console.log(`*In KP Astrology, the sublord (SL) of a house cusp determines the precise manifestation of that house's promise.*`);
    let houseSigs = "N/A";
    let planetSigs = "N/A";
    try {
      if (typeof kp.house_significators === 'string') {
        const hs = JSON.parse(kp.house_significators.replace(/'/g, '"'));
        const ps = JSON.parse(kp.planet_significators.replace(/'/g, '"'));
        
        console.log(`\n#### House Significators (Houses -> Planets)`);
        Object.keys(hs).slice(0, 12).forEach(h => {
          let levels = [];
          if (hs[h].A) levels.push(`A: ${hs[h].A.join(',')}`);
          if (hs[h].B) levels.push(`B: ${hs[h].B.join(',')}`);
          if (hs[h].C) levels.push(`C: ${hs[h].C.join(',')}`);
          if (hs[h].D) levels.push(`D: ${hs[h].D.join(',')}`);
          console.log(`- **House ${h}**: ${levels.join(' | ')}`);
        });

        console.log(`\n#### Planet Significators (Planets -> Houses)`);
        Object.keys(ps).forEach(p => {
          let levels = [];
          if (ps[p].A) levels.push(`A: ${ps[p].A.join(',')}`);
          if (ps[p].B) levels.push(`B: ${ps[p].B.join(',')}`);
          if (ps[p].C) levels.push(`C: ${ps[p].C.join(',')}`);
          if (ps[p].D) levels.push(`D: ${ps[p].D.join(',')}`);
          console.log(`- **${p}**: ${levels.join(' | ')}`);
        });
      }
    } catch(e) {
      console.log("```json\n" + JSON.stringify(kp.planet_significators, null, 2).substring(0, 400) + "...\n```");
    }
  }

  console.log(`\n## 3. Divisional Charts (Vargas)`);
  const div = data.divisionalCharts || {};
  if (div.d9) {
    console.log(`**Navamsa (D9):** Shows the inner reality, dharma, and marriage potential. Ascendant: ${div.d9.ascendant?.sign?.name || "N/A"}`);
    // extract d9 planets if needed
  }
  if (div.d10) {
    console.log(`**Dasamsa (D10):** Shows great detail regarding career, status, and authority.`);
  }

  console.log(`\n## 4. Vimshottari Dasha (Timing of Events)`);
  const dashas = data.dashas;
  if (dashas) {
    console.log(`- **Current Mahadasha (Major Period):** ${dashas.current_mahadasha || "N/A"}`);
    console.log(`- **Current Antardasha (Sub-Period):** ${dashas.current_antardasha || "N/A"}`);
  }

  console.log(`\n## 5. Shadbala (Planetary Strength)`);
  console.log(`Planets meeting minimum strength requirements:`);
  houses.forEach((h: any) => {
    const occs = h.occupants || [];
    occs.forEach((occ: any) => {
      if (occ && occ.shadbala && occ.shadbala.Shadbala) {
        let meets = occ.shadbala.Shadbala.MeetsRequirement === "Yes" ? "✅" : "❌";
        console.log(`- **${occ.celestialBody}**: ${occ.shadbala.Shadbala.Rupas} Rupas ${meets}`);
      }
    });
  });

  console.log(`\n## 6. Panchanga (Vedic Almanac)`);
  const panchanga = data.panchanga || {};
  console.log(`- **Tithi**: ${panchanga.tithi?.name || "N/A"} `);
  console.log(`- **Nakshatra**: ${panchanga.nakshatra?.name || "N/A"}`);
  console.log(`- **Yoga**: ${panchanga.yoga?.name || "N/A"}`);
  console.log(`- **Karana**: ${panchanga.karana?.name || "N/A"}`);
  console.log(`- **Vaara**: ${panchanga.vaara?.name || "N/A"}`);

  console.log(`\n---`);
  console.log(`*This comprehensive report was dynamically generated from your local chart JSON. It utilizes native TypeScript offline data parsing combining Parashara dignities, Shadbala vitality, and accurate KP significators.*`);
}

function main() {
  const args = parseArgs();
  analyzeChart(args.chart, args.focus);
}

main();

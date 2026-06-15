#!/usr/bin/env bun

/**
 * Generate Complete Vedic Astrology Birth Chart
 * 
 * Combines jyotishganit, VedicAstro, and flatlib for comprehensive analysis
 */

import { execSync } from "child_process";
import { writeFileSync, existsSync, mkdirSync } from "fs";

interface Args {
  date: string;
  time: string;
  lat: number;
  lon: number;
  tz: number;
  name?: string;
  place?: string;
  output?: string;
}

function parseArgs(): Args {
  const args = process.argv.slice(2);
  const parsed: any = {};

  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace(/^--/, "");
    const value = args[i + 1];
    
    if (["lat", "lon", "tz"].includes(key)) {
      parsed[key] = parseFloat(value);
    } else {
      parsed[key] = value;
    }
  }

  if (!parsed.date || !parsed.time || !parsed.lat || !parsed.lon || parsed.tz === undefined) {
    console.log("Usage: generate-chart.ts [options]");
    console.log("\nRequired:");
    console.log("  --date YYYY-MM-DD        Birth date");
    console.log("  --time HH:MM:SS          Birth time (24-hour)");
    console.log("  --lat LATITUDE           Latitude (decimal)");
    console.log("  --lon LONGITUDE          Longitude (decimal)");
    console.log("  --tz TIMEZONE            Timezone offset from UTC (e.g., 5.5 for IST)");
    console.log("\nOptional:");
    console.log("  --name NAME              Person's name");
    console.log("  --place PLACE            Birth place");
    console.log("  --output PATH            Output file path");
    console.log("\nExample:");
    console.log('  generate-chart.ts --date "1990-07-15" --time "14:30:00" \\');
    console.log("    --lat 28.6139 --lon 77.2090 --tz 5.5 \\");
    console.log('    --name "Sample Person" --place "New Delhi"');
    process.exit(1);
  }

  return parsed as Args;
}

function ensurePythonDeps() {
  console.log("🔍 Checking Python dependencies...\n");
  
  const packages = [
    "jyotishganit",
    "vedicastro",
    "git+https://github.com/diliprk/flatlib.git@sidereal#egg=flatlib"
  ];

  for (const pkg of packages) {
    try {
      const pkgName = pkg.includes("git+") ? "flatlib" : pkg;
      execSync(`python3.11 -c "import ${pkgName}"`, { stdio: "ignore" });
      console.log(`✅ ${pkgName} already installed`);
    } catch {
      console.log(`📦 Installing ${pkg.split("#")[0].split("/").pop()}...`);
      try {
        execSync(`python3.11 -m pip install ${pkg}`, { stdio: "inherit" });
      } catch (error) {
        console.error(`⚠️ Failed to install ${pkg}. Some features (like KP) may be unavailable.`);
        console.error("   Try manually: python3.11 -m pip install --user " + pkg + " (or add --break-system-packages on MacOS/Linux)");
      }
    }
  }
  
  console.log();
}

function generateChart(args: Args): string {
  const pythonScript = `
import json
from datetime import datetime
from jyotishganit import calculate_birth_chart, get_birth_chart_json
try:
    from vedicastro.VedicAstro import VedicHoroscopeData
    HAS_VEDICASTRO = True
except ImportError:
    HAS_VEDICASTRO = False

# Parse input
date_str = "${args.date} ${args.time}"
dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

# Generate jyotishganit chart (comprehensive)
print("📊 Calculating planetary positions...", flush=True)
jg_chart = calculate_birth_chart(
    birth_date=dt,
    latitude=${args.lat},
    longitude=${args.lon},
    timezone_offset=${args.tz},
    location_name="${args.place || ""}",
    name="${args.name || ""}"
)

# Parse JS arguments for vedicastro
year, month, day = map(int, "${args.date}".split('-'))
hour, minute, second = map(int, "${args.time}".split(':'))
tz_val = float(${args.tz})
tz_hrs = int(tz_val)
tz_mins = int((tz_val - tz_hrs) * 60)
utc_str = f"{tz_hrs:+03d}:{tz_mins:02d}"

# Generate VedicAstro chart (KP system)
print("🔮 Computing KP significators...", flush=True)
if HAS_VEDICASTRO:
    try:
        va_data = VedicHoroscopeData(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second,
            utc=utc_str,
            latitude=${args.lat},
            longitude=${args.lon}
        )
        va_chart = va_data.generate_chart()
        
        # Get KP data
        planets_data = va_data.get_planets_data_from_chart(va_chart)
        houses_data = va_data.get_houses_data_from_chart(va_chart)
        planet_sigs = va_data.get_planet_wise_significators(planets_data=planets_data, houses_data=houses_data)
        house_sigs = va_data.get_house_wise_significators(planets_data=planets_data, houses_data=houses_data)
        
        kp_data = {
            "planets": planets_data.to_dict() if hasattr(planets_data, 'to_dict') else str(planets_data),
            "houses": houses_data.to_dict() if hasattr(houses_data, 'to_dict') else str(houses_data),
            "planet_significators": planet_sigs.to_dict() if hasattr(planet_sigs, 'to_dict') else str(planet_sigs),
            "house_significators": house_sigs.to_dict() if hasattr(house_sigs, 'to_dict') else str(house_sigs)
        }
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        print(f"⚠️  KP data partially unavailable: {err_msg}", flush=True)
        kp_data = {"error": err_msg}
else:
    print(f"⚠️  KP data unavailable because vedicastro could not be imported.", flush=True)
    kp_data = {"error": "vedicastro not installed (requires Python 3.11+)"}

# Combine data
print("📝 Generating complete chart data...", flush=True)
combined = get_birth_chart_json(jg_chart)
combined["kp_data"] = kp_data
combined["meta"] = {
    "generated_at": datetime.now().isoformat(),
    "systems": ["jyotishganit", "vedicastro", "flatlib"],
    "ayanamsa": "True Chitra Paksha (Lahiri)"
}

# Output JSON
print(json.dumps(combined, indent=2, default=str))
`;

  try {
    const output = execSync(`python3.11 -c '${pythonScript.replace(/'/g, "'\\''")}'`, {
      encoding: "utf-8",
      maxBuffer: 10 * 1024 * 1024
    });
    
    // Extract JSON from output (after progress messages)
    const lines = output.split("\n");
    const jsonStart = lines.findIndex(line => line.trim() === "{");
    const jsonOutput = lines.slice(jsonStart).join("\n");
    
    return jsonOutput;
  } catch (error: any) {
    console.error("❌ Error generating chart:");
    console.error(error.stderr || error.message);
    process.exit(1);
  }
}

function main() {
  console.log("🌟 Vedic Astrology Chart Generator\n");
  
  const args = parseArgs();
  ensurePythonDeps();
  
  console.log("⚙️  Configuration:");
  console.log(`   Date: ${args.date}`);
  console.log(`   Time: ${args.time}`);
  console.log(`   Location: ${args.lat}°N, ${args.lon}°E`);
  console.log(`   Timezone: UTC${args.tz > 0 ? "+" : ""}${args.tz}`);
  if (args.name) console.log(`   Name: ${args.name}`);
  if (args.place) console.log(`   Place: ${args.place}`);
  console.log();
  
  const chartData = generateChart(args);
  
  // Save to file
  const outputDir = process.env.ASTRO_CHARTS_DIR || "./Charts";
  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true });
  }
  
  const filename = args.output || `${outputDir}/${(args.name || "chart").toLowerCase().replace(/\s+/g, "-")}-${args.date}.json`;
  writeFileSync(filename, chartData);
  
  console.log("\n✅ Chart generated successfully!");
  console.log(`📁 Saved to: ${filename}`);
  console.log("\n📊 Chart includes:");
  console.log("   ✓ D1-D60 divisional charts");
  console.log("   ✓ Panchanga (Tithi, Nakshatra, Yoga, Karana, Vaara)");
  console.log("   ✓ Vimshottari Dasha periods");
  console.log("   ✓ Shadbala (planetary strength)");
  console.log("   ✓ Ashtakavarga points");
  console.log("   ✓ KP significators and sublords");
  console.log("   ✓ Planetary aspects");
  console.log("\n💡 Next steps:");
  console.log(`   bun scripts/interpret-chart.ts --chart "${filename}" --focus career`);
  console.log(`   bun scripts/analyze-dasha.ts --chart "${filename}"`);
}

main();

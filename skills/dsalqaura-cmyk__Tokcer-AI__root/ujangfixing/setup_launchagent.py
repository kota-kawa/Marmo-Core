import os
import subprocess

def main():
    home = os.path.expanduser("~")
    launch_agents_dir = os.path.join(home, "Library", "LaunchAgents")
    
    if not os.path.exists(launch_agents_dir):
        os.makedirs(launch_agents_dir)
        
    plist_path = os.path.join(launch_agents_dir, "com.tokcer.autopost.plist")
    
    workspace = "/Users/iman.salqaura/Documents/Tokcer ai v1/tokcer-ai"
    script_path = os.path.join(workspace, "ujangfixing", "tokcer_viral_bot.py")
    stdout_log = os.path.join(workspace, "ujangfixing", "autopost_stdout.log")
    stderr_log = os.path.join(workspace, "ujangfixing", "autopost_stderr.log")
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tokcer.autopost</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{script_path}</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>WorkingDirectory</key>
    <string>{workspace}</string>
    <key>StandardOutPath</key>
    <string>{stdout_log}</string>
    <key>StandardErrorPath</key>
    <string>{stderr_log}</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
    
    with open(plist_path, "w", encoding="utf-8") as f:
        f.write(plist_content)
        
    print(f"Plist created at: {plist_path}")
    
    # Unload if already loaded
    subprocess.run(["launchctl", "unload", plist_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Load the agent
    res = subprocess.run(["launchctl", "load", plist_path], capture_output=True, text=True)
    if res.returncode == 0:
        print("Successfully loaded LaunchAgent! Autoposting is now 100% automated on macOS.")
    else:
        print(f"Failed to load LaunchAgent: {res.stderr}")

if __name__ == "__main__":
    main()

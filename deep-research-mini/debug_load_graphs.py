
import sys
import os
import traceback

# Add current directory to path so imports work as they do in the app
sys.path.append(os.getcwd())

print("--- Testing Imports ---")

print("\n1. Importing researcher...")
try:
    from src.agents.research import researcher
    print("✅ researcher imported successfully")
except Exception:
    print("❌ Failed to import researcher")
    traceback.print_exc()

print("\n2. Importing planner...")
try:
    from src.agents.planner import planner
    print("✅ planner imported successfully")
except Exception:
    print("❌ Failed to import planner")
    traceback.print_exc()

print("\n3. Importing supervisor...")
try:
    from src.agents.supervisor import supervisor
    print("✅ supervisor imported successfully")
except Exception:
    print("❌ Failed to import supervisor")
    traceback.print_exc()

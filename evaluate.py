import asyncio
import sys
import os
from main import process_request

# --- AUTO-SAVING CODE ---
class DualLogger:
    """This class acts as a 'splitter'."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()


async def run_evaluation():
    """Evaluates the performance of Agent."""

    print("🧪 STARTING AGENT EVALUATION...")
    print("="*50)
    
    # Test Case: Data input in Polish because the agent expects Polish context
    test_date = "27 września 2025"
    print(f"📅 Testing for date input: '{test_date}' (Polish Language Context)")
    
    results = await process_request(test_date)
    
    print("\n🧐 ANALYZING RESULTS:")
    print("-" * 20)
    
    if results is None:
        print("❌ ERROR: Result is None!")
        return

    if len(results) == 0:
        print("❌ ERROR: Agent returned 0 events.")
        return

    print(f"✅ SUCCESS: Received {len(results)} processed events.")
    
    first_item = results[0]
    required_keys = ["event_name", "menu_items", "facebook_post"]
    
    missing_keys = [key for key in required_keys if key not in first_item]
    
    if not missing_keys:
        print("✅ SUCCESS: JSON Structure is valid.")
        print(f"   Sample Menu Item (Local Language): {first_item.get('menu_items', [{}])[0].get('name')}")
    else:
        print(f"❌ ERROR: Missing keys in JSON: {missing_keys}")

    print("\n🎉 EVALUATION COMPLETED SUCCESSFULLY.")
    print("="*50)


if __name__ == "__main__":
    LOG_DIR = "evaluation_logs"
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        print(f"📁 Created directory: {LOG_DIR}")
    output_path = os.path.join(LOG_DIR, "evaluation_output.txt")
    
    # --- SAVE ACTIVATION ---
    sys.stdout = DualLogger(output_path)
    
    asyncio.run(run_evaluation())
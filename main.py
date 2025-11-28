import os
import json
import re
import asyncio
from dotenv import load_dotenv, find_dotenv
from datetime import datetime

from google.adk.runners import InMemoryRunner
from crowdbrew_agent.agent import root_agent
from crowdbrew_agent import database

# Load environment variables
_ = load_dotenv(find_dotenv())


def extract_json_from_response(response_object):
    """Extracts clean JSON from the raw agent response."""
    text = str(response_object)
    
    # 1. Try finding Markdown code block containing JSON
    matches = re.findall(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if matches:
        for json_candidate in reversed(matches):
            if '"output"' in json_candidate:
                return json_candidate
        return matches[-1]

    # 2. Try finding specific output key structure
    match_struct = re.search(r'(\{\s*"output":\s*\[.*?\]\s*\})', text, re.DOTALL)
    if match_struct: return match_struct.group(1)

    # 3. Fallback: Find the last JSON-like structure
    matches_raw = list(re.finditer(r'\{.*\}', text, re.DOTALL))
    if matches_raw:
        for match in reversed(matches_raw):
            candidate = match.group(0)
            if '"output"' in candidate: return candidate
                
    return text


async def process_request(user_date_query):
    print("💽 Initializing database...")
    database.init_db()

    print("\n🤖 CrowdBrew processes: {user_date_query}")

    runner = InMemoryRunner(agent=root_agent)
    response = await runner.run_debug(user_date_query)

    processed_items = []

    try:
        print("\n🔄 Parsing response to JSON...")
        json_str = extract_json_from_response(response)
        data = json.loads(json_str)
        print("✅ Success! JSON data received.")
        
        output_items = data.get("output", [])
        if not output_items:
             if isinstance(data, list): output_items = data
             elif isinstance(data, dict) and "facebook_post" in data: output_items = [data]

        # --- Write Loop ---
        for item in output_items:
            ai_date = item.get("event_date", datetime.now().strftime("%Y-%m-%d"))
            
            real_event_name = item.get("event_name", "Wydarzenie Nieznane")
            real_location = item.get("location", "Łódź (nieokreślone)")
            real_description = item.get("description", "Brak opisu")
            
            print(f"   ➕ [{ai_date}] Processing: {real_event_name}")

            # Save Event
            current_event_id = database.add_event(
                date=ai_date,
                name=real_event_name,
                location=real_location,
                description=real_description
            )
            
            # Save Marketing Content
            database.add_marketing_bundle(current_event_id, item)

            item['db_id'] = current_event_id
            processed_items.append(item)

        return processed_items
            
    except json.JSONDecodeError:
        print(f"\n❌ JSON parsing error. Agent returned:\n{json_str[:200]}...")
        return []
    except Exception as e:
        print(f"\n❌ Writing error: {e}")
        return []


if __name__ == "__main__":
    async def main_cli():
        print("💽 Terminal Mode")
        query = input("\n📅 Podaj zapytanie z datą: ")
        results = await process_request(query)
        print(f"\n✅ Completed. {len(results)} elements saved.")
    asyncio.run(main_cli())
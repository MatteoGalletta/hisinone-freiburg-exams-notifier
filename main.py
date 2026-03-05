import requests
from bs4 import BeautifulSoup
import sys
import re
import json
import os
from datetime import datetime
import time
import argparse

# --- Configuration ---
# Load credentials from config.json
def load_config():
    """Load configuration from config.json file."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.exists(config_path):
        print("❌ Error: config.json not found!")
        print("Please create config.json based on config.example.json")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing config.json: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading config.json: {e}")
        sys.exit(1)

# Load configuration
config = load_config()

LOGIN_URL = "https://campus.uni-freiburg.de/qisserver/rds?state=user&type=1&category=auth.login"
EXAM_PAGE_BASE = "https://campus.uni-freiburg.de/qisserver/pages/sul/examAssessment/personExamsReadonly.xhtml?_flowId=examsOverviewForPerson-flow"
CACHE_FILE = "exams_structure.json"

# Load credentials from config
USERNAME = config['hisinone']['username']
PASSWORD = config['hisinone']['password']

# Telegram Configuration
TELEGRAM_BOT_TOKEN = config['telegram']['bot_token']
TELEGRAM_CHAT_ID = config['telegram']['chat_id']

# Bot state
LAST_UPDATE_ID_FILE = "last_update_id.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Origin": "https://campus.uni-freiburg.de",
    "Referer": "https://campus.uni-freiburg.de/qisserver/pages/cs/sys/portal/hisinoneStartPage.faces",
    "Connection": "keep-alive"
}

def extract_exam_structure(html_content):
    """Extract the exam tree structure from HTML table and return as a list."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the main tree table
    # tree_table = soup.find('table', {'class': 'tableOverflowFix'})
    
    # if not tree_table:
    #     return None
    
    # Find all rows in the tree table (skip the header row)
    # rows = tree_table.find_all('tr')[1:]  # Skip header row
    rows = soup.find_all('tr')[1:]  # Skip header row
    
    if not rows:
        return None
    
    exams = []
    
    for row in rows:
        # Extract the level from the class attribute
        class_attr = row.get('class', [])
        level_match = re.search(r'treeTableCellLevel(\d+)', ' '.join(class_attr) if isinstance(class_attr, list) else class_attr)
        current_level = int(level_match.group(1)) if level_match else 1
        
        # Try to extract the exam/course name
        # Look for span with :defaulttext or :unDeftxt in the id
        name_span = row.find('span', {'id': re.compile(r'(defaulttext|unDeftxt)$')})
        if name_span:
            name = name_span.get_text(strip=True)
            # Only skip truly empty names
            if name:
                # Try to extract the grade
                grade_span = row.find('span', {'id': re.compile(r':grade$')})
                grade = grade_span.get_text(strip=True) if grade_span else None
                
                exams.append({
                    "level": current_level,
                    "name": name,
                    "grade": grade
                })
    
    return exams

def print_exam_structure(exams):
    """Print the exam structure in a readable format."""
    for exam in exams:
        indent = "  " * (exam["level"] - 1)
        name_with_grade = exam['name']
        if exam.get('grade'):
            name_with_grade = f"{exam['name']} (Grade: {exam['grade']})"
        print(f"{indent}├── {name_with_grade}")

def load_previous_structure():
    """Load the previous exam structure from cache file."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('exams', [])
        except:
            return None
    return None

def save_exam_structure(exams):
    """Save the current exam structure to cache file."""
    data = {
        'timestamp': datetime.now().isoformat(),
        'exams': exams
    }
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def compare_structures(old_exams, new_exams):
    """Compare old and new exam structures and return differences."""
    if old_exams is None:
        return None
    
    # Compare by name and grade
    old_items = {(e['name'], e.get('grade')) for e in old_exams}
    new_items = {(e['name'], e.get('grade')) for e in new_exams}
    
    old_names = {e['name'] for e in old_exams}
    new_names = {e['name'] for e in new_exams}
    
    added = new_names - old_names
    removed = old_names - new_names
    
    # Check for grade changes
    grade_changes = []
    for new_exam in new_exams:
        for old_exam in old_exams:
            if new_exam['name'] == old_exam['name']:
                new_grade = new_exam.get('grade')
                old_grade = old_exam.get('grade')
                if new_grade != old_grade and new_grade:
                    grade_changes.append({
                        'name': new_exam['name'],
                        'old_grade': old_grade,
                        'new_grade': new_grade
                    })
    
    if added or removed or grade_changes:
        return {'added': added, 'removed': removed, 'grade_changes': grade_changes}
    return None

def send_telegram_message(chat_id, message, parse_mode="Markdown"):
    """Send a generic Telegram message. Returns message_id on success, None on failure."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Telegram bot token not configured")
        return None
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result.get('result', {}).get('message_id')
        else:
            print(f"⚠️ Failed to send Telegram message: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"⚠️ Error sending Telegram message: {e}")
        return None

def edit_telegram_message(chat_id, message_id, new_text, parse_mode="Markdown"):
    """Edit an existing Telegram message."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Telegram bot token not configured")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": new_text
    }
    
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            print(f"⚠️ Failed to edit Telegram message: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"⚠️ Error editing Telegram message: {e}")
        return False

def send_telegram_notification(changes, current_exams):
    """Send Telegram notification with exam structure and changes."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    # Only send notification if there are changes
    if not changes:
        return
    
    # Build message with full structure in code block
    message = "📚 *HISinOne Exam Structure*\n\n```\n"
    
    # Add exam structure
    for exam in current_exams:
        indent = "  " * (exam["level"] - 1)
        name_with_grade = exam['name']
        if exam.get('grade'):
            name_with_grade = f"{exam['name']} (Grade: {exam['grade']})"
        message += f"{indent}├── {name_with_grade}\n"
    
    # Add changes
    message += "\n" + "="*40 + "\n"
    message += "⚠️ CHANGES DETECTED\n\n"
    
    if changes.get('added'):
        message += "🆕 New exams added:\n"
        for exam in sorted(changes['added']):
            message += f"  ✅ {exam}\n"
        message += "\n"
    
    if changes.get('removed'):
        message += "❌ Exams removed:\n"
        for exam in sorted(changes['removed']):
            message += f"  ❌ {exam}\n"
        message += "\n"
    
    if changes.get('grade_changes'):
        message += "📊 Grades changed:\n"
        for change in changes['grade_changes']:
            old_grade_str = change['old_grade'] if change['old_grade'] else 'no grade'
            message += f"  📝 {change['name']}:\n      {old_grade_str} → {change['new_grade']}\n"
        message += "\n"
    
    message += "```"
    
    send_telegram_message(TELEGRAM_CHAT_ID, message)

def get_telegram_updates(offset=None):
    """Get updates from Telegram bot."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {
        "timeout": 30,
        "allowed_updates": ["message"]
    }
    
    if offset:
        params["offset"] = offset
    
    try:
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️ Failed to get Telegram updates: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ Error getting Telegram updates: {e}")
        return None

def load_last_update_id():
    """Load the last processed update ID."""
    if os.path.exists(LAST_UPDATE_ID_FILE):
        try:
            with open(LAST_UPDATE_ID_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_update_id', 0)
        except:
            return 0
    return 0

def save_last_update_id(update_id):
    """Save the last processed update ID."""
    with open(LAST_UPDATE_ID_FILE, 'w') as f:
        json.dump({'last_update_id': update_id}, f)

def format_exam_tree_message(exams):
    """Format exam tree as a Telegram message (plain text, no Markdown)."""
    message = "📚 HISinOne Exam Structure\n\n"
    
    for exam in exams:
        indent = "  " * (exam["level"] - 1)
        name_with_grade = exam['name']
        if exam.get('grade'):
            name_with_grade = f"{exam['name']} (Grade: {exam['grade']})"
        message += f"{indent}├── {name_with_grade}\n"
    
    return message

def handle_telegram_command(command, chat_id, message_id):
    """Handle incoming Telegram commands."""
    print(f"📨 Received command: {command} from chat_id: {chat_id}")
    
    # Check if user is authorized
    if str(chat_id) != str(TELEGRAM_CHAT_ID):
        print(f"⚠️ Unauthorized access attempt from chat_id: {chat_id}")
        send_telegram_message(chat_id, "❌ You are not authorized to use this bot.")
        return
    
    if command == '/start':
        response = "👋 Welcome to HISinOne Exam Notifier!\n\nAvailable commands:\n/fetch - Get current exam structure\n/help - Show this help message"
        send_telegram_message(chat_id, response)
        
    elif command == '/help':
        response = "📚 *HISinOne Exam Notifier Commands*\n\n/fetch - Fetch and display current exam structure\n/help - Show this help message"
        send_telegram_message(chat_id, response)
        
    elif command == '/fetch':
        # Send initial "processing" message
        status_message_id = send_telegram_message(chat_id, "⏳ Fetching exam data from HISinOne...")
        
        # Login and fetch exam tree
        session = login_and_get_session()
        if not session:
            if status_message_id:
                edit_telegram_message(chat_id, status_message_id, "❌ Login failed. Please check the configuration.")
            else:
                send_telegram_message(chat_id, "❌ Login failed. Please check the configuration.")
            return
        
        current_exams = fetch_exam_tree(session)
        if not current_exams:
            if status_message_id:
                edit_telegram_message(chat_id, status_message_id, "❌ Failed to fetch exam tree. Please try again later.")
            else:
                send_telegram_message(chat_id, "❌ Failed to fetch exam tree. Please try again later.")
            return
        
        # Format and edit the message with the exam tree
        message = format_exam_tree_message(current_exams)
        if status_message_id:
            edit_telegram_message(chat_id, status_message_id, message, parse_mode=None)
            print("✅ Updated message with exam tree for user")
        else:
            send_telegram_message(chat_id, message, parse_mode=None)
            print("✅ Sent exam tree to user")
    else:
        response = f"❓ Unknown command: {command}\n\nUse /help to see available commands."
        send_telegram_message(chat_id, response)

def telegram_bot_loop():
    """Main loop for Telegram bot - listens for commands and performs periodic checks."""
    print("🤖 Starting Telegram bot...")
    print("Bot is now listening for commands and will check for exam updates every 10 minutes.")
    print("Press Ctrl+C to stop.\n")
    
    last_update_id = load_last_update_id()
    last_check_time = time.time()
    CHECK_INTERVAL = 600  # 10 minutes in seconds
    
    while True:
        try:
            # Check if it's time for periodic exam check
            current_time = time.time()
            if current_time - last_check_time >= CHECK_INTERVAL:
                print(f"\n⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running periodic exam check...")
                
                try:
                    # Login and fetch exam tree
                    session = login_and_get_session()
                    if session:
                        current_exams = fetch_exam_tree(session)
                        if current_exams:
                            # Load previous structure and compare
                            previous_exams = load_previous_structure()
                            changes = compare_structures(previous_exams, current_exams)
                            
                            # Save current structure
                            save_exam_structure(current_exams)
                            
                            # Notify about changes
                            print("\n📚 Exam Structure:")
                            print_exam_structure(current_exams)
                            notify_changes(changes)
                            
                            # Send Telegram notification if there are changes
                            send_telegram_notification(changes, current_exams)
                        else:
                            print("❌ Failed to fetch exam tree during periodic check")
                    else:
                        print("❌ Login failed during periodic check")
                except Exception as e:
                    print(f"⚠️ Error during periodic check: {e}")
                
                last_check_time = current_time
                print(f"✅ Periodic check complete. Next check in 10 minutes.\n")
            
            # Get updates from Telegram
            updates = get_telegram_updates(offset=last_update_id + 1 if last_update_id else None)
            
            if not updates or not updates.get('ok'):
                time.sleep(1)
                continue
            
            # Process each update
            for update in updates.get('result', []):
                update_id = update.get('update_id')
                
                if update_id:
                    last_update_id = max(last_update_id, update_id)
                    save_last_update_id(last_update_id)
                
                # Extract message
                message = update.get('message')
                if not message:
                    continue
                
                chat_id = message.get('chat', {}).get('id')
                message_id = message.get('message_id')
                text = message.get('text', '').strip()
                
                # Process commands
                if text.startswith('/'):
                    handle_telegram_command(text, chat_id, message_id)
            
        except KeyboardInterrupt:
            print("\n\n👋 Stopping bot...")
            break
        except Exception as e:
            print(f"⚠️ Error in bot loop: {e}")
            time.sleep(5)

def notify_changes(changes):
    """Notify user about changes in the exam structure."""
    if changes is None:
        print("✅ No changes detected.")
        return
    
    if changes['added']:
        print("\n🆕 New exams/courses added:")
        for exam in sorted(changes['added']):
            print(f"  + {exam}")
    
    if changes['removed']:
        print("\n❌ Exams/courses removed:")
        for exam in sorted(changes['removed']):
            print(f"  - {exam}")
    
    if changes.get('grade_changes'):
        print("\n📊 Grade changes detected:")
        for change in changes['grade_changes']:
            old_grade_str = change['old_grade'] if change['old_grade'] else 'no grade'
            print(f"  📝 {change['name']}: {old_grade_str} → {change['new_grade']}")

def print_list_tree(html_content):
    """Parse and print the exam tree from HTML table structure."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the main tree table
    tree_table = soup.find('table', {'class': 'tableOverflowFix'})
    
    if not tree_table:
        print("Empty tree. Could not find tree table in response.")
        return
    
    # Find all rows in the tree table (skip the header row)
    rows = tree_table.find_all('tr')[1:]  # Skip header row
    
    if not rows:
        print("Empty tree. This usually means the Flow Key (e1s1) has expired.")
        return
    
    previous_level = 0
    
    for row in rows:
        # Extract the level from the class attribute
        class_attr = row.get('class', [])
        level_match = re.search(r'treeTableCellLevel(\d+)', ' '.join(class_attr) if isinstance(class_attr, list) else class_attr)
        current_level = int(level_match.group(1)) if level_match else 1
        
        # Try to extract the exam/course name
        # Look for span with :defaulttext or :unDeftxt in the id
        name_span = row.find('span', {'id': re.compile(r'(defaulttext|unDeftxt)$')})
        if name_span:
            name = name_span.get_text(strip=True)
            # Only skip truly empty names
            if name:
                # Print with appropriate indentation
                indent = "  " * (current_level - 1)
                print(f"{indent}├── {name}")

def extract_flow_key(url):
    """Extract the flow execution key from a URL."""
    match = re.search(r'_flowExecutionKey=([^&]+)', url)
    return match.group(1) if match else None

def extract_view_state(html_content):
    """Extract the ViewState from the HTML response."""
    # Try to find in various formats
    patterns = [
        r'<input[^>]*name="javax\.faces\.ViewState"[^>]*value="([^"]*)"',
        r'javax\.faces\.ViewState["\']?\s*value\s*=\s*["\']?([^"\'&\s>]+)',
        r'javax\.faces\.ViewState["\']?\s*:\s*["\']?([^"\'&\s}]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html_content)
        if match:
            return match.group(1)
    
    # Fallback: try to find any ViewState value
    soup = BeautifulSoup(html_content, 'html.parser')
    view_state_input = soup.find('input', {'name': 'javax.faces.ViewState'})
    if view_state_input and view_state_input.get('value'):
        return view_state_input.get('value')
    
    # If still not found, return None and we'll use a fallback
    return None

def login_and_get_session():
    """Perform login and return authenticated session."""
    # 1. Start a Session
    session = requests.Session()
    session.headers.update(HEADERS)

    # 2. Perform Login
    login_payload = {
        "userInfo": "",
        "ajax-token": "76d6f982-a3d9-4701-9cb6-387b7ef703e3",
        "asdf": USERNAME,
        "fdsa": PASSWORD,
        "submit": ""
    }

    print(f"Attempting login for {USERNAME}...")
    response = session.post(LOGIN_URL, data=login_payload, allow_redirects=True)

    # 3. Verify Login Success
    if "Abmelden" in response.text or "Logout" in response.text:
        print("✅ Login successful!")
        return session
    else:
        print("❌ Login failed. Check credentials or ajax-token.")
        return None

def fetch_exam_tree(session):
    """Fetch and extract exam tree from HISinOne. Returns list of exams or None."""
    # 4. Get the Exam Page to Extract Flow Key and ViewState
    exam_page_res = session.get(EXAM_PAGE_BASE, allow_redirects=True)
    
    # Extract flow key from redirect URL
    flow_key = extract_flow_key(exam_page_res.url)
    
    if not flow_key:
        flow_key = "e1s1"
    
    # Extract ViewState from the initial page
    view_state = extract_view_state(exam_page_res.text)
    if not view_state:
        view_state = "e1s1"
    
    # 5. Expand the tree by clicking the "expand all" button
    data_url = f"{EXAM_PAGE_BASE}&_flowExecutionKey={flow_key}"
    
    # This specific request REQUIRES the AJAX header
    ajax_headers = {
        "Faces-Request": "partial/ajax",
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
    }
    
    # Expand all nodes
    expand_data = {
        "activePageElementId": "",
        "refreshButtonClickedId": "",
        "navigationPosition": "hisinoneMeinStudium,examAssessmentForStudent",
        "authenticity_token": "L5T1+UzUSWjBbD4vGko5zW4Ue7Ce9u/7JpU8sReoF9c=",
        "autoScroll": "",
        "examsReadonly:overviewAsTreeReadonly:collapsiblePanelCollapsedState": "",
        "examsReadonly:degreeProgramProgressForReportAsTree:collapsiblePanelCollapsedState": "",
        "examsReadonly:degreeProgramProgressForReportAsTree:studyHistoryTree:0:0:0:0:checkTick": "true",
        "examsReadonly:degreeProgramProgressForReportAsTree:studyHistoryTree:0:0:1:0:checkTick": "true",
        "examsReadonly_SUBMIT": "1",
        "javax.faces.ViewState": view_state,
        "javax.faces.behavior.event": "action",
        "javax.faces.partial.event": "click",
        "javax.faces.source": "examsReadonly:overviewAsTreeReadonly:tree:expandAll2",
        "javax.faces.partial.ajax": "true",
        "javax.faces.partial.execute": "examsReadonly:overviewAsTreeReadonly:tree:expandAll2",
        "javax.faces.partial.render": "examsReadonly:overviewAsTreeReadonly:tree:expandAll2 examsReadonly:overviewAsTreeReadonly:tree:ExamOverviewForPersonTreeReadonly examsReadonly:overviewAsTreeReadonly:tree:collapseAll2 examsReadonly:messages-infobox",
        "examsReadonly": "examsReadonly"
    }
    
    # Perform the expand all request
    exam_res = session.post(data_url, headers=ajax_headers, data=expand_data)
    
    # 7. Extract and Print Tree
    content = exam_res.text
    
    # Extract CDATA content if present
    if "<![CDATA[" in content:
        # There may be multiple CDATA sections; find the one with the main tree HTML
        cdata_sections = re.findall(r'<!\[CDATA\[(.*?)\]\]>', content, re.DOTALL)
        # The main tree is usually in the second update section
        html_part = cdata_sections[3] if len(cdata_sections) > 3 else cdata_sections[0] if cdata_sections else content
    else:
        html_part = content
    
    # Extract exam structure
    current_exams = extract_exam_structure(html_part)
    
    if not current_exams:
        print("Empty tree. This usually means the Flow Key (e1s1) has expired.")
        return None
    
    return current_exams

def run_workflow():
    """Original workflow: fetch, compare, save and notify."""
    session = login_and_get_session()
    if not session:
        return
    
    current_exams = fetch_exam_tree(session)
    if not current_exams:
        return
    
    # Load previous structure and compare
    previous_exams = load_previous_structure()
    changes = compare_structures(previous_exams, current_exams)
    
    # Save current structure
    save_exam_structure(current_exams)
    
    # Notify about changes
    print("\n📚 Exam Structure:")
    print_exam_structure(current_exams)
    
    # Always notify changes (or lack thereof)
    notify_changes(changes)
    
    # Send Telegram notification with full structure and changes
    send_telegram_notification(changes, current_exams)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="HISinOne Exam Checker - Monitor and fetch exam results from HISinOne",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='check',
        choices=['check', 'bot'],
        help='Command to execute: check (default) - check for changes, update cache and send notifications, bot - start Telegram bot to listen for commands'
    )
    
    args = parser.parse_args()
    
    if args.command == 'bot':
        telegram_bot_loop()
    else:
        run_workflow()
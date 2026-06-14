import os
import sys
import threading
from datetime import datetime, timedelta
from .database import (
    get_all_events, save_event, delete_event, 
    update_event, update_event_google_id,
    get_deleted_event_google_ids, remove_deleted_event_google_id
)

def safe_print(*args, **kwargs):
    try:
        sys.stdout.write(" ".join(map(str, args)) + "\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        try:
            cleaned_args = [str(arg).encode('ascii', 'replace').decode('ascii') for arg in args]
            sys.stdout.write(" ".join(cleaned_args) + "\n")
            sys.stdout.flush()
        except Exception:
            pass

print = safe_print


def load_dotenv():
    """Manually reads .env at the project root and populates os.environ."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(root_dir, '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, val = line.split('=', 1)
                            os.environ[key.strip()] = val.strip().strip("'").strip('"')
        except Exception as e:
            print(f"[Dotenv] Error reading .env file: {e}")

# Initial load
load_dotenv()

LAST_SYNC_ERROR = None

def get_calendar_id():
    """Gets the calendar ID from environment, reloading .env first."""
    load_dotenv()
    return os.environ.get("GOOGLE_CALENDAR_ID") or 'primary'

def get_calendar_service(credentials_path):
    """Initializes and returns the Google Calendar API service."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print("[Google Calendar] Missing packages: 'google-api-python-client' and 'google-auth'.")
        return None

    try:
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"[Google Calendar] Failed to build service: {e}")
        return None

def push_event_to_google(event_id, event_title, event_date, event_time, localizacao=None, recorrencia=None, service=None, db_path=None):
    """Pushes a single local event to Google Calendar."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    credentials_path = os.path.join(root_dir, 'credentials.json')
    
    if not os.path.exists(credentials_path):
        print("[Google Calendar] Sync skipped: 'credentials.json' not found at project root.")
        return None
        
    try:
        if not service:
            service = get_calendar_service(credentials_path)
            if not service:
                return None
                
        # Parse ISO date-time string
        start_datetime = f"{event_date}T{event_time}:00"
        
        # Default duration: 1 hour
        dt = datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M:%S")
        dt_end = dt + timedelta(hours=1)
        end_datetime = dt_end.strftime("%Y-%m-%dT%H:%M:%S")
        
        event_body = {
            'summary': event_title,
            'description': 'Agendado automaticamente pelo assistente de IA do DashFamília',
            'start': {
                'dateTime': start_datetime,
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': 'America/Sao_Paulo',
            },
        }
        
        if localizacao:
            event_body['location'] = localizacao
            
        if recorrencia:
            event_body['recurrence'] = [recorrencia]
            
        calendar_id = get_calendar_id()
        
        print(f"[Google Calendar] Pushing event '{event_title}' to Google Calendar ({calendar_id})...")
        created_event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        google_id = created_event.get('id')
        
        if google_id:
            update_event_google_id(event_id, google_id, db_path=db_path)
            print(f"[Google Calendar] Sync successful. Google Event ID: {google_id}")
            return google_id
            
    except Exception as e:
        print(f"[Google Calendar] Error pushing event: {e}")
    return None

def push_event_to_google_background(event_id, event_title, event_date, event_time, localizacao=None, recorrencia=None, db_path=None):
    t = threading.Thread(
        target=push_event_to_google,
        args=(event_id, event_title, event_date, event_time, localizacao, recorrencia, None, db_path)
    )
    t.daemon = True
    t.start()

def update_event_in_google(google_event_id, event_title, event_date, event_time, localizacao=None, recorrencia=None, service=None):
    """Updates an existing event in Google Calendar by its Google Event ID."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    credentials_path = os.path.join(root_dir, 'credentials.json')
    
    if not os.path.exists(credentials_path):
        print("[Google Calendar] Update skipped: 'credentials.json' not found at project root.")
        return False
        
    try:
        if not service:
            service = get_calendar_service(credentials_path)
            if not service:
                return False
                
        # Parse ISO date-time string
        start_datetime = f"{event_date}T{event_time}:00"
        
        # Default duration: 1 hour
        dt = datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M:%S")
        dt_end = dt + timedelta(hours=1)
        end_datetime = dt_end.strftime("%Y-%m-%dT%H:%M:%S")
        
        event_body = {
            'summary': event_title,
            'description': 'Agendado automaticamente pelo assistente de IA do DashFamília',
            'start': {
                'dateTime': start_datetime,
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': 'America/Sao_Paulo',
            },
        }
        
        if localizacao:
            event_body['location'] = localizacao
        else:
            event_body['location'] = ""
            
        if recorrencia:
            event_body['recurrence'] = [recorrencia]
        else:
            event_body['recurrence'] = []
            
        calendar_id = get_calendar_id()
        print(f"[Google Calendar] Updating event '{google_event_id}' in Google Calendar ({calendar_id})...")
        service.events().patch(calendarId=calendar_id, eventId=google_event_id, body=event_body).execute()
        print(f"[Google Calendar] Update successful for Google Event ID: {google_event_id}")
        return True
    except Exception as e:
        print(f"[Google Calendar] Error updating event: {e}")
        return False

def update_event_in_google_background(google_event_id, event_title, event_date, event_time, localizacao=None, recorrencia=None):
    """Runs the Google Calendar update in a background thread."""
    t = threading.Thread(
        target=update_event_in_google,
        args=(google_event_id, event_title, event_date, event_time, localizacao, recorrencia)
    )
    t.daemon = True
    t.start()

def delete_event_from_google(google_event_id, service=None):
    """Deletes an event from Google Calendar by its Google Event ID."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    credentials_path = os.path.join(root_dir, 'credentials.json')
    
    if not os.path.exists(credentials_path):
        print("[Google Calendar] Delete skipped: 'credentials.json' not found at project root.")
        return False
        
    try:
        if not service:
            service = get_calendar_service(credentials_path)
            if not service:
                return False
                
        calendar_id = get_calendar_id()
        print(f"[Google Calendar] Deleting event '{google_event_id}' from Google Calendar ({calendar_id})...")
        service.events().delete(calendarId=calendar_id, eventId=google_event_id).execute()
        print(f"[Google Calendar] Delete successful for Google Event ID: {google_event_id}")
        return True
    except Exception as e:
        print(f"[Google Calendar] Error deleting event: {e}")
        if "404" in str(e) or "notFound" in str(e) or "Not Found" in str(e):
            return "404"
        return False

def delete_event_from_google_background(google_event_id, db_path=None):
    """Runs the Google Calendar deletion in a background thread."""
    def run():
        res = delete_event_from_google(google_event_id)
        if res is True or res == "404":
            try:
                remove_deleted_event_google_id(google_event_id, db_path)
            except Exception as e:
                print(f"[Google Calendar] Error removing event from deleted queue: {e}")
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()


def sync_calendars(db_path=None):
    """Performs bidirectional calendar synchronization."""
    global LAST_SYNC_ERROR
    LAST_SYNC_ERROR = None
    
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    credentials_path = os.path.join(root_dir, 'credentials.json')
    
    if not os.path.exists(credentials_path):
        LAST_SYNC_ERROR = "Arquivo 'credentials.json' não encontrado na raiz do projeto. Por favor, configure as credenciais."
        print("[Google Calendar] Sync skipped: 'credentials.json' not found at project root.")
        return False
        
    service = get_calendar_service(credentials_path)
    if not service:
        LAST_SYNC_ERROR = "Não foi possível inicializar o serviço do Google Agenda. Verifique se as dependências (google-api-python-client, google-auth) estão instaladas e se o credentials.json está correto."
        print("[Google Calendar] Sync skipped: could not initialize calendar service.")
        return False
        
    calendar_id = get_calendar_id()
    
    try:
        # 0. Sync deletions from local eventos_deletados queue
        deleted_google_ids = get_deleted_event_google_ids(db_path)
        for g_id in deleted_google_ids:
            res_del = delete_event_from_google(g_id, service)
            if res_del is True or res_del == "404":
                remove_deleted_event_google_id(g_id, db_path)
                
        # 1. Push any local events that don't have a google_event_id yet
        local_events = get_all_events(db_path)
        for le in local_events:
            if not le.get('google_event_id'):
                g_id = push_event_to_google(
                    le['id'], le['titulo'], le['data'], le['hora'], 
                    localizacao=le.get('localizacao'), recorrencia=le.get('recorrencia'),
                    service=service, db_path=db_path
                )
                if g_id:
                    # Update our reference
                    le['google_event_id'] = g_id
                    
        # 2. Pull remote events from Google Calendar
        # Sync window: last 30 days to next 90 days
        now_dt = datetime.utcnow()
        time_min = (now_dt - timedelta(days=30)).isoformat() + 'Z'
        time_max = (now_dt + timedelta(days=90)).isoformat() + 'Z'
        
        print(f"[Google Calendar] Fetching remote events from {time_min} to {time_max}...")
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        google_events = events_result.get('items', [])
        active_google_ids = set()
        
        # Reload local events to have the latest state
        local_events = get_all_events(db_path)
        local_by_google_id = {e['google_event_id']: e for e in local_events if e['google_event_id']}
        
        # Fetch updated deleted list to avoid pulling newly deleted items
        deleted_google_ids = get_deleted_event_google_ids(db_path)
        
        for g_event in google_events:
            g_id = g_event.get('id')
            if g_id in deleted_google_ids:
                continue
            active_google_ids.add(g_id)
            
            summary = g_event.get('summary', 'Compromisso sem título')
            start = g_event.get('start', {})
            start_dt = start.get('dateTime')
            start_date = start.get('date')
            
            event_date = ""
            event_time = "00:00"
            
            if start_dt:
                parts = start_dt.split('T')
                event_date = parts[0]
                time_part = parts[1]
                event_time = time_part[:5]
            elif start_date:
                event_date = start_date
                event_time = "00:00"
                
            g_loc = g_event.get('location')
            g_rec_list = g_event.get('recurrence')
            g_rec = g_rec_list[0] if g_rec_list else None
                
            local_ev = local_by_google_id.get(g_id)
            if local_ev:
                # Existing event: check if details changed and update locally if so
                if (local_ev['titulo'] != summary or 
                    local_ev['data'] != event_date or 
                    local_ev['hora'] != event_time or
                    local_ev.get('localizacao') != g_loc or
                    local_ev.get('recorrencia') != g_rec):
                    print(f"[Google Calendar] Updating local event ID {local_ev['id']} to match Google...")
                    update_event(
                        event_id=local_ev['id'],
                        titulo=summary,
                        data=event_date,
                        hora=event_time,
                        responsavel=local_ev['responsavel'],
                        cor=local_ev['cor'],
                        categoria=local_ev['categoria'],
                        localizacao=g_loc,
                        recorrencia=g_rec,
                        db_path=db_path
                    )
            else:
                # Event doesn't exist by google_event_id.
                # Try matching by title, date, time for unlinked local events to avoid duplicates
                matched_local = None
                for le in local_events:
                    if (not le['google_event_id'] and
                        le['titulo'].lower().strip() == summary.lower().strip() and
                        le['data'] == event_date and
                        le['hora'] == event_time):
                        matched_local = le
                        break
                        
                if matched_local:
                    print(f"[Google Calendar] Matching local event ID {matched_local['id']} to Google ID {g_id}")
                    update_event_google_id(matched_local['id'], g_id, db_path)
                    update_event(
                        event_id=matched_local['id'],
                        titulo=summary,
                        data=event_date,
                        hora=event_time,
                        responsavel=matched_local['responsavel'],
                        cor=matched_local['cor'],
                        categoria=matched_local['categoria'],
                        localizacao=g_loc,
                        recorrencia=g_rec,
                        db_path=db_path
                    )
                else:
                    # New event from Google
                    print(f"[Google Calendar] Creating new local event '{summary}' from Google...")
                    save_event(
                        titulo=summary,
                        data=event_date,
                        hora=event_time,
                        responsavel='Google',
                        cor='#2ed573',  # Green color for Google Calendar events
                        categoria='Familiar',
                        google_event_id=g_id,
                        localizacao=g_loc,
                        recorrencia=g_rec,
                        db_path=db_path
                    )
                    
        # 3. Clean up deleted events in local SQLite
        sync_start_date = (now_dt - timedelta(days=30)).strftime("%Y-%m-%d")
        sync_end_date = (now_dt + timedelta(days=90)).strftime("%Y-%m-%d")
        
        for le in local_events:
            g_id = le.get('google_event_id')
            if g_id and g_id not in active_google_ids:
                # Only delete if it falls inside our sync window to prevent deleting historical events
                if sync_start_date <= le['data'] <= sync_end_date:
                    print(f"[Google Calendar] Deleting local event ID {le['id']} ('{le['titulo']}') because it was deleted on Google.")
                    delete_event(le['id'], db_path)
                    
        print("[Google Calendar] Bidirectional sync completed successfully.")
        return True
    except Exception as e:
        LAST_SYNC_ERROR = str(e)
        print(f"[Google Calendar] Error during sync: {e}")
        return False

def sync_calendars_background(db_path=None, callback=None):
    """Runs the bidirectional sync in a background thread."""
    def run():
        success = sync_calendars(db_path)
        if callback:
            callback(success)
            
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

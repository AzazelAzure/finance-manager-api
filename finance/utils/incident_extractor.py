import os
import datetime
import re

def extract_incident_logs(log_file_path, ticket_created_at, window_minutes=10, max_read_bytes=5 * 1024 * 1024):
    """
    Extracts the logs within the preceding window_minutes of ticket_created_at.
    Seeks from the tail of log_file_path up to max_read_bytes.
    Parses timestamps timezone-aware in UTC.
    """
    if not os.path.exists(log_file_path):
        return []

    file_size = os.path.getsize(log_file_path)
    start_pos = max(0, file_size - max_read_bytes)

    lines = []
    with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
        if start_pos > 0:
            f.seek(start_pos)
            # Discard the first line as it may be partial
            f.readline()
        lines = f.readlines()

    ticket_utc = ticket_created_at.astimezone(datetime.timezone.utc)
    start_time = ticket_utc - datetime.timedelta(minutes=window_minutes)
    end_time = ticket_utc

    log_entries = []
    current_entry = None
    timestamp_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')

    for line in lines:
        match = timestamp_pattern.match(line)
        if match:
            if current_entry:
                log_entries.append(current_entry)
            timestamp_str = match.group(1)
            try:
                dt = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                dt = None
            current_entry = {
                'timestamp': dt,
                'lines': [line]
            }
        else:
            if current_entry:
                current_entry['lines'].append(line)

    if current_entry:
        log_entries.append(current_entry)

    extracted_lines = []
    for entry in log_entries:
        dt = entry['timestamp']
        if dt is None:
            continue
        if start_time <= dt <= end_time:
            extracted_lines.extend(entry['lines'])

    return extracted_lines

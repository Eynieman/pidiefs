import os
import sys
import urllib.request
import urllib.parse


def send_whatsapp_notification():
    api_key = os.environ.get("CALLMEBOT_API_KEY")
    to_number = os.environ.get("WHATSAPP_TO_NUMBER")

    commit_author = os.environ.get("COMMIT_AUTHOR", "Desconocido")
    commit_message = os.environ.get("COMMIT_MESSAGE", "Sin mensaje")
    branch = os.environ.get("BRANCH", "unknown")
    commit_url = os.environ.get("COMMIT_URL", "")
    changed_files = os.environ.get("CHANGED_FILES", "")
    event_type = os.environ.get("EVENT_TYPE", "push")

    if not all([api_key, to_number]):
        print("Error: Faltan CALLMEBOT_API_KEY o WHATSAPP_TO_NUMBER")
        sys.exit(1)

    if event_type == "pull_request":
        header = "\U0001f500 Pull Request en pageyn"
    else:
        header = "\U0001f4e6 Push a pageyn"

    lines = [
        header,
        f"\U0001f464 {commit_author}",
        f"\U0001f4dd \"{commit_message}\"",
        f"\U0001f33f {branch}",
    ]

    if changed_files:
        file_list = [f.strip() for f in changed_files.split(",") if f.strip()]
        lines.append(f"\U0001f4c2 Archivos ({len(file_list)}):")
        for f in file_list:
            lines.append(f"  \u2022 {f}")

    if commit_url:
        lines.append(f"\U0001f517 {commit_url}")

    message_body = "\n".join(lines)

    url = "https://api.callmebot.com/whatsapp.php"
    params = urllib.parse.urlencode(
        {"phone": to_number, "text": message_body, "apikey": api_key},
        doseq=True,
    )
    full_url = f"{url}?{params}"

    try:
        resp = urllib.request.urlopen(full_url, timeout=10)
        print(f"Mensaje enviado. Status: {resp.status}")
    except urllib.error.HTTPError as e:
        print(f"Error HTTP: {e.code} - {e.read().decode()}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error de conexion: {e.reason}")
        sys.exit(1)


if __name__ == "__main__":
    send_whatsapp_notification()

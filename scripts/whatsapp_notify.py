import os
import sys
from twilio.rest import Client


def send_whatsapp_notification():
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    to_number = os.environ.get("WHATSAPP_TO_NUMBER")
    from_number = "whatsapp:+14155238886"

    commit_author = os.environ.get("COMMIT_AUTHOR", "Desconocido")
    commit_message = os.environ.get("COMMIT_MESSAGE", "Sin mensaje")
    branch = os.environ.get("BRANCH", "unknown")
    commit_url = os.environ.get("COMMIT_URL", "")
    changed_files = os.environ.get("CHANGED_FILES", "")
    event_type = os.environ.get("EVENT_TYPE", "push")

    if not all([account_sid, auth_token, to_number]):
        print("Error: Faltan variables de entorno TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN o WHATSAPP_TO_NUMBER")
        sys.exit(1)

    if event_type == "pull_request":
        header = f"🔀 Pull Request en pidiefs"
    else:
        header = f"📬 Push en pidiefs"

    lines = [
        header,
        "",
        f"👤 Autor: {commit_author}",
        f"📝 Mensaje: {commit_message}",
        f"🌿 Branch: {branch}",
    ]

    if changed_files:
        file_list = [f.strip() for f in changed_files.split(",") if f.strip()]
        lines.append(f"📂 Archivos modificados ({len(file_list)}):")
        for f in file_list:
            lines.append(f"  • {f}")

    if commit_url:
        lines.append(f"🔗 {commit_url}")

    message_body = "\n".join(lines)

    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=message_body,
        from_=from_number,
        to=f"whatsapp:{to_number}",
    )

    print(f"Mensaje enviado. SID: {message.sid}")


if __name__ == "__main__":
    send_whatsapp_notification()

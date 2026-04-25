import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_confirmation_email(to_email: str, token: str):
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    from_name = os.getenv("GMAIL_FROM_NAME", "Login App")
    app_url = os.getenv("APP_URL", "http://localhost:8000")

    confirmation_link = f"{app_url}/api/users/confirm/{token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Confirma tu correo electronico"
    msg["From"] = f"{from_name} <{gmail_user}>"
    msg["To"] = to_email

    html = _build_confirmation_html(confirmation_link)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_email, msg.as_string())
        print(f"Correo de confirmacion enviado a {to_email}")
    except Exception as e:
        print(f"Error enviando correo de confirmacion: {e}")


def _build_confirmation_html(confirmation_link: str) -> str:
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white;
                    padding: 30px; border-radius: 8px;">
            <h2 style="color: #333;">Bienvenido!</h2>
            <p style="color: #555;">
                Gracias por registrarte. Confirma tu correo haciendo clic en el boton:
            </p>
            <a href="{confirmation_link}"
               style="display: inline-block; padding: 12px 24px;
                      background-color: #4CAF50; color: white;
                      text-decoration: none; border-radius: 4px; margin: 10px 0;">
                Confirmar Email
            </a>
            <p style="color: #999; font-size: 12px;">
                Si no creaste esta cuenta, ignora este correo.
            </p>
        </div>
    </body>
    </html>
    """

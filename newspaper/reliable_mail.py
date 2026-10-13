"""Bounded pre-DATA retry, durable acceptance, and honest uncertain outcomes."""
import datetime as dt
import hashlib
import smtplib
import ssl
import time
from email.utils import format_datetime

class AcceptanceUncertain(RuntimeError): pass

def deliver(message, sender, password, host, port, journal,
            factory=None, pause=time.sleep):
    factory = factory or smtplib.SMTP_SSL
    if journal.decision() == "accepted": return "already_accepted"
    if journal.state.get("status") in {"sending", "uncertain"}:
        raise AcceptanceUncertain("Inspect previous attempt before another transmission")
    # Deterministic ID aids investigation. It is not an SMTP idempotency guarantee.
    address_hash = hashlib.sha256(str(message["To"]).encode()).hexdigest()[:16]
    message["Message-ID"] = f"<newspaper.{journal.day}.{address_hash}@{sender.split('@')[-1]}>"
    message["Date"] = format_datetime(dt.datetime.now(dt.timezone.utc))
    identity = str(message["Message-ID"])
    digest = hashlib.sha256(message.as_bytes()).hexdigest()
    for attempt in range(1,4):
        smtp = None
        entered_data = False
        try:
            smtp = factory(host,port,timeout=30,context=ssl.create_default_context())
            smtp.login(sender,password)
            # Persist before DATA: losing the response requires review, not duplicates.
            journal.write(status="sending", message_id_hash=hashlib.sha256(identity.encode()).hexdigest(),
                          message_sha256=digest, smtp_attempt=attempt)
            entered_data = True
            refused = smtp.send_message(message)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)
            # Never let QUIT failure turn accepted mail into a failed delivery.
            journal.write(status="accepted", accepted_at=dt.datetime.now(dt.timezone.utc).isoformat())
            return "accepted"
        except (smtplib.SMTPAuthenticationError, smtplib.SMTPRecipientsRefused,
                smtplib.SMTPSenderRefused, smtplib.SMTPDataError) as exc:
            journal.write(status="failed_safe", error_type=type(exc).__name__)
            raise RuntimeError("SMTP rejected transaction: "+type(exc).__name__) from None
        except Exception as exc:
            if entered_data:
                # If receipt persistence failed after SMTP acceptance, prior
                # durable state stays 'sending' and blocks automated duplicate.
                try: journal.write(status="uncertain",error_type=type(exc).__name__)
                except Exception: pass
                raise AcceptanceUncertain("SMTP outcome or acceptance persistence needs review") from None
            journal.write(status="failed_safe",error_type=type(exc).__name__)
            if attempt == 3: raise RuntimeError("SMTP connection failed after three attempts") from None
            pause(5 * attempt)
        finally:
            if smtp is not None:
                try: smtp.quit()
                except Exception:
                    try: smtp.close()
                    except Exception: pass

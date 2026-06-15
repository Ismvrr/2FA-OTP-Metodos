import secrets
import string


def generate_otp(length: int = 6, otp_type: str = "numeric") -> str:
    if otp_type == "alphanumeric":
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    return ''.join(secrets.choice(string.digits) for _ in range(length))

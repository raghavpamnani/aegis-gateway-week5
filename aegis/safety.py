import re


def check_question(text):
    """Small explicit local-demo boundaries, not a comprehensive injection detector."""
    if re.search(r"\bsk-[A-Za-z0-9_-]{16,}|\b(?:password|api[_ -]?key)\s*[:=]\s*\S+", text, re.I):
        return "Do not enter credentials. Use the fictional support cases."
    if re.search(
        r"ignore (?:all |previous |prior )?(?:instructions|rules)|reveal (?:the |your )?system prompt",
        text,
        re.I,
    ):
        return (
            "Instruction override request rejected. Ask a support question grounded in the fictional corpus."
        )
    return None

def sanitize_err(e: Exception, max_len=1000) -> str:
    return str(e).strip().replace("\n", " ")[:max_len]

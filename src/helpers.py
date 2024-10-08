def sanitize_err(e: Exception, max_len=1000) -> str:
    # sanitize error message (take only first line and limit length)
    return str(e).split("\n")[0][:max_len]

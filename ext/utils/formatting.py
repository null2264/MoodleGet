def pformat(text):
    text = text.lower()
    text = text.replace(" ", "_")
    for s in "%()":
        text = text.replace(s, "")
    return text

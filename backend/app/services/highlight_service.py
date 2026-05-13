def build_highlight_state(
    expected_words: list[str],
    statuses: list[str],
    current_index: int,
) -> dict:
    items = []
    for index, word in enumerate(expected_words):
        status = statuses[index] if index < len(statuses) else "unread"
        if index == current_index and status == "unread":
            status = "current"
        items.append({"word": word, "status": status})

    progress = 0.0
    if expected_words:
        progress = round((current_index / len(expected_words)) * 100, 1)

    return {
        "words": items,
        "current_index": current_index,
        "progress": progress,
    }

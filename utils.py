import telebot


def create_buttons(elements: list, width: int):
    """
    Creates buttons with the given elements in the list with the given width and returns a markup.
    """
    markup = telebot.types.ReplyKeyboardMarkup(row_width=width, resize_keyboard=True)

    if width > 1 and len(elements) > width:
        for i in range(0, len(elements), width):
            buttons = [telebot.types.KeyboardButton(e) for e in elements[i:i + width] if e]
            markup.add(*buttons)
    else:
        for element in elements:
            if element:
                markup.add(telebot.types.KeyboardButton(element))

    return markup
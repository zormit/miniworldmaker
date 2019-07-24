from miniworldmaker.tokens import text_token


class NumberToken(text_token.TextToken):
    """
    A number token shows a Number.

    You have to set the size of the token with self.size() manually so that
    the complete text can be seen.

    Args:
        position: Top-Left position of Number
        number: The initial number
        font-size: The size of the font (default: 80)
        color: The color of the font (default: white)

    Examples:
        >>> self.score = NumberToken(position = (0, 0), number=0)
        Sets a new NumberToken to display the score.
    """

    def __init__(self, position, number = 0, font_size= 80, color=(255, 255, 255, 255)):
        super().__init__(position, str(number), font_size, color)
        self.number = number

    def inc(self):
        """
        Increases the number by one
        """
        self.number += 1
        self.set_text(str(self.number))

    def set_number(self, number):
        """
        Sets the number

        Args:
            number: The number which should be displayed
        """
        self.number = number
        self.set_text(str(self.number))

    def get_number(self) -> int:
        """
        Returns the current number

        Returns: The current number

        """
        self.costume.call_action("text changed")
        return int(self.costume.text)

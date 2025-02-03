from chirp.common.printing import cprint

class CustomInput():
    """
    Defines a callable object that works similarly to input.
    Allows specification of different input methods for
    command line and web interface
    """

    def __init__(self):
        self.input = self.default_input

    def __call__(self, choices: list[str] = None, allow_custom: bool = True):
        if not choices:
            choices = ["yes", "no"]
            allow_custom = False
        index = 1
        for choice in choices:
            cprint(f"{index}. {choice}")
            index += 1
        if allow_custom:
            cprint(f"{index}. [custom input]")
        return self.input()
    
    def default_input(self):
        return input()



cinput = CustomInput()

if __name__ == "__main__":
    cprint( cinput(["hey", "HI"], False))
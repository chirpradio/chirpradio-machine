from chirp.common.printing import cprint
import contextlib

class CustomInput():
    """
    Defines a callable object that works similarly to input.
    Allows specification of different input methods for
    the command line interface and web interface
    """

    def __init__(self):
        self.input = self.default_input

    def __call__(self, prompt: str, choices: list[str], allow_custom: bool = True):
        return self.input(prompt, choices, allow_custom)
    
    def default_input(self, prompt, choices: list[str], allow_custom: bool) -> str:
        """
        Prints the prompt, then the list of choices enumerated
        User types the number assigned to a choice to select it
        If allow_custon, user is allowed to give custom input
        Returns an item from choices, or custom input if given
        """
        cprint(prompt)

        index = 1
        for choice in choices:
            cprint(f"{index}. {choice}")
            index += 1
        if allow_custom:
            cprint(f"{index}. [custom input]")

        while True:
            inp = input()
            if inp.isdigit():
                inp = int(inp)
                if inp in range(1, len(choices) + 1):
                    cprint(f"Continuing with \'{choices[inp-1]}\'")
                    return choices[inp - 1]
                elif allow_custom and inp == len(choices) + 1:
                    ci = input("[type custom input here]: ")
                    cprint(f"Continuing with \'{ci}\'")
                    return ci
            cprint(f"Please type a number between 1 and {len(choices) + allow_custom}")

    @contextlib.contextmanager
    def use_input_function(self, func):
        self.input = func
        yield
        self.input = self.default_input


cinput = CustomInput()

def test():
    #choice = cinput("What topping do you want on your pizza?", ["Cheese", "Pepperoni", "Pineapple"], True)
    choice = cinput("Saw %d errors. Continue anyways?" % 3, ["Yes", "No"], False)
    cprint("You chose: " + choice)

if __name__ == "__main__":
    test()

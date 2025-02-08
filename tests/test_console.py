from covgen.console import console as console


def examplestr(s: str) -> str:
    return f'[bold red]{s} example: [black on white underline]Nigga!'


def example():
    console.rule(examplestr("Rule"))
    console.log(examplestr('Log'))
    console.print(examplestr('Print'))


if __name__ == "__main__":
    example()


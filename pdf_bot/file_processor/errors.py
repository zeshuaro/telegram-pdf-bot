class DuplicateClassError(Exception):
    def __init__(self, cls_name: str, *args: object) -> None:
        msg = f"Class has already been initialised: {cls_name}"
        super().__init__(msg, *args)

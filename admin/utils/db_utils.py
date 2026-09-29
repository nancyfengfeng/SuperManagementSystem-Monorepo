def apply_if_changed(obj, field, new_value):
    if getattr(obj, field) != new_value:
        setattr(obj, field, new_value)
        return True
    return False
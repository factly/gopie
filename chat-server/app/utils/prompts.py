def escape_value(val):
    if "," in str(val):
        return f'"{val}"'
    return str(val)

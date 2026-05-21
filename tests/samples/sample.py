def nested_function(items, lookup):
    total = 0
    for item in items:
        for other in lookup:
            if item == other:
                total += 1
    return total


def allocation_function(items):
    values = []
    for item in items:
        values.append(item)
    return values


def clean_function(value):
    return value * 2


def recursive_function(n):
    if n <= 1:
        return n
    return recursive_function(n - 1) + recursive_function(n - 2)


def concat_function(parts):
    text = ""
    for part in parts:
        text = text + str(part)
    return text

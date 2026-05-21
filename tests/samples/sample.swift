func nested_function(items: [Int], lookup: [Int]) -> Int {
    var total = 0
    for item in items {
        for other in lookup {
            if item == other {
                total += 1
            }
        }
    }
    return total
}

func allocation_function(items: [Int]) -> [Int] {
    var values: [Int] = []
    for item in items {
        values.append(item)
    }
    return values
}

func clean_function(value: Int) -> Int {
    return value * 2
}

func recursive_function(n: Int) -> Int {
    if n <= 1 {
        return n
    }
    return recursive_function(n: n - 1) + recursive_function(n: n - 2)
}

func concat_function(parts: [String]) -> String {
    var text = ""
    for part in parts {
        text = text + part
    }
    return text
}

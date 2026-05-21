fun nested_function(items: List<Int>, lookup: List<Int>): Int {
    var total = 0
    for (item in items) {
        for (other in lookup) {
            if (item == other) {
                total += 1
            }
        }
    }
    return total
}

fun allocation_function(items: List<Int>): MutableList<Int> {
    val values = mutableListOf<Int>()
    for (item in items) {
        values.add(item)
    }
    return values
}

fun clean_function(value: Int): Int {
    return value * 2
}

fun recursive_function(n: Int): Int {
    if (n <= 1) {
        return n
    }
    return recursive_function(n - 1) + recursive_function(n - 2)
}

fun concat_function(parts: List<String>): String {
    var text = ""
    for (part in parts) {
        text = text + part
    }
    return text
}

fn nested_function(items: Vec<i32>, lookup: Vec<i32>) -> i32 {
    let mut total = 0;
    for item in items {
        for other in &lookup {
            if item == *other {
                total += 1;
            }
        }
    }
    total
}

fn allocation_function(items: Vec<i32>) -> Vec<i32> {
    let mut values = Vec::new();
    for item in items {
        values.push(item);
    }
    values
}

fn clean_function(value: i32) -> i32 {
    value * 2
}

fn recursive_function(n: i32) -> i32 {
    if n <= 1 {
        return n;
    }
    recursive_function(n - 1) + recursive_function(n - 2)
}

fn concat_function(parts: Vec<&str>) -> String {
    let mut text = String::new();
    for part in parts {
        text = text + part;
    }
    text
}

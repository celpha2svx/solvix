int nested_function(int items[], int lookup[], int size) {
    int total = 0;
    for (int i = 0; i < size; i++) {
        for (int j = 0; j < size; j++) {
            if (items[i] == lookup[j]) {
                total += 1;
            }
        }
    }
    return total;
}

int allocation_function(int size) {
    int total = 0;
    for (int i = 0; i < size; i++) {
        auto value = new int(i);
        total += *value;
    }
    return total;
}

int clean_function(int value) {
    return value * 2;
}

int recursive_function(int n) {
    if (n <= 1) {
        return n;
    }
    return recursive_function(n - 1) + recursive_function(n - 2);
}

std::string concat_function(std::vector<std::string> parts) {
    std::string text = "";
    for (auto part : parts) {
        text = text + part;
    }
    return text;
}

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
        int *value = malloc(sizeof(int));
        total += i;
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

char *concat_function(char *parts[], int size) {
    char *text = "";
    for (int i = 0; i < size; i++) {
        strcat(text, parts[i]);
    }
    return text;
}

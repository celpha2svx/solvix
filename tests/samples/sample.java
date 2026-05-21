class Sample {
    int nested_function(int[] items, int[] lookup) {
        int total = 0;
        for (int item : items) {
            for (int other : lookup) {
                if (item == other) {
                    total += 1;
                }
            }
        }
        return total;
    }

    int[] allocation_function(int[] items) {
        java.util.ArrayList<Integer> values = new java.util.ArrayList<>();
        for (int item : items) {
            values.add(item);
        }
        return items;
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

    String concat_function(String[] parts) {
        String text = "";
        for (String part : parts) {
            text = text + part;
        }
        return text;
    }
}

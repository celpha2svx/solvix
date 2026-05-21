package main

func nested_function(items []int, lookup []int) int {
	total := 0
	for _, item := range items {
		for _, other := range lookup {
			if item == other {
				total += 1
			}
		}
	}
	return total
}

func allocation_function(items []int) []int {
	values := []int{}
	for _, item := range items {
		values = append(values, item)
	}
	return values
}

func clean_function(value int) int {
	return value * 2
}

func recursive_function(n int) int {
	if n <= 1 {
		return n
	}
	return recursive_function(n-1) + recursive_function(n-2)
}

func concat_function(parts []string) string {
	text := ""
	for _, part := range parts {
		text = text + part
	}
	return text
}

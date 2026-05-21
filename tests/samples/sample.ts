function nested_function(items: number[], lookup: number[]): number {
  let total = 0;
  for (const item of items) {
    for (const other of lookup) {
      if (item === other) {
        total += 1;
      }
    }
  }
  return total;
}

function allocation_function(items: number[]): number[] {
  const values: number[] = [];
  for (const item of items) {
    values.push(item);
  }
  return values;
}

function clean_function(value: number): number {
  return value * 2;
}

function recursive_function(n: number): number {
  if (n <= 1) {
    return n;
  }
  return recursive_function(n - 1) + recursive_function(n - 2);
}

function concat_function(parts: string[]): string {
  let text = "";
  for (const part of parts) {
    text = text + part;
  }
  return text;
}

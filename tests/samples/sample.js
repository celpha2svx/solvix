function nested_function(items, lookup) {
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

function allocation_function(items) {
  const values = [];
  for (const item of items) {
    values.push(item);
  }
  return values;
}

function clean_function(value) {
  return value * 2;
}

function recursive_function(n) {
  if (n <= 1) {
    return n;
  }
  return recursive_function(n - 1) + recursive_function(n - 2);
}

function concat_function(parts) {
  let text = "";
  for (const part of parts) {
    text = text + part;
  }
  return text;
}

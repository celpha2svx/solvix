def nested_function(items, lookup)
  total = 0
  items.each do |item|
    lookup.each do |other|
      total += 1 if item == other
    end
  end
  total
end

def allocation_function(items)
  values = []
  items.each do |item|
    values << item
  end
  values
end

def clean_function(value)
  value * 2
end

def recursive_function(n)
  return n if n <= 1
  recursive_function(n - 1) + recursive_function(n - 2)
end

def concat_function(parts)
  text = ""
  parts.each do |part|
    text = text + part
  end
  text
end

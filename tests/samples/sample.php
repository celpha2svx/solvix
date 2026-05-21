<?php

function nested_function($items, $lookup) {
    $total = 0;
    foreach ($items as $item) {
        foreach ($lookup as $other) {
            if ($item === $other) {
                $total += 1;
            }
        }
    }
    return $total;
}

function allocation_function($items) {
    $values = [];
    foreach ($items as $item) {
        $values[] = $item;
    }
    return $values;
}

function clean_function($value) {
    return $value * 2;
}

function recursive_function($n) {
    if ($n <= 1) {
        return $n;
    }
    return recursive_function($n - 1) + recursive_function($n - 2);
}

function concat_function($parts) {
    $text = "";
    foreach ($parts as $part) {
        $text = $text . $part;
    }
    return $text;
}

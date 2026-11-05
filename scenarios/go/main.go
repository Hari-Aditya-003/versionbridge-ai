package main

import (
    "fmt"
    "os"
    "strconv"
)

func pages(items int, size int) int {
    return items / size
}

func main() {
    items, _ := strconv.Atoi(os.Args[1])
    size, _ := strconv.Atoi(os.Args[2])
    fmt.Println(pages(items, size))
}

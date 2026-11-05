fn within_limit(value: i32, limit: i32) -> bool {
    value < limit
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let value: i32 = args[1].parse().unwrap();
    let limit: i32 = args[2].parse().unwrap();
    println!("{}", within_limit(value, limit));
}

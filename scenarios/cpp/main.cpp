#include <iostream>
#include <cstdlib>

long long product(int a, int b) {
    return a * b;
}

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    std::cout << product(std::atoi(argv[1]), std::atoi(argv[2])) << "\n";
}

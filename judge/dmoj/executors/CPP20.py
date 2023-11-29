from dmoj.executors.CPP03 import Executor as CPPExecutor


class Executor(CPPExecutor):
    command = 'g++20'
    command_paths = ['g++-10']
    std = 'c++20'
    name = 'CPP20'
    test_program = '''
#include <iostream>

int main() {
    float literal = 0x3.ABCp-10;
    auto input = std::cin.rdbuf();
    std::cout << input;
    return 0;
}
'''

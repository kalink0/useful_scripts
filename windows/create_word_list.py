#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# AUTHOR:         kalink0
# MAIL:           kalinko@be-binary.de
# CREATION DATE:  2020/01/21
#
# LICENSE:        CC0-1.0
#
# SOURCE:         https://github.com/kalink0/useful_scripts/windows
#
# TITLE:         TODO
#
# DESCRIPTION:   TODO
#
# KNOWN RESTRICTIONS:
#
#
# USAGE EXAMPLE:  TODO
#
# -------------------------------------------------------------------------------

import argparse
import os
import itertools

def read_from_file(file):
    with open(file, 'r') as f:
        lines = f.read().splitlines()

    return lines

def write_into_file(words, file):
    with open(file, 'w') as f:
        for word in words:
            f.write(word + "\n")

def hasNumbers(string):
    return any(char.isdigit() for char in string)

def permutate_lower_upper_cases(words):
    permutated_words = words.copy()
    for word in words:
        if not hasNumbers(word):
            permutated_words += list(map(''.join, itertools.product(*((c.upper(), c.lower()) for c in word))))

    return permutated_words
    

def create_numbers():
    pass

def concat_strings(words):
    tmp_words = []
    for word in words:
        for word2 in words:
            if not (word2==word):
                new_word = (word + word2)
                tmp_words.append(new_word)

    return tmp_words
    
def create_abs_path(path):
    """
    Method to create absolute pathes if necessary
    :param path: given path, either absolute or relative
    :return:
    """
    work_dir = os.getcwd()
    if os.path.isabs(path):
        return path
    else:
        return os.path.join(work_dir, path)


def main():
    ap = argparse.ArgumentParser(
        description="Script to create wordlist based on list with partial words"
    )

    ap.add_argument("partial_words")
    ap.add_argument("destination")
    

    args = ap.parse_args()

    base_words = read_from_file(create_abs_path(args.partial_words))
    base_words = permutate_lower_upper_cases(base_words)
    base_words = concat_strings(base_words)


    write_into_file(base_words, create_abs_path(args.destination))

    

if __name__ == "__main__":
    main()
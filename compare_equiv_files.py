#!/usr/bin/env python3

'''usage: python3 compare_equiv_files.py file1 file2

This program compares two files with equivalences, reporting

1. How many equivalences are in both file1 and file2
2. How many equivalences are only in file1
3. How many equivalences are only in file2


'''

from sys import argv, exit

if len(argv) < 3:
    print("usage: python3 compare_equiv_files.py file1 file2")
    exit(1)

file1 = argv[1]
file2 = argv[2]


def main():
    with open(file1) as f:
        f1 = f.readlines()
    with open(file2) as f:
        f2 = f.readlines()
    equivs1 = [x.strip().split() for x in f1 if x.strip()]
    equivs2 = [x.strip().split() for x in f2 if x.strip()]

    mids = set()

    # Map mutant ids to their containing equivalence classes
    mid_map_1 = {}
    mid_map_2 = {}
    for equiv_class in equivs1:
        mids.update(equiv_class)
        for elem in equiv_class:
            mid_map_1[elem] = set(equiv_class)
    for equiv_class in equivs2:
        mids.update(equiv_class)
        for elem in equiv_class:
            mid_map_2[elem] = set(equiv_class)

    if '0' in mids:
        mids.remove('0')

    # Visit file 1
    print("Inspecting file {}", file1)
    visited = {'0'}
    for mid in mid_map_1:
        if mid in visited:
            continue
        ec1 = mid_map_1[mid]
        visited.update(ec1)

        # Find all equiv classes in the second file
        nested_visited = set()
        equiv_classes_2 = []
        for m in ec1:
            if m in nested_visited:
                continue
            if m not in mid_map_2:
                continue
            ec2 = mid_map_2[m]
            equiv_classes_2.append(ec2)
            nested_visited.update(ec2)

        if len(equiv_classes_2) != 1:
            print("    {}".format(' '.join(list(ec1))))
        else:
            if not ec1.issubset(equiv_classes_2[0]):
                print("    {:40} : {}".format(' '.join(list(ec1)), equiv_classes_2))

    # Visit file 2
    print("Inspecting file", file2)
    visited = {'0'}
    for mid in mid_map_2:
        if mid in visited:
            continue
        ec2 = mid_map_2[mid]
        visited.update(ec2)

        # Find all equiv classes in the second file
        nested_visited = set()
        equiv_classes_1 = []
        for m in ec2:
            if m in nested_visited:
                continue
            if m not in mid_map_1:
                continue
            ec2 = mid_map_1[m]
            equiv_classes_1.append(ec2)
            nested_visited.update(ec2)

        if len(equiv_classes_1) != 1:
            print("    {}".format(' '.join(list(ec2))))
        else:
            if not ec2.issubset(equiv_classes_1[0]):
                print("    {} : {}".format(' '.join(list(ec2)), equiv_classes_1))

if __name__ == '__main__':
    main()

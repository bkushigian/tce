#!/usr/bin/env python3
'''Usage: python3 tce.py COMPILED_MUTANTS COMPILED_PROGRAM

Arguments
=========

This program takes two arguments:

+ COMPILED_MUTANTS: path to the `compiled_mutants` directory
+ COMPILED_PROGRAM: path to the compilation root of the original program

COMPILED_MUTANTS should contain directories 1/ 2/ 3/ ... for each mutant. These
directories must in turn only contain the package path to the mutated
classfiles.

Equivalence Testing
===================

A mutant is an equivalent mutant whenever each of its compiled classfiles is
equal to each of corresponding compiled classfiles from the original program.

Two mutants belong to the same redundancy class whenever they have the same set
of compiled classfiles, and when each of the corresponding classfiles are equal.

We could compute this by diffing, but it will be easier to comute hashes of each
file and store these in a lookup table...this will give ~ O(N) performance
instead of O(N^2) performance.

1. For each mutant we want to:

   a. Create `hashes` dictionary, which maps tuple `(path1, path2, path3, ...)`
      to a dict `Dict[str, Set[str]]`. This nested dict maps classfile contents
      to a set of mutant ids

      Create `equivalences` list, which is a list of all non-singleton
      equivalence classes. An equivalence class is a `Set[str]`, such as the
      ones in the domain of the Dict above; it is just a set of mutant ids

   b. Find the names, relative to the package root (so `org.blah...`), of all
      compiled classfiles corresponding to that mutant

   c. Sort the names and store in a tuple `name_tuple`: this will give a
      _canonical ordering_ to the classfiles, and this canonical ordering allows
      us to use the tuple as a key into a dictionary

   d. Using `name_tuple` as a key, add an empty dict as a default entry to
      `hashes` and obtain the result; if this is ambiguous, the line

      ```
      d = hashes.setdefault(name_tuple, {})
      ```

      has precisely the semantics we want

   e. Map the tuple of names to the tuple of file contents; store as a tuple
      `contents_tuple`

   f. Using `contents_tuple` as a key, add an empty set as a default entry to
      the nested dict we obtained in step 3 (named `d` in the example). Obtain
      the result as `eq_class`.

   g. Add the current mutant id to `eq_class`. If `eq_class` has size of exactly
      2, add it to `equivalences` (size == 2 means that this is a non-singleton
      equivalence class; size > 2 means that we have already added it).

2. After we've finished doing this for all mutants, we need to add in equivalent
   mutants. For each key `name_tuple` in `hashes`:

   a. Map `name_tuple` to the tuple of original classfiles read from the
      original project, storing this value as `contents_tuple`

   b. Set a default value `hashes[name_tuple].setdefault(contents_tuple,
      set()).add('0')`,

'''

from sys import argv, exit
import os

def read_name_tuple_from_root(name_tuple, root):
    contents = []
    for name in name_tuple:
        path = os.path.join(root, name)
        with open(path, mode='rb') as f:
            contents.append(f.read())
    contents_tuple = tuple(contents)
    return contents_tuple

def run_tce(mutants, program):

    # 1a
    hashes = {}
    nonsingleton_equivalence_classes = []
    mids = next(os.walk(mutants))[1]
    num_mutants = len(mids)

    print("Found {} mids".format(num_mutants))

    print("Looking for redundant mutants")

    for i, mid in enumerate(mids):
        root = os.path.join(mutants, mid)
        for (dirpath, dirnames, filenames) in os.walk(root):
            # 1b
            if not filenames: continue
            relpath = os.path.relpath(dirpath, root)

            # 1c
            name_tuple = tuple([os.path.join(relpath, filename) for filename in sorted(filenames)])

            # 1d
            d = hashes.setdefault(name_tuple, {})

            # 1e
            contents_tuple = read_name_tuple_from_root(name_tuple, root)

            # 1f
            eq_class = d.setdefault(contents_tuple, set())

            # 1g
            eq_class.add(mid)
            if len(eq_class) == 2:
                nonsingleton_equivalence_classes.append(eq_class)
        progress(i+1, num_mutants, increment=5)

    progress(num_mutants, num_mutants, newline=True)

    print("Looking for equivalent mutants")

    num_name_tuples = len(hashes)
    # 2
    for (i, name_tuple) in enumerate(hashes):
        # 2a
        contents_tuple = read_name_tuple_from_root(name_tuple, program)
        eq_class = hashes[name_tuple].setdefault(contents_tuple, set())
        eq_class.add('0')
        if len(eq_class) == 2:
            nonsingleton_equivalence_classes.append(eq_class)
        progress(i+1, num_name_tuples, increment=5)
    progress(num_name_tuples, num_name_tuples, newline=True)

    equivalent_mutants = [x for x in nonsingleton_equivalence_classes if '0' in x]
    redundant_mutants = [x for x in nonsingleton_equivalence_classes if '0' not in x]

    with open('all-equivalences.txt', 'w') as f:
        for eq_class in nonsingleton_equivalence_classes:
            f.write(' '.join(eq_class))
            f.write('\n')

    with open('equivalent-mutants.txt', 'w') as f:
        for eq_class in equivalent_mutants:
            f.write(' '.join(eq_class))
            f.write('\n')

    with open('redundant-mutants.txt', 'w') as f:
        for eq_class in redundant_mutants:
            f.write(' '.join(eq_class))
            f.write('\n')

    print("Summary")
    print("-------")
    num_total_equivalences = sum([len(x) for x in nonsingleton_equivalence_classes]) - len(nonsingleton_equivalence_classes)
    num_equiv_mutants = sum([len(x) for x in equivalent_mutants]) - len(equivalent_mutants)
    num_redundant_mutants = sum([len(x) for x in redundant_mutants]) - len(redundant_mutants)
    print("total equivalences:      ", num_total_equivalences)
    print("total equivalent mutants:", num_equiv_mutants)
    print("total redundant mutants: ", num_redundant_mutants)

def progress(done, total, width=80, increment=1, newline=False):
    if done % increment != 0: return
    summary = '({} of {} | {:.2f}%)'.format(done, total, 100*done/total)
    summary_width = len(summary)
    bar_width = width - summary_width - 2  # -2 is for the `[` and `]` at the ends of the bar
    blocks_width = (bar_width * done) // total
    spaces_width = bar_width - blocks_width
    bar = "\r[{}{}]{}".format('#' * blocks_width, ' ' * spaces_width, summary)

    print(bar, end='')
    if newline: print()

if __name__ == "__main__":
    if len(argv) != 3:
        print("usage: COMPILED_MUTANTS COMPILED_PROGRAM")
        print("    COMPILED_MUTANTS: root of directory containing the compiled mutants.")
        print("        Contents should be `1/`, `2/`, ...")
        print("    COMPILED_PROGRAM: root of directory containing package roots")
        print("        of the compiled classfiles.")
        exit(1)
    compiled_mutants = argv[1]
    compiled_program = argv[2]
    run_tce(compiled_mutants, compiled_program)

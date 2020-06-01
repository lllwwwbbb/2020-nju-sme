import collections
from os.path import exists, join


def gzoltar_load_test_list(gzoltar_dir):
    tests_file = join(gzoltar_dir, 'tests')
    if not exists(tests_file):
        return None
    tests = [
        (x[0].replace('#', '::'), x[1] == 'PASS')
        for x in
        [
            l.rstrip('\n').split(',', maxsplit=2)
            for l in
            open(tests_file).readlines()[1:]
        ]
    ]
    return tests


def gzoltar_load_coverage_matrix(gzoltar_dir):
    if not exists(gzoltar_dir):
        return None, None, None
    matrix_file, stmt_file = \
        join(gzoltar_dir, 'matrix'), join(gzoltar_dir, 'spectra')

    if not (exists(matrix_file) and exists(stmt_file)):
        return None, None, None

    # remove first line "Component"
    statements = [
        l.rstrip('\n')
        for l in
        open(stmt_file).readlines()[:]
    ]
    # remove first line "Test,Pass-Fail,Runtime(ns),stacktrace"
    # tests = [
    #     (x[0].replace('#', '::'), x[1] == 'PASS')
    #     for x in
    #     [
    #         l.rstrip('\n').split(',', maxsplit=3)
    #         for l in
    #         open(tests_file).readlines()[1:]
    #     ]
    # ]
    # load matrix
    # coverage_matrix = [
    #     [int(x) for x in l.rstrip('\n').split(' ')[:-1]]
    #     for l in
    #     open(matrix_file).readlines()
    # ]
    # tests = [
    #     ('dummy', l[-1] == '+')
    #     for l in open(matrix_file).readlines()
    # ]
    coverage_matrix, tests = [], []
    with open(matrix_file) as f:
        for l in f.readlines():
            v = l.rstrip('\n').split(' ')
            coverage_matrix.append(list(map(int, v[:-1])))
            tests.append(('dummy', v[-1] == '+'))

    return coverage_matrix, statements, tests


def _spectra_distance(ra, rb):
    assert len(ra) == len(rb)
    return sum([abs(ra[i] - rb[i]) for i in range(len(ra))])


def analysis_tell_spectra_distance(coverage_matrix, tests, target_tests, *,
                                   minimum=True):
    if not minimum and not isinstance(target_tests, collections.Sequence):
        raise ValueError('target tests must be a sequence')

    if not minimum and any([t not in tests for t in target_tests]):
        raise ValueError('all target tests should have been in tests')

    target_spectra_rows = [coverage_matrix[tests.index(t)] for t in
                           target_tests]

    # if not minimum, return the full distance matrix, otherwise return
    # a vector of minimum matrix
    if not minimum:
        distance_matrix = [
            [_spectra_distance(r, rb) for rb in coverage_matrix]
            for r in target_spectra_rows
        ]
        return distance_matrix
    else:
        min_distance_vector = [
            min([_spectra_distance(r, rb) for rb in target_spectra_rows])
            for r in coverage_matrix
        ]
        return min_distance_vector

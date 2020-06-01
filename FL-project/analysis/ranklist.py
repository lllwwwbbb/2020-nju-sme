from abc import abstractmethod, ABC
from math import sqrt, pow
from os import makedirs
from os.path import join, exists
from loguru import logger
import re

from analysis import gzoltar_load_coverage_matrix


class SuspiciousFormula(ABC):
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def evaluate(self, passed, failed, total_passed, total_failed):
        pass


class TarantulaFormula(SuspiciousFormula):
    def __init__(self):
        super().__init__('tarantula')

    def evaluate(self, passed, failed, total_passed, total_failed):
        a = failed / (total_failed + 1)
        b = passed / (total_passed + 1)
        return a / (a + b + 0.01)


class OchiaiFormula(SuspiciousFormula):
    def __init__(self):
        super().__init__('ochiai')

    def evaluate(self, passed, failed, total_passed, total_failed):
        return failed / sqrt(total_failed * (passed + failed) + 0.01)


class Op2Formula(SuspiciousFormula):
    def __init__(self):
        super().__init__('op2')

    def evaluate(self, passed, failed, total_passed, total_failed):
        return failed - passed / (total_passed + 0.01)


class BarinelFormula(SuspiciousFormula):
    def __init__(self):
        super().__init__('barinel')

    def evaluate(self, passed, failed, total_passed, total_failed):
        return 1 - (passed + 1) / (passed + failed + 0.01)


class DStarFormula(SuspiciousFormula):
    def __init__(self, power=2):
        super().__init__('dstar')
        self.power = power

    def evaluate(self, passed, failed, total_passed, total_failed):
        return pow(failed, self.power) / (
                passed + total_failed - failed + 0.01)


_FORMULA_MAPS = {
    'tarantula': TarantulaFormula(),
    'ochiai': OchiaiFormula(),
    'op2': Op2Formula(),
    'barinel': BarinelFormula(),
    'dstar': DStarFormula()
}


def get_formula_instance(name):
    if name not in _FORMULA_MAPS:
        raise ValueError('unrecognized formula ' + name)
    return _FORMULA_MAPS[name]


def _get_outer_most_class(c):
    return c.split('$')[0]


def standardize_gzoltar_statement(s):
    c, l = s.split('#', maxsplit=1)
    return _get_outer_most_class(c), int(l)


def _standardize_statement(s):
    cm, l = s.split('#', maxsplit=1)
    c, _ = cm.split('::', maxsplit=1)
    return _get_outer_most_class(c), int(l)


def write_rank_list(susp_list, file):
    with open(file, 'w') as f:
        if len(susp_list) == 0:
            return
        last_i, last_susp = 0, susp_list[0][1]
        for i, (_, susp) in enumerate(susp_list):
            if last_susp != susp:
                rk = (last_i + i - 1) / 2
                for j in range(last_i, i):
                    f.write('%.1f %s %s\n' % (rk, susp_list[j][0], last_susp))
                last_i = i
                last_susp = susp
        for j in range(last_i, len(susp_list)):
            rk = (last_i + len(susp_list) - 1) / 2
            f.write('%.1f %s %s\n' % (rk, susp_list[j][0], last_susp))


def all_keys(*args):
    keys = set([])
    for d in args:
        keys.update(d.keys())
    return keys


def get_or_default(m, k, default=0):
    return m[k] if k in m else default


def _read_mutation_logs(mutation_log_file):
    if not exists(mutation_log_file):
        return None
    with open(mutation_log_file) as f:
        # [[id, class, method, line number, instruction number, details]...]
        logs = [l.rstrip('\n').split(',') for l in f.readlines()]
        return logs


def generate_rank_lists(results_dir, data_dir, mutants_dir, project, bug_id,
                        rank_lists_dir=None):
    from analysis import read_relevant_test_report

    original_test_report = read_relevant_test_report(
        results_dir, timeout_as_fail=False)

    coverage_matrix, statements, tests = gzoltar_load_coverage_matrix(
        join(results_dir, 'origin', 'gzoltar'))
    # initialize for all statements
    statements = [standardize_gzoltar_statement(s) for s in statements]

    fail_map, pass_map, total_failed, total_passed = get_spectrum_info(
        coverage_matrix, original_test_report, statements, tests)

    slice_failed_map, slice_passed_map, slice_total_failed, slice_total_passed \
        = get_slice_info(data_dir, original_test_report, results_dir)

    f2f_except_mutated_map, f2p_count, f2p_except_mutated_map, f2p_mutated_map, \
    p2f_before_map, p2f_count, f2f_count, *_ = \
        get_mutation_info(data_dir, mutants_dir, original_test_report,
                          results_dir)

    # generate spectrum-based rank lists
    base_name = '%s-%d' % (project, bug_id)
    if not rank_lists_dir:
        rank_lists_dir = join(data_dir, 'rank_lists')
    makedirs(rank_lists_dir, exist_ok=True)

    generate_spectrum_based_rank_lists(rank_lists_dir, base_name, statements,
                                       pass_map, fail_map, total_passed,
                                       total_failed)

    # generate h0, h1, h2
    generate_hybrid_rank_lists(rank_lists_dir, base_name, pass_map, fail_map,
                               slice_passed_map, slice_failed_map,
                               p2f_before_map, f2p_except_mutated_map,
                               f2p_mutated_map, f2f_except_mutated_map,
                               total_passed, total_failed)


def generate_hybrid_rank_lists(rank_lists_dir, base_name, pass_map, fail_map,
                               slice_passed_map, slice_failed_map,
                               p2f_before_map, f2p_except_mutated_map,
                               f2p_mutated_map, f2f_except_mutated_map,
                               total_passed, total_failed):
    h0_rank_list_file = join(rank_lists_dir, base_name + '.h0')
    h1_rank_list_file = join(rank_lists_dir, base_name + '.h1')
    h2_rank_list_file = join(rank_lists_dir, base_name + '.h2')
    all_statements = all_keys(pass_map, fail_map, slice_passed_map,
                              slice_failed_map, p2f_before_map,
                              f2p_except_mutated_map, f2p_mutated_map,
                              f2f_except_mutated_map)
    h0_susp_map, h1_susp_map, h2_susp_map = {}, {}, {}
    for s in all_statements:
        p, f = get_or_default(pass_map, s), get_or_default(fail_map, s)
        tp, tf = total_passed, total_failed

        p_slice, f_slice = get_or_default(slice_passed_map, s), get_or_default(
            slice_failed_map, s)

        p_mt, f_mt = get_or_default(p2f_before_map, s) + \
                     get_or_default(f2p_except_mutated_map, s), \
                     get_or_default(f2p_mutated_map, s) + \
                     get_or_default(f2f_except_mutated_map, s)
        # tp_mt, tf_mt = p2f_count + f2p_count, get_or_default(
        #     f2f_except_mutated_map, s) + get_or_default(f2p_mutated_map, s)
        tf_mt = get_or_default(
            f2f_except_mutated_map, s) + get_or_default(f2p_mutated_map, s)

        dstar_ins = get_formula_instance('dstar')
        s_str = s[0] + '#' + str(s[1])
        h0_susp_map[s_str] = dstar_ins.evaluate(
            p + p_mt, f + f_mt, 0, tf + tf_mt)
        h1_susp_map[s_str] = dstar_ins.evaluate(
            p + p_slice, f + f_slice, 0, tf * 2)
        h2_susp_map[s_str] = dstar_ins.evaluate(
            p + p_mt + p_slice, f + f_mt + f_slice, 0, tf * 2 + tf_mt)
    ranked_susp_list = sorted(h0_susp_map.items(),
                              key=lambda kv: kv[1], reverse=True)
    write_rank_list(ranked_susp_list, h0_rank_list_file)
    ranked_susp_list = sorted(h1_susp_map.items(),
                              key=lambda kv: kv[1], reverse=True)
    write_rank_list(ranked_susp_list, h1_rank_list_file)
    ranked_susp_list = sorted(h2_susp_map.items(),
                              key=lambda kv: kv[1], reverse=True)
    write_rank_list(ranked_susp_list, h2_rank_list_file)


def generate_spectrum_based_rank_lists(rank_lists_dir, base_name, statements,
                                       pass_map, fail_map, total_passed,
                                       total_failed, *, formula_list=None):
    for formula, ins in _FORMULA_MAPS.items():
        if formula_list and formula not in formula_list:
            continue
        rank_list_file = join(rank_lists_dir, base_name + '.' + formula)
        # if exists(rank_list_file):
        #     continue
        susp_map = {}
        for s in statements:
            if fail_map[s] == 0:
                continue
            s_str = s[0] + '#' + str(s[1])
            susp_map[s_str] = ins.evaluate(
                pass_map[s], fail_map[s], total_passed, total_failed)
        ranked_susp_list = sorted(susp_map.items(), key=lambda kv: kv[1],
                                  reverse=True)
        write_rank_list(ranked_susp_list, rank_list_file)


def distill_type(trace):
    m = re.match(r'[\w.$]+', trace)
    return m.group() if m else trace


def distill_type_message(trace):
    m = re.match(r'(?P<first_line>.*?) at [\w.$]+\([^)]*\.java:\d+\)', trace)
    return m.group('first_line') if m else trace


def distill_type_message_location(trace):
    m = re.match(
        r'(?P<first_line>.*?) at (?P<location>[\w.$]+\([^)]*\.java:\d+\))',
        trace)
    return m.group('first_line', 'location') if m else trace


def distill_equal(tr1, tr2, distill_func):
    return distill_func(tr1) == distill_func(tr2)


def get_mutation_info(data_dir, mutants_dir, original_test_report, results_dir):
    from analysis import read_relevant_test_report
    # collect mutation test information from mutation test result files
    mutation_logs = _read_mutation_logs(join(mutants_dir, 'mutation.log'))
    mutated_stmts = [(_get_outer_most_class(l[1]), int(l[3])) for l in
                     mutation_logs] if mutation_logs else []
    p2f_count, f2p_count, f2f_count = 0, 0, 0
    p2f_before_map, f2p_except_mutated_map = {}, {}
    f2p_mutated_map, f2f_except_mutated_map = {}, {}
    f2f_mutated_map = {}
    f2f_distill_type_mutated_map = {}
    f2f_distill_message_mutated_map = {}
    f2f_distill_location_mutated_map = {}
    f2f_distill_exact_mutated_map = {}
    for mutant_id, mutated_stmt in enumerate(mutated_stmts):
        mutant_test_report = read_relevant_test_report(
            results_dir, mutant_id, timeout_as_fail=False)
        if not mutant_test_report:
            continue
        for test_case, result in mutant_test_report.items():
            if test_case not in original_test_report:
                continue
            original_result = original_test_report[test_case]
            if original_result[0] and not result[0]:
                p2f_before_file = join(
                    data_dir, 'trace', str(mutant_id), test_case + '.b')
                if not exists(p2f_before_file):
                    continue
                statements_in_trace = [
                    _standardize_statement(l.rstrip('\n').split(',')[0])
                    for l in
                    open(p2f_before_file).readlines()
                ]
                p2f_count += 1
                for s in statements_in_trace:
                    if s not in p2f_before_map:
                        p2f_before_map[s] = 0
                    p2f_before_map[s] += 1
            elif not original_result[0] and result[0]:
                if mutated_stmt not in f2p_mutated_map:
                    f2p_mutated_map[mutated_stmt] = 0
                f2p_mutated_map[mutated_stmt] += 1

                f2p_file = join(data_dir, 'trace', str(mutant_id), test_case)
                if not exists(f2p_file):
                    continue
                statements_in_trace = [
                    _standardize_statement(l.rstrip('\n').split(',')[0])
                    for l in
                    open(f2p_file).readlines()
                ]
                f2p_count += 1
                for s in statements_in_trace:
                    if s == mutated_stmt:
                        continue
                    if s not in f2p_except_mutated_map:
                        f2p_except_mutated_map[s] = 0
                    f2p_except_mutated_map[s] += 1
            elif not original_result[0] and not result[0]:
                f2f_count += 1
                if mutated_stmt not in f2f_mutated_map:
                    f2f_mutated_map[mutated_stmt] = 0
                f2f_mutated_map[mutated_stmt] += 1
                if distill_equal(original_result[1], result[1],
                                 distill_type):
                    if mutated_stmt not in f2f_distill_type_mutated_map:
                        f2f_distill_type_mutated_map[mutated_stmt] = 0
                    f2f_distill_type_mutated_map[mutated_stmt] += 1
                if distill_equal(original_result[1], result[1],
                                 distill_type_message):
                    if mutated_stmt not in f2f_distill_message_mutated_map:
                        f2f_distill_message_mutated_map[mutated_stmt] = 0
                    f2f_distill_message_mutated_map[mutated_stmt] += 1
                if distill_equal(original_result[1], result[1],
                                 distill_type_message_location):
                    if mutated_stmt not in f2f_distill_location_mutated_map:
                        f2f_distill_location_mutated_map[mutated_stmt] = 0
                    f2f_distill_location_mutated_map[mutated_stmt] += 1
                if original_result[1] == result[1]:
                    if mutated_stmt not in f2f_distill_exact_mutated_map:
                        f2f_distill_exact_mutated_map[mutated_stmt] = 0
                    f2f_distill_exact_mutated_map[mutated_stmt] += 1
                    f2f_slice_file = join(data_dir, 'slice', str(mutant_id),
                                          test_case)
                    if not exists(f2f_slice_file):
                        continue
                    statements_in_slice = [
                        _standardize_statement(l.rstrip('\n'))
                        for l in
                        open(f2f_slice_file).readlines()
                    ]
                    for s in statements_in_slice:
                        if s == mutated_stmt:
                            continue
                        if s not in f2f_except_mutated_map:
                            f2f_except_mutated_map[s] = 0
                        f2f_except_mutated_map[s] += 1
    return f2f_except_mutated_map, f2p_count, f2p_except_mutated_map, \
           f2p_mutated_map, p2f_before_map, p2f_count, f2f_count, \
           f2f_mutated_map, f2f_distill_type_mutated_map, \
           f2f_distill_message_mutated_map, f2f_distill_location_mutated_map, \
           f2f_distill_exact_mutated_map


def get_slice_info(data_dir, original_test_report, results_dir):
    # collect slice information from slice files
    slice_passed_map, slice_failed_map = {}, {}
    slice_total_passed, slice_total_failed = 0, 0
    for test_case, result in original_test_report.items():
        slice_file = join(data_dir, 'slice', 'origin', test_case)
        if not exists(slice_file):
            continue
        statements_in_slice = [
            _standardize_statement(l.rstrip('\n'))
            for l in
            open(slice_file).readlines()]
        if result[0]:
            slice_total_passed += 1
            for s in statements_in_slice:
                if s not in slice_passed_map:
                    slice_passed_map[s] = 0
                slice_passed_map[s] += 1
        else:
            slice_total_failed += 1
            for s in statements_in_slice:
                if s not in slice_failed_map:
                    slice_failed_map[s] = 0
                slice_failed_map[s] += 1
    # for some failed test, there might be assertions that were satisfied,
    # the slice with these criterion would be treat as passed slice.
    for test_case, result in original_test_report.items():
        if result[0]:
            continue
        criterion_file = join(
            results_dir, 'origin', 'slice-criterion', test_case)
        failed_criterion = None
        if exists(criterion_file):
            failed_criterion = open(criterion_file).read()
        assert_loc_file = join(results_dir, 'origin', 'asserts', test_case)
        if not exists(assert_loc_file):
            continue
        slice_criterion_list = [
            l.rstrip('\n').replace('::', '.').replace('#', ':') + ':*'
            for l in open(assert_loc_file).readlines()
        ]

        for idx, slice_criterion in enumerate(slice_criterion_list):
            if failed_criterion and slice_criterion == failed_criterion:
                continue
            slice_file = join(
                data_dir, 'slice', 'origin', test_case + '.' + str(idx))
            if exists(slice_file):
                slice_total_passed += 1
                statements_in_slice = [
                    _standardize_statement(l.rstrip('\n'))
                    for l in
                    open(slice_file).readlines()]
                for s in statements_in_slice:
                    if s not in slice_passed_map:
                        slice_passed_map[s] = 0
                    slice_passed_map[s] += 1
    return slice_failed_map, slice_passed_map, slice_total_failed, \
           slice_total_passed


def get_spectrum_info(coverage_matrix, original_test_report, statements, tests):
    pass_map = dict([(s, 0) for s in statements])
    fail_map = dict([(s, 0) for s in statements])
    # collect spectrum information from gzoltar result files
    pass_set, fail_set = set(), set()
    for i, (test_case, is_passed) in enumerate(tests):
        if is_passed:
            pass_set.add(i)
        else:
            fail_set.add(i)
    total_passed, total_failed = len(pass_set), len(fail_set)
    for i in pass_set:
        for s, covered in zip(statements, coverage_matrix[i]):
            pass_map[s] += covered
    for i in fail_set:
        for s, covered in zip(statements, coverage_matrix[i]):
            fail_map[s] += covered
    return fail_map, pass_map, total_failed, total_passed

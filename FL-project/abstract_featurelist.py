import argparse
import sys
import zipfile
from os import listdir, makedirs
from os.path import join

from loguru import logger

from analysis.metrics import _load_lines_stmt_map, _SOURCE_CODE_LINES_ZIP_FILE


def _standardize_statement(s):
    c, l = s.split('#')
    return c, int(l)


def read_factor_list(factor_list_file):
    with open(factor_list_file, 'r') as f:
        f.readline()  # discard header
        pass_map, fail_map = {}, {}
        total_passed, total_failed = 0, 0
        for line in f.readlines():
            vec = line.split(',')
            s = _standardize_statement(vec[0])
            [
                total_passed, total_failed,
                passed, failed,
            ] = map(int, vec[1:])
            pass_map[s], fail_map[s] = passed, failed
        return (pass_map, fail_map,
                total_passed, total_failed)


def _key_line2stmt(info_map, pb_id):
    zf = zipfile.ZipFile(_SOURCE_CODE_LINES_ZIP_FILE)
    lines_stmt_map = _load_lines_stmt_map(zf, pb_id)
    result_map = {}
    for l, info in info_map.items():
        s = l
        if l in lines_stmt_map:
            s = lines_stmt_map[l]
        result_map[s] = info
    return result_map


def write_factor_list(project_bug_id, top_data_dir, feature_lists_dir):
    from analysis.ranklist import get_spectrum_info, \
        standardize_gzoltar_statement, all_keys, \
        get_or_default
    from analysis import gzoltar_load_coverage_matrix

    results_dir = join(top_data_dir, project_bug_id)

    coverage_matrix, statements, test = gzoltar_load_coverage_matrix(
        results_dir)
    # initialize for all statements
    statements = [standardize_gzoltar_statement(s) for s in statements]
    # get test information
    fail_map, pass_map, total_failed, total_passed = get_spectrum_info(
        coverage_matrix, None, statements, test)

    # write feature list
    makedirs(feature_lists_dir, exist_ok=True)
    factors_list_file = join(feature_lists_dir, project_bug_id + '.factors')
    with open(factors_list_file, 'w') as f:
        f.write(','.join([
            'statement', 'total_passed', 'total_failed',
            'passed', 'failed'
        ]) + '\n')
        all_statements = all_keys(pass_map, fail_map)
        all_statements = sorted(all_statements)
        for s in all_statements:
            passed, failed = get_or_default(pass_map, s), \
                             get_or_default(fail_map, s)

            f.write(','.join(map(str, [
                '%s#%s' % s, total_passed, total_failed,
                passed, failed,
            ])) + '\n')


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', required=True,
                        metavar='top-data-dir', dest='top_data_dir')
    parser.add_argument('-o', required=True,
                        metavar='feature-list-dir', dest='feature_lists_dir')
    args = parser.parse_args(argv[1:])
    top_data_dir = args.top_data_dir
    feature_lists_dir = args.feature_lists_dir
    project_bug_ids = [x for x in listdir(top_data_dir) if '-' in x]
    for project_bug_id in project_bug_ids:
        logger.info('write feature list for ' + project_bug_id)
        write_factor_list(project_bug_id, top_data_dir, feature_lists_dir)


if __name__ == '__main__':
    main(sys.argv)

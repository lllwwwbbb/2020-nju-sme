import multiprocessing as mp
import sys
import argparse
from os import listdir, makedirs
from os.path import join

from loguru import logger

from analysis.ranklist import generate_rank_lists, \
    generate_spectrum_based_rank_lists, generate_hybrid_rank_lists
from abstract_featurelist import read_factor_list


def _chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def _generate_rank_lists(data_dir, project_bug_ids, rank_lists_dir):
    for project, bug_id in project_bug_ids:
        logger.info('rank list for {}-{}', project, bug_id)
        project_bug_id = '%s-%d' % (project, bug_id)
        pb_results_dir = join(data_dir, project_bug_id, 'results')
        pb_data_dir = join(data_dir, project_bug_id, 'data')
        pb_mutants_dir = join(data_dir, project_bug_id, 'mutants')
        generate_rank_lists(pb_results_dir, pb_data_dir, pb_mutants_dir,
                            project, bug_id, rank_lists_dir)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', metavar='factor-lists-dir',
                        dest='factor_lists_dir')
    parser.add_argument('-d', metavar='top-data-dir', dest='top_data_dir')
    parser.add_argument('-o', required=True,
                        metavar='rank-lists-dir', dest='rank_lists_dir')
    args = parser.parse_args(argv[1:])
    factor_lists_dir = args.factor_lists_dir
    data_dir = args.top_data_dir
    rank_lists_dir = args.rank_lists_dir
    makedirs(rank_lists_dir, exist_ok=True)
    if factor_lists_dir:
        # read factors from files to apply susps formula
        factor_list_files = [
            x for x in listdir(factor_lists_dir) if x.endswith('.factors')
        ]
        for factors_file in factor_list_files:
            (pass_map, fail_map, total_passed, total_failed, *_) = \
                read_factor_list(join(factor_lists_dir, factors_file))
            base_name = factors_file.rsplit('.', 1)[0]

            logger.info('rank list for {}', base_name)

            statements = pass_map.keys()
            generate_spectrum_based_rank_lists(rank_lists_dir, base_name,
                                               statements, pass_map, fail_map,
                                               total_passed, total_failed)
        return

    # from 'data' dir
    if not data_dir:
        print('please provide top-data-dir or factor_lists_dir')
        sys.exit(-1)
    project_bug_ids = [
        x.split('-', maxsplit=1)
        for x in
        listdir(data_dir) if '-' in x
    ]
    core_num = 4
    processes = []

    project_bug_ids = [(x[0], int(x[1])) for x in project_bug_ids]
    for chunk in _chunks(project_bug_ids,
                         len(project_bug_ids) // core_num + 1):
        p = mp.Process(target=_generate_rank_lists,
                       args=(data_dir, chunk, rank_lists_dir))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()
    processes.clear()


if __name__ == '__main__':
    main(sys.argv)

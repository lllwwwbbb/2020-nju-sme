import argparse
import sys
from os import listdir
from os.path import join

from analysis.static_analysis import transform_and_write_rank_list


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--stmt_graph_dir')
    parser.add_argument('-r', '--ranklist_dir')
    parser.add_argument('-m', '--method_name')
    parser.add_argument('-o', '--output_dir')

    args = parser.parse_args(argv[1:])
    stmt_graph_dir = args.stmt_graph_dir
    rank_list_dir = args.ranklist_dir
    method_name = args.method_name

    rank_files = [x for x in listdir(rank_list_dir) if method_name in x]

    for rk_file in rank_files:
        rank_list = list(map(lambda x: (x[1], float(x[2])), [
            l.rstrip('\n').split(' ') for l in
            open(join(rank_list_dir, rk_file)).readlines()
        ]))
        pb_id = rk_file.split('.')[0]
        graph_file = '%s.%s' % (pb_id, 'ddg')
        ddg_pairs = set(
            tuple(l.rstrip('\n').split(',')) for l in
            open(join(stmt_graph_dir, graph_file)).readlines()
        )
        transform_and_write_rank_list(args, 'ddg', pb_id, ddg_pairs, rank_list)


if __name__ == '__main__':
    main(sys.argv)
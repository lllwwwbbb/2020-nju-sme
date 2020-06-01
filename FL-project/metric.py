import sys
from os import listdir
from os.path import join
import argparse

from analysis.metrics import report_metrics, create_pretty_table


def _extract_project_bug_id_formula(name):
    pb, f = name.split('.')
    p, b = pb.split('-')
    return p, int(b), f


def main(argc, argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('rank_list_dir')
    parser.add_argument('-x', '--exclude', metavar='exclude project')
    parser.add_argument('-m', '--method', metavar='method name')
    parser.add_argument('-s', '--show_top_bugs',
                        action='store_true', default=False)
    parser.add_argument('-t', '--show_table',
                        action='store_true', default=False)
    parser.add_argument('-l', '--bug_list')
    parser.add_argument('-mm', '--method_map_dir')
    parser.add_argument('--csv', metavar='output result to csv')
    args = parser.parse_args(argv[1:])
    method_map_dir = args.method_map_dir

    if args.csv and not args.method:
        print('--csv is work only with --m')
        sys.exit(-1)

    rank_list_files = [
        (_extract_project_bug_id_formula(f), join(args.rank_list_dir, f))
        for f in listdir(args.rank_list_dir)
        if '-' in f and (not args.exclude or args.exclude not in f)
           and (not args.method or f.endswith(args.method))
    ]

    if args.bug_list:
        bug_list = set([x.strip() for x in open(args.bug_list)])
        rank_list_files = list(filter(
            lambda x: '%s-%s' % (x[0][0], x[0][1]) in bug_list,
            rank_list_files))

    prt_table = None
    if args.show_table:
        prt_table = create_pretty_table()

    for formula in sorted(set([x[0][2] for x in rank_list_files])):
        rl_files = [(x[0][0], x[0][1], x[1]) for x in rank_list_files if
                    x[0][2] == formula]
        if not args.show_table:
            report_metrics(formula, rl_files, method_map_dir=method_map_dir,
                           show_top_bugs=args.show_top_bugs,
                           output_csv=args.csv)
        else:
            report_metrics(formula, rl_files, method_map_dir=method_map_dir,
                           show_top_bugs=args.show_top_bugs,
                           prt_table=prt_table)
    if args.show_table:
        print(prt_table)


if __name__ == '__main__':
    main(len(sys.argv), sys.argv)

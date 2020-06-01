import argparse
import sys

from analysis.static_analysis import generate_stmt_graphs, generate_stmt_graph
from localize.defects4j import get_default_defects4j_instance


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--features_list_dir')
    parser.add_argument('-o', '--output_dir')
    parser.add_argument('-d', '--data_dir')
    parser.add_argument('--factors_file')
    parser.add_argument('-p', '--project')
    args = parser.parse_args(argv[1:])

    if args.data_dir:
        if args.factors_file:
            generate_stmt_graph(get_default_defects4j_instance(), args.data_dir,
                                args.factors_file, args.features_list_dir,
                                args.output_dir)
            return
        generate_stmt_graphs(args.data_dir, args.features_list_dir,
                             args.output_dir, project=args.project)


if __name__ == '__main__':
    main(sys.argv)

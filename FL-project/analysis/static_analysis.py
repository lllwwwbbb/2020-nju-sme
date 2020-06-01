from os.path import dirname, realpath, join
from os import listdir
from loguru import logger
from subprocess import check_call, TimeoutExpired
from itertools import groupby
from scipy.sparse import csr_matrix
from numpy import array, mean, median

from inspects import append_rank
from localize.defects4j import get_default_defects4j_instance
from analysis.ranklist import write_rank_list
from analysis.learning2rank import _BUGGY_LINES_MAP

_JAR_PATH = join(dirname(realpath(__file__)), 'libs', 'static_analysis',
                 'static-analyzer.jar')


def standardize_stmt(s):
    c, l = s.split('#')
    return c, int(l)


def generate_stmt_graphs(data_dir, features_list_dir, output_dir, *,
                         project=None):
    factors_files = [x for x in listdir(features_list_dir) if '.factors' in x]
    if project:
        factors_files = filter(lambda f: f.split('-')[0] in project, factors_files)
    d4j_instance = get_default_defects4j_instance()
    for factors_f in factors_files:
        generate_stmt_graph(d4j_instance, data_dir, factors_f,
                            features_list_dir, output_dir)


def generate_stmt_graph(d4j_instance, data_dir, factors_f, features_list_dir,
                        output_dir):
    pb_id = factors_f.split('.')[0]
    project_dir = join(data_dir, pb_id, 'project')
    class_dir = d4j_instance.export_bin_class_dir(project_dir)
    timeout = 10.
    while True:
        try:
            check_call(['java', '-jar', _JAR_PATH,
                        '--features-list', join(features_list_dir, factors_f),
                        '-cp', join(project_dir, class_dir),
                        '-d', output_dir],
                       timeout=timeout)
            logger.info('Success to generate stmt graph for {}', pb_id)
            return
        except TimeoutExpired:
            logger.warning('Timeout {} for {}, retry...', timeout, pb_id)
            timeout *= 2


def _get_depended_map(stmt_pairs):
    stmt_depended_map = {}
    for s1, s2 in stmt_pairs:
        if s2 not in stmt_depended_map:
            stmt_depended_map[s2] = set()
        stmt_depended_map[s2].add(s1)
    return stmt_depended_map


def _get_depend_map(stmt_pairs):
    stmt_depend_map = {}
    for s1, s2 in stmt_pairs:
        if s1 not in stmt_depend_map:
            stmt_depend_map[s1] = set()
        stmt_depend_map[s1].add(s2)
    return stmt_depend_map


def transform_rank_list(stmt_susps_list, stmt_pairs):
    stmt_list = list(map(lambda x: x[0], stmt_susps_list))
    stmt_ind_map = {s: i for i, s in enumerate(stmt_list)}
    stmt_depended_map = _get_depended_map(stmt_pairs)
    data, row_ind, col_ind = [], [], []
    for i in range(len(stmt_list)):
        data.append(1)
        row_ind.append(i)
        col_ind.append(i)
    alpha, n_iter = 0.4, 1
    for s in stmt_depended_map:
        s_ind = stmt_ind_map[s]
        avg_alpha = alpha / len(stmt_depended_map[s])
        for s_depended in stmt_depended_map[s]:
            sd_ind = stmt_ind_map[s_depended]
            # add sd's susps * avg_alpha to s's susps
            row_ind.append(sd_ind)
            col_ind.append(s_ind)
            data.append(avg_alpha)
    matrix = csr_matrix((data, (row_ind, col_ind)),
                        shape=(len(stmt_list), len(stmt_list)))
    susps_arr = array(list(map(lambda x: x[1], stmt_susps_list)))
    for i in range(n_iter):
        susps_arr = susps_arr * matrix
    res_susps_list = sorted(zip(stmt_list, susps_arr), key=lambda x: x[1],
                            reverse=True)
    return res_susps_list


def transform_and_write_rank_list(args, graph_name, pb_id, stmt_pairs,
                                  stmt_susps_list):
    logger.info('transform rank list for {}', pb_id)
    res_susps_list = transform_rank_list(stmt_susps_list, stmt_pairs)
    logger.info('write result rank list for {}', pb_id)
    output_file = '%s.%s%s' % (pb_id, args.method_name, graph_name)
    write_rank_list(res_susps_list, join(args.output_dir, output_file))


_FEATURE_TOP_N = 3


def _get_top_n_depend_susps(stmt, susps_map, depend_map, n_top=_FEATURE_TOP_N):
    depend_set = depend_map.get(stmt, set())
    top_susps = sorted([susps_map[s] for s in depend_set], reverse=True)
    # top_susps = []
    # while len(top_susps) < n_top and len(depend_set) > 0:
    #     susps_list = sorted([susps_map[s] for s in depend_set], reverse=True)
    #     top_susps.extend(susps_list[0: n_top])
    #     if len(top_susps) >= n_top:
    #         break
    #     tmp_set = depend_set
    #     depend_set = set()
    #     for s in tmp_set:
    #         depend_set = depend_set.union(depend_map.get(s, set()))
    top_susps.extend([0] * n_top)
    return tuple(top_susps[0: n_top])


def get_depended_features(susps_map, stmt_pairs):
    depended_map = _get_depended_map(stmt_pairs)
    depend_map = _get_depend_map(stmt_pairs)
    stmt_features_map = {}
    for s in susps_map:
        depended_susps_list = \
            _get_top_n_depend_susps(s, susps_map, depended_map)
        depend_susps_list = \
            _get_top_n_depend_susps(s, susps_map, depend_map)
        stmt_features_map[s] = tuple(depended_susps_list[0: _FEATURE_TOP_N] +
                                     depend_susps_list[0: _FEATURE_TOP_N])
    return stmt_features_map


def get_mrank_features(susps_map, mmap_pairs, stmt_susps_list):
    top_n_count = 30
    top_n_method = 3
    s_method_map = {s: m for s, m in mmap_pairs}
    top_n_stmts = map(lambda x: x[0], stmt_susps_list[:top_n_count])
    dummy = 1
    method_stmts_ranks = []
    for k, g in groupby(top_n_stmts, lambda s: s_method_map.get(s, dummy)):
        if k != dummy:
            method_stmts_ranks.append([k, list(g)])
    append_rank(method_stmts_ranks, susps_map)
    mrank_features_map = {s: (0,) * top_n_method for s in susps_map}
    for m_stmts_rank in method_stmts_ranks:
        rank = m_stmts_rank[-1]
        if rank >= top_n_method:
            break
        stmts = m_stmts_rank[1]
        feature_v = [0] * top_n_method
        feature_v[rank] = 1
        for s in stmts:
            mrank_features_map[s] = tuple(feature_v)
    return mrank_features_map

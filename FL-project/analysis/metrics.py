import csv
import zipfile
from os.path import dirname, realpath, join

_FILE_DIR = dirname(realpath(__file__))
_BUGGY_LINES_DIR = join(_FILE_DIR, 'misc', 'stats', 'defects4j.buggy-lines')
_BUGGY_LINES_ZIP_FILE = join(_BUGGY_LINES_DIR, 'buggy-lines.zip')
_SLOC_CSV_FILE = join(_BUGGY_LINES_DIR, 'sloc.csv')
_SOURCE_CODE_LINES_ZIP_FILE = join(_BUGGY_LINES_DIR, 'source-code-lines.zip')


def _standardize_buggy_line_statement(line):
    s, ln = line.split('#')
    return s[:-5].replace('/', '.'), int(ln)


def _load_exact_buggy_lines(zf, bug, compressed_files):
    buggy_lines = set([])
    omission_lines = {}
    omission_candidates = set([])
    buggy_lines_file = bug + '.buggy.lines'
    candidates_file = bug + '.candidates'
    if buggy_lines_file in compressed_files:
        lines = [l.rstrip('\n')
                 for l in
                 zf.open(buggy_lines_file).read()
                     .decode(encoding='iso-8859-1').split('\n')]
        lines = [l for l in lines if len(l) > 0]
        for line in lines:
            src_file, line_number, statement = line.split('#', maxsplit=2)
            statement = statement.strip(' ')
            location = (src_file[:-5].replace('/', '.'), int(line_number))
            if statement == 'FAULT_OF_OMISSION':
                omission_lines[location] = set([])
            else:
                buggy_lines.add(location)
    if candidates_file in compressed_files:
        lines = [l.rstrip('\n')
                 for l in
                 zf.open(candidates_file).read()
                     .decode(encoding='iso-8859-1').split('\n')]
        lines = [l for l in lines if len(l) > 0]
        for line in lines:
            buggy_line_omission, buggy_line_candidate = line.split(',')
            omission_location = _standardize_buggy_line_statement(
                buggy_line_omission)
            candidate_location = _standardize_buggy_line_statement(
                buggy_line_candidate)
            if omission_location in omission_lines:
                omission_lines[omission_location].add(candidate_location)
                omission_candidates.add(candidate_location)
    return buggy_lines, omission_lines, omission_candidates


def _load_buggy_lines():
    zf = zipfile.ZipFile(_BUGGY_LINES_ZIP_FILE)
    compressed_files = zf.namelist()
    bugs = set([x.split('.')[0] for x in compressed_files])
    buggy_lines_map = {}
    for b in bugs:
        project, bug_id = b.split('-')
        bug_id = int(bug_id)
        b, o, oc = _load_exact_buggy_lines(zf, b, compressed_files)
        buggy_lines_map[(project, bug_id)] = (b, o, oc)
    return buggy_lines_map


def _load_sloc_map():
    r = csv.reader(open(_SLOC_CSV_FILE))
    next(r, None)  # skip header
    sloc_map = {}
    for row in r:
        sloc_map[(row[0], int(row[1]))] = (int(row[2]), int(row[3]))
    return sloc_map


def _load_lines_stmt_map(zf, b):
    lines_stmt_map = {}
    for l in zf.open(b + 'b.source-code.lines') \
            .read().decode('utf-8').split('\n'):
        if not l:
            continue
        line, stmt = list(map(_standardize_buggy_line_statement, l.split(':')))
        lines_stmt_map[line] = stmt
    return lines_stmt_map


def _load_buggy_stmts_map():
    zf = zipfile.ZipFile(_SOURCE_CODE_LINES_ZIP_FILE)
    compressed_files = zf.namelist()
    buggy_lines_map = _load_buggy_lines()
    bugs = set([x.split('b.')[0] for x in compressed_files])
    buggy_stmts_map = {}
    for b in bugs:
        lines_stmt_map = _load_lines_stmt_map(zf, b)

        def line2stmt(line):
            if line not in lines_stmt_map:
                return line
            else:
                return lines_stmt_map[line]

        project, bid = b.split('-')
        bid = int(bid)
        buggy_lines = buggy_lines_map[project, bid]
        buggy_stmts = [set(map(line2stmt, bls)) for bls in buggy_lines]
        buggy_stmts_map[project, bid] = buggy_stmts
    return buggy_stmts_map


# _BUGGY_LINES_MAP = _load_buggy_stmts_map()
_BUGGY_LINES_MAP = _load_buggy_lines()
_SLOC_MAP = _load_sloc_map()


def get_buggy_lines_map():
    return _BUGGY_LINES_MAP


def _standardize_string_statement(s):
    c, l = s.split('#')
    return c, int(l)


def is_omission_fault(project, bug_id):
    _, omission_lines, _ = _BUGGY_LINES_MAP[
        (project, bug_id)]
    return len(omission_lines) > 0


def continuous_multiple(arr):
    arr = list(arr)
    r = arr[0]
    for t in arr[1:]:
        r *= t
    return r


def nCr(n, r):
    r = min(r, n - r)
    if r == 0:
        return 1
    numer = continuous_multiple(range(n, n - r, -1))
    demon = continuous_multiple(range(1, r + 1))
    return numer // demon


def E_inspect(st, en, nf):
    expected = float(st)
    n = en - st + 1
    for k in range(1, n - nf + 1):
        term = float(nCr(n - k - 1, nf - 1) * k) / nCr(n, nf)
        expected += term
    return expected


def collect_statistics(project, bug_id, rank_list_file, *, method_map_file=None,
                       top_n, top_ln, wet_n, ctop_ln):
    buggy_lines, _, omission_candidates = _BUGGY_LINES_MAP[
        (project, bug_id)]
    faulty_elements = buggy_lines.union(omission_candidates)

    top_rank = None
    top_line_no = None
    ctop_line_no = None
    is_top_n = [False] * len(top_n)
    is_top_ln = [False] * len(top_ln)
    is_ctop_ln = [False] * len(ctop_ln)
    wet_s_n = [0] * len(wet_n)
    e_inspect = None

    rk_lines = [
        l.rstrip('\n').split(' ', 2)
        for l in
        open(rank_list_file).readlines()
    ]

    ranked_elements = [
        (float(l[0]), _standardize_string_statement(l[1]), eval(l[2]))
        for l
        in rk_lines
    ]

    if ranked_elements and method_map_file:
        mmap_pairs = set(tuple(l.rstrip('\n').split(',', maxsplit=1)) for l in
                         open(method_map_file).readlines())
        method_map = {_standardize_string_statement(s): m for s, m in
                      mmap_pairs}
        faulty_elements = set(
            map(lambda x: method_map.get(x, x), faulty_elements))
        method_susps_sets = {m: set() for m in (
            set(map(lambda x: method_map.get(x[1], x[1]), ranked_elements)))}
        for (r, e, susps) in ranked_elements:
            method_susps_sets[method_map.get(e, e)].add(susps)
        method_rank_susps = []
        for method, susps_set in method_susps_sets.items():
            susps = max(susps_set)
            method_rank_susps.append([-1, method, susps])
        method_rank_susps.sort(key=lambda x: x[2], reverse=True)
        # print(len(method_rank_susps), project, bug_id)
        last_i, last_susp = 0, method_rank_susps[0][2]
        for i, (_, _, susp) in enumerate(method_rank_susps):
            if last_susp != susp:
                rk = (last_i + i - 1) / 2
                for j in range(last_i, i):
                    method_rank_susps[j][0] = rk
                last_i = i
                last_susp = susp
        for j in range(last_i, len(method_rank_susps)):
            rk = (last_i + len(method_rank_susps) - 1) / 2
            method_rank_susps[j][0] = rk
        ranked_elements = method_rank_susps

    pre_susps = None
    pre_line = -1
    for idx, (rank, element, suspicious) in enumerate(ranked_elements):
        if not pre_susps or pre_susps != suspicious:
            pre_susps = suspicious
            pre_line = idx + 1
        # is buggy line
        if element in faulty_elements:
            for i, n in enumerate(top_n):
                if rank + 1 <= n:
                    is_top_n[i] = True
            if not top_rank:
                top_rank = rank + 1
            for i, ln in enumerate(top_ln):
                if idx + 1 <= ln:
                    is_top_ln[i] = True
            if not top_line_no:
                top_line_no = idx + 1
            for i, ln in enumerate(ctop_ln):
                if pre_line <= ln:
                    is_ctop_ln[i] = True
            if not ctop_line_no:
                ctop_line_no = pre_line
            if not e_inspect:
                end = idx + 1
                count = 1
                while end < len(ranked_elements) \
                        and ranked_elements[end][0] == rank:
                    if ranked_elements[end][1] in faulty_elements:
                        count += 1
                    end += 1
                if end >= len(ranked_elements):
                    end = len(ranked_elements) - 1
                # print(rank_list_file, pre_line, end, count)
                e_inspect = E_inspect(pre_line, end, count)

    for i, ln in enumerate(wet_n):
        if top_line_no and ln >= top_line_no:
            wet_s_n[i] = top_line_no - 1
        else:
            wet_s_n[i] = ln

    len_rank = len(ranked_elements)

    return top_rank, top_line_no, is_top_n, is_top_ln, wet_s_n, \
           ctop_line_no, is_ctop_ln, e_inspect, len_rank


def report_metrics(formula, rank_list_files, *, prt_table=None,
                   show_top_bugs=False, method_map_dir=None, output_csv=None,
                   top_n=(1, 2, 3, 5, 10, 20),
                   top_ln=(1, 2, 3, 5, 10, 20),
                   wet_n=(1, 2, 3, 5, 10, 20),
                   ctop_ln=(1,),
                   e_inspect_n=(1, 3, 5)):
    if not rank_list_files or len(rank_list_files) == 0:
        raise ValueError('rank list files must not be empty')
    top_n_count = [0] * len(top_n)
    top_n_bugs = [set() for _ in top_n]
    top_ln_count = [0] * len(top_ln)
    ctop_ln_count = [0] * len(ctop_ln)
    ties_at_ln_bugs = [set() for _ in ctop_ln]
    total_wet_s_n = [0] * len(wet_n)
    bug_size = len(rank_list_files)
    exam_scores = []
    top_ranks = []
    len_ranks = []
    top_lines_no = []
    ctop_lines_no = []
    e_inspect_n_count = [0] * len(e_inspect_n)
    pb_id_list = []
    for project, bug_id, rank_list_file in rank_list_files:
        method_map_file = None
        if method_map_dir:
            method_map_file = join(method_map_dir,
                                   '%s-%s.mmap' % (project, bug_id))
        pb_id_list.append('%s-%s' % (project, bug_id))
        top_rank, top_line_no, is_top_n, is_top_ln, wet_s_n, \
        ctop_line_no, is_ctop_ln, e_inspect, len_rank = \
            collect_statistics(
                project, bug_id, rank_list_file,
                method_map_file=method_map_file,
                top_n=top_n,
                top_ln=top_ln,
                wet_n=wet_n, ctop_ln=ctop_ln)
        for i in range(len(top_n)):
            if is_top_n[i]:
                top_n_count[i] += 1
                top_n_bugs[i].add('%s-%s' % (project, bug_id))
        for i in range(len(top_ln)):
            if is_top_ln[i]:
                top_ln_count[i] += 1
        for i in range(len(ctop_ln)):
            if is_ctop_ln[i]:
                ctop_ln_count[i] += 1
                i_top = top_n.index(ctop_ln[i])
                if not is_top_n[i_top]:
                    ties_at_ln_bugs[i].add('%s-%s' % (project, bug_id))
        for i in range(len(wet_n)):
            total_wet_s_n[i] += wet_s_n[i]
        if top_rank:
            top_ranks.append(top_rank)
            exam_scores.append(top_rank / _SLOC_MAP[(project, bug_id)][1])
        else:
            r = (_SLOC_MAP[(project, bug_id)][0] + len_rank) / 2
            top_ranks.append(r)
            exam_scores.append(r / _SLOC_MAP[(project, bug_id)][1])
        len_ranks.append(len_rank)
        if top_line_no:
            top_lines_no.append(top_line_no)
        if ctop_line_no:
            ctop_lines_no.append(ctop_lines_no)
        if e_inspect:
            for i in range(len(e_inspect_n)):
                if e_inspect < e_inspect_n[i] + 0.01:
                    e_inspect_n_count[i] += 1
    if output_csv:
        with open(output_csv, 'w') as f:
            t_n = [1, 5, 10]
            f.write('project-bug-id,%s-top-rank' % formula)
            for t in t_n:
                f.write(',%s-top-%d?' % (formula, t))
            f.write('\n')
            for pb_id, top_r in zip(pb_id_list, top_ranks):
                f.write('%s,%s' % (pb_id, top_r))
                for t in t_n:
                    f.write(',%s' % (top_r <= t))
                f.write('\n')
    elif prt_table:
        print_metrics_table(formula, prt_table, bug_size, top_lines_no, top_ln,
                            top_ln_count, top_n, top_n_count, top_ranks,
                            ctop_ln, ctop_ln_count, exam_scores,
                            e_inspect_n, e_inspect_n_count, len_ranks)
    else:
        print_metrics(formula, bug_size, exam_scores, show_top_bugs,
                      top_lines_no, top_ln, top_ln_count, top_n, top_n_bugs,
                      top_n_count, top_ranks, total_wet_s_n, wet_n,
                      ctop_ln, ties_at_ln_bugs, e_inspect_n, e_inspect_n_count)


def print_metrics(formula, bug_size, exam_scores, show_top_bugs, top_lines_no,
                  top_ln, top_ln_count, top_n, top_n_bugs, top_n_count,
                  top_ranks, total_wet_s_n, wet_n, ctop_ln, ties_at_ln_bugs,
                  e_inspect_n, e_inspect_n_count):
    print('[formula]: ' + formula)
    print('  * Bug size: %d' % bug_size)
    # print('  * Mean EXAM score: %.4f' % (sum(exam_scores) / bug_size))
    # print('  * Median EXAM score: %.4f' % sorted(exam_scores)[bug_size // 2])
    # print('  * 70th percentile top rank: %.1f' % sorted(top_ranks)[
    #     int(bug_size * .7)])
    print('  * MRR@TOP5: %.3f' % (sum(map(lambda x: (1.0 / x) if x <= 5 else 0,
                                          top_ranks)) / bug_size))
    print('  * MRR@LINE5: %.3f' % (sum(map(lambda x: (1.0 / x) if x <= 5 else 0,
                                           top_lines_no)) / bug_size))
    print('  * Top-N', end='')
    for i in range(len(top_n)):
        print(', N=%d: %d(%.1f%%)' % (
            top_n[i], top_n_count[i], top_n_count[i] * 100 / bug_size),
              end='')
    print()
    print('  * E-inspect-N', end='')
    for i in range(len(e_inspect_n)):
        print(', N=%d: %d(%.1f%%)' % (
            e_inspect_n[i], e_inspect_n_count[i],
            e_inspect_n_count[i] * 100 / bug_size),
              end='')
    print()
    print('  * AT-N', end='')
    for i in range(len(top_ln)):
        print(', N=%d: %d(%.1f%%)' % (
            top_ln[i], top_ln_count[i], top_ln_count[i] * 100 / bug_size),
              end='')
    print()
    print('  * WET-N', end='')
    for i in range(len(wet_n)):
        print(', N=%d: %.1f%%' % (
            wet_n[i], total_wet_s_n[i] * 100 / wet_n[i] / bug_size
        ), end='')
    print()
    if show_top_bugs:
        for i in range(len(top_n)):
            print('  * Top-%d' % top_n[i], end='')
            if i > 0:
                print('(but not Top-%d)' % top_n[i - 1], end='')
            print(':')
            if i > 0:
                buffer = list(top_n_bugs[i].difference(top_n_bugs[i - 1]))
            else:
                buffer = list(top_n_bugs[i])
            print(sorted(buffer))
        for i in range(len(ctop_ln)):
            print('  * Ties at Line-%d:' % ctop_ln[i])
            print(sorted(ties_at_ln_bugs[i]))


_TABLE_FIELD_NAMES = [
    'FORMULA',
    'TOP-1',
    'TOP-2',
    'TOP-3',
    'TOP-5',
    # 'MRR@TOP5',
    'REACH-1',
    # 'AT-1',
    'EXAM',
    # 'MRR@LINE5',
    'E-inspect-1',
    'E-inspect-3',
    'E-inspect-5',
    # 'TOP-1%',
    # 'TOP-2%',
    # 'TOP-3%',
    # 'TOP-4%',
    # 'TOP-5%',
    # 'TOP-10%',
    # 'TOP-1%(max 150)',
    # 'TOP-2%(max 150)',
    # 'TOP-3%(max 150)',
    # 'TOP-4%(max 150)',
    # 'TOP-5%(max 150)',
    # 'TOP-10%(max 150)',
    # 'size-10%(max 150)',
    # 'rank size',
    # 'Rank-70%',
    # 'Rank-80%',
    # 'Rank-90%',
    'SIZE'
]


def create_pretty_table():
    from prettytable import PrettyTable
    pt = PrettyTable()
    pt.field_names = _TABLE_FIELD_NAMES
    return pt


def print_metrics_table(formula, pt, bug_size, top_lines_no, top_ln,
                        top_ln_count, top_n, top_n_count, top_ranks, ctop_ln,
                        ctop_ln_count, exam_scores, e_inspect_n,
                        e_inspect_n_count, len_ranks):
    metric_map = {}
    metric_map['FORMULA'] = formula
    metric_map['SIZE'] = bug_size
    # metric_map['MRR@LINE5'] = '%.3f' % (sum(
    #     map(lambda x: (1.0 / x) if x <= 5 else 0, top_lines_no)) / bug_size)
    # metric_map['MRR@TOP5'] = '%.3f' % (sum(
    #     map(lambda x: (1.0 / x) if x <= 5 else 0, top_ranks)) / bug_size)
    metric_map['EXAM'] = '%.3f' % (sum(exam_scores) / bug_size)
    for i in range(len(top_n)):
        metric_map['TOP-%s' % top_n[i]] = '%d(%.1f%%)' % (
            top_n_count[i], top_n_count[i] * 100 / bug_size)
    # for i in range(len(top_ln)):
    #     metric_map['AT-%d' % top_ln[i]] = '%d(%.1f%%)' % (
    #         top_ln_count[i], top_ln_count[i] * 100 / bug_size)
    for i in range(len(ctop_ln)):
        metric_map['REACH-%d' % ctop_ln[i]] = '%d(%.1f%%)' % (
            ctop_ln_count[i], ctop_ln_count[i] * 100 / bug_size)
    for i in range(len(e_inspect_n)):
        metric_map['E-inspect-%d' % e_inspect_n[i]] = '%d(%.1f%%)' % (
            e_inspect_n_count[i], e_inspect_n_count[i] * 100 / bug_size)
    # for percent in [0.7, 0.8, 0.9]:
    #     metric_map['Rank-%d%%' % (percent * 100)] = '%d' % sorted(top_ranks)[
    #         int(bug_size * percent)]
    # for percent in [0.01, 0.02, 0.03, 0.04, 0.05, 0.1]:
    #     cnt_at = sum(
    #         top < l * percent for top, l in zip(top_ranks, len_ranks))
    #     metric_map['TOP-%d%%' % (percent * 100)] = '%d(%.1f%%)' % (
    #         cnt_at, cnt_at / bug_size * 100)
    # for percent in [0.01, 0.02, 0.03, 0.04, 0.05, 0.1]:
    #     cnt_at = sum(
    #         top < min(l * percent, 150) for top, l in zip(top_ranks, len_ranks))
    #     metric_map['TOP-%d%%(max 150)' % (percent * 100)] = '%d(%.1f%%)' % (
    #         cnt_at, cnt_at / bug_size * 100)
    # metric_map['rank size'] = '%.1f' % (sum(len_ranks) / bug_size)
    metric_map['size-10%(max 150)'] = '%.1f' % (
            sum(map(lambda x: min(x, 150), len_ranks)) / bug_size)
    pt.add_row([metric_map[f] for f in _TABLE_FIELD_NAMES])

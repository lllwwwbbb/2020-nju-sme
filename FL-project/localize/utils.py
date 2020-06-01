from os.path import join, exists


def read_mutation_log_file(mutation_log_file):
    if not exists(mutation_log_file):
        return None
    with open(mutation_log_file) as f:
        # [[id, class, method, line number, instruction number, details]...]
        logs = [l.rstrip('\n').split(',') for l in f.readlines()]
        return logs


def read_mutation_logs(context):
    mutation_log_file = join(context['dir.mutants'], 'mutation.log')
    return read_mutation_log_file(mutation_log_file)


def read_relevant_test_report(results_dir, mutant_id=None, *,
                              timeout_as_fail=False):
    origin_report_map = read_relevant_test_report_origin(results_dir, mutant_id)
    if not origin_report_map:
        return None
    report_map = {}
    for tc in origin_report_map:
        origin_report = origin_report_map[tc]
        if origin_report[0] == 'TIMEOUT' and not timeout_as_fail:
            continue
        report = list(origin_report)
        report[0] = (origin_report[0] == 'PASS')
        report_map[tc] = report
    return report_map


def read_relevant_test_report_origin(results_dir, mutant_id=None):
    if mutant_id:
        result_dir = join(results_dir, str(mutant_id))
    else:
        result_dir = join(results_dir, 'origin')
    relevant_test_report_file = join(result_dir, 'relevant-tests.report')
    if not exists(relevant_test_report_file):
        return None
    report_map = {}
    with open(relevant_test_report_file) as f:
        line = f.readline()
        while line:
            line = line.rstrip('\n')
            if line.startswith('--- '):
                test_case, if_pass = line[4:].split(',', maxsplit=1)
                if if_pass == 'PASS':
                    report_map[test_case] = (if_pass,)
                else:  # if_pass = FAIL, TIMEOUT
                    line = f.readline()
                    cause_lines = []
                    while line:
                        line = line.rstrip('\n')
                        if len(line) > 0:
                            cause_lines.append(line)
                        else:
                            break
                        line = f.readline()
                    report_map[test_case] = (if_pass, '\n'.join(cause_lines))
            line = f.readline()
    return report_map

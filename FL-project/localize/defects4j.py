import subprocess
from os import listdir
from os.path import exists, join, isdir, isfile, dirname, realpath, relpath

from loguru import logger


def _handle_and_log_called_process_error(e):
    if not isinstance(e, subprocess.CalledProcessError):
        raise RuntimeError('never reach here')

    logger.trace(
        'failed command is {}, return code {}' + ' '.join(e.cmd),
        e.returncode)
    if e.stdout:
        logger.trace('stdout:\n{}', e.stdout)
    if e.stderr:
        logger.trace('stderr:\n{}', e.stderr)


_FILE_DIR = dirname(realpath(__file__))
_DEFECTS4J_DEFAULT_DIR = join(dirname(_FILE_DIR), 'defects4j')


def get_default_defects4j_instance():
    return Defects4J(_DEFECTS4J_DEFAULT_DIR, validate=True)


class Defects4J:
    @staticmethod
    def _validate_defects4j_files_under(defects4j_path, *, revision=None,
                                        tag=None):
        logger.info('validate defects4j files under {}, revision {}, tag {}',
                    defects4j_path, revision, tag)
        try:
            # check revision or tag if revision or tag is not None
            if tag is not None:
                if not isinstance(tag, str):
                    logger.warning('tag must be a string, not {}, skip',
                                   type(tag).__name__)
                else:
                    current_tag = subprocess.check_output(
                        ['git', 'tag', '--points-at', 'HEAD'],
                        cwd=defects4j_path, universal_newlines=True)
                    if tag != current_tag:
                        logger.error('tag mismatch, expect {}, but got {}',
                                     tag, current_tag)
                        return False
            elif revision is not None:
                if not isinstance(revision, str):
                    logger.warning('revision must be a string, not {}, skip',
                                   type(revision).__name__)
                else:
                    current_revision = subprocess.check_output(
                        ['git', 'rev-parse', '--verify', 'HEAD'],
                        cwd=defects4j_path, universal_newlines=True)
                    if revision != current_revision:
                        logger.error('commit mismatch, expect {}, but got {}',
                                     revision, current_revision)
                        return False

            # ensure files are not changed
            changed_files = subprocess.check_output(
                ['git', 'diff', '--name-only'],
                cwd=defects4j_path, universal_newlines=True) \
                .split('\n')
            changed_files = [f for f in changed_files if f != '']
            if len(changed_files) > 0:
                logger.error('files under Defects4J path {} are changed:\n'
                             '{}',
                             defects4j_path, '\n'.join(changed_files))
                return False

            # ensure project repos has be initialized by check if
            # directories are exists
            third_party_files = ['project_repos', 'major',
                                 'framework/lib/test_generation',
                                 'framework/lib/build_systems',
                                 'framework/lib/analyzer.jar']
            for file in third_party_files:
                if not exists(join(defects4j_path, file)):
                    logger.error('file {} does not exists under {}', file,
                                 defects4j_path)
                    return False
        except subprocess.CalledProcessError as e:
            _handle_and_log_called_process_error(e)
            return False

        return True

    def __init__(self, defects4j_root_path, *, validate=False,
                 validate_args=None):
        if validate_args is None:
            validate_args = {}
        if validate:
            self._validate_defects4j_files_under(
                defects4j_root_path, **validate_args)

        self.root_directory = defects4j_root_path
        self._load_project_details()

    def _load_project_details(self):
        projects_directory = join(self.root_directory, 'framework/projects')
        self.projects = sorted(list(
            filter(lambda f: f != 'lib' and isdir(join(projects_directory, f)),
                   listdir(projects_directory))))
        self.bugs = [
            len(open(
                join(projects_directory, project, 'commit-db')).readlines())
            for project in self.projects
        ]

    def list_bugs(self):
        for idx, project in enumerate(self.projects):
            for bug_id in range(1, self.bugs[idx] + 1):
                yield (project, bug_id)

    def checkout_project(self, project, bug_id, target_directory):
        logger.info('checkout {}-{} to {}', project, bug_id, target_directory)
        try:
            subprocess.check_call(
                ['framework/bin/defects4j', 'checkout', '-p', project, '-v',
                 '%db' % bug_id, '-w', target_directory],
                cwd=self.root_directory)
        except subprocess.CalledProcessError as e:
            _handle_and_log_called_process_error(e)
            return False
        return True

    def export_test_classpath(self, project_directory):
        try:
            classpath = subprocess.check_output(
                ['framework/bin/defects4j', 'export', '-p', 'cp.test',
                 '-w', project_directory],
                cwd=self.root_directory, universal_newlines=True)
            assert classpath != ''
            classpath = classpath.split(':')
            return classpath
        except subprocess.CalledProcessError as e:
            _handle_and_log_called_process_error(e)
            return None

    def export_bin_class_dir(self, project_directory):
        try:
            class_dir = subprocess.check_output(
                ['framework/bin/defects4j', 'export', '-p', 'dir.bin.classes',
                 '-w', project_directory],
                cwd=self.root_directory, universal_newlines=True)
            assert class_dir != ''
            return class_dir
        except subprocess.CalledProcessError as e:
            _handle_and_log_called_process_error(e)
            return None

    def export_bin_test_dir(self, project_directory):
        try:
            test_dir = subprocess.check_output(
                ['framework/bin/defects4j', 'export', '-p', 'dir.bin.tests',
                 '-w', project_directory],
                cwd=self.root_directory, universal_newlines=True)
            assert test_dir != ''
            return test_dir
        except subprocess.CalledProcessError as e:
            _handle_and_log_called_process_error(e)
            return None

    def compile_project(self, project_directory):
        logger.info('compile project under {}', project_directory)
        try:
            subprocess.check_call(['framework/bin/defects4j', 'compile', '-w',
                                   project_directory], cwd=self.root_directory)
        except subprocess.CalledProcessError as e:
            _handle_and_log_called_process_error(e)
            return False
        return True

    def list_trigger_test_cases(self, project, bug_id):
        trigger_tests_directory = join(
            self.root_directory,
            'framework/projects', project, 'trigger_tests')
        test_cases = [
            l[4:] for l in
            filter(lambda l: l.startswith('--- '),
                   [
                       l.rstrip('\n').strip() for l in
                       open(
                           join(trigger_tests_directory,
                                str(bug_id))
                       ).readlines()
                   ])
        ]
        return set(test_cases)

    def list_trigger_test_classes(self, project, bug_id):
        test_cases = self.list_trigger_test_cases(project, bug_id)
        return set([t.split('::')[0] for t in test_cases])

    def list_relevant_test_classes(self, project, bug_id):
        return set([
            l.rstrip('\n') for l in
            open(
                join(self.root_directory,
                     'framework/projects/%s/relevant_tests/%d' % (
                         project, bug_id))
            ).readlines()
        ])

    def list_src_loaded_classes(self, project, bug_id):
        return set([
            l.rstrip('\n') for l in
            open(
                join(self.root_directory,
                     'framework/projects/%s/loaded_classes/%d.src' % (
                         project, bug_id))
            ).readlines()
        ])

    def list_test_loaded_classes(self, project, bug_id):
        return set([
            l.rstrip('\n') for l in
            open(
                join(self.root_directory,
                     'framework/projects/%s/loaded_classes/%d.test' % (
                         project, bug_id))
            ).readlines()
        ])

    def list_modified_classes(self, project, bug_id):
        return set([
            l.rstrip('\n') for l in
            open(
                join(self.root_directory,
                     'framework/projects/%s/modified_classes/%d.src' % (
                         project, bug_id))
            ).readlines()
        ])

    @staticmethod
    def resolve_property_file(project_directory):
        property_file = join(project_directory, 'defects4j.build.properties')
        if not isfile(property_file):
            return None
        lines = [l.rstrip('\n') for l in open(property_file).readlines()][1:]
        property_map = dict(
            [(x[0], x[1]) for x in [l.split('=', maxsplit=1) for l in lines]])
        if 'd4j.classes.modified' in property_map:
            property_map['d4j.classes.modified'] = property_map[
                'd4j.classes.modified'].split(',')
        if 'd4j.tests.trigger' in property_map:
            property_map['d4j.tests.trigger'] = property_map[
                'd4j.tests.trigger'].split(',')
        return property_map

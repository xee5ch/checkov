import logging
import sys
import os
import importlib


class Registry(object):
    checks = {}

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.checks = {}

    def register(self, check):
        for entity in check.supported_entities:
            if entity not in self.checks.keys():
                self.checks[entity] = []
            self.checks[entity].append(check)

    def get_checks(self, entity):
        if entity in self.checks.keys():
            return self.checks[entity]
        return []

    def scan(self, block, scanned_file, skipped_checks):
        entity = list(block.keys())[0]
        entity_conf = block[entity]
        results = {}
        checks = self.get_checks(entity)
        for check in checks:
            skip_info = {}
            if skipped_checks:
                if check.id in [x['id'] for x in skipped_checks]:
                    skip_info = [x for x in skipped_checks if x['id'] == check.id][0]
            entity_name = list(entity_conf.keys())[0]
            entity_conf_def = entity_conf[entity_name]
            self.logger.debug("Running check: {} on file {}".format(check.name, scanned_file))
            result = check.run(scanned_file=scanned_file, entity_configuration=entity_conf_def,
                               entity_name=entity_name, entity_type=entity, skip_info=skip_info)

            results[check] = result
        return results

    def _directory_has_init_py(self, directory):
        """ Check if a given directory contains a file named __init__.py.

        __init__.py is needed to ensure the directory is a Python module, thus
        can be imported.
        """
        if os.path.exists("{}/__init__.py".format(directory)):
            return True
        return False

    def _file_can_be_imported(self, entry):
        """ Verify if a directory entry is a non-magic Python file."""
        if entry.is_file() and not entry.name.startswith('__') and entry.name.endswith('.py'):
            return True
        return False

    def load_external_checks(self, directory):
        """ Browse a directory looking for .py files to import.

        Log an error when the directory does not contains an __init__.py or
        when a .py file has syntax error
        """
        directory = os.path.expanduser(directory)
        self.logger.debug("Loading external checks from {}".format(directory))
        sys.path.insert(1, directory)

        with os.scandir(directory) as directory_content:
            if not self._directory_has_init_py(directory):
                self.logger.info("No __init__.py found in {}. Cannot load any check here.".format(directory))
            else:
                for entry in directory_content:
                    if self._file_can_be_imported(entry):
                        check_name = entry.name.replace('.py', '')
                        try:
                            self.logger.debug("Importing external check '{}'".format(check_name))
                            importlib.import_module(check_name)
                        except SyntaxError as e:
                            self.logger.error(
                                "Cannot load external check '{check_name}' from {check_full_path} : {error_message} ("
                                "{error_line}:{error_column}) "
                                    .format(
                                    check_name=check_name,
                                    check_full_path=e.args[1][0],
                                    error_message=e.args[0],
                                    error_line=e.args[1][1],
                                    error_column=e.args[1][2]
                                )
                            )

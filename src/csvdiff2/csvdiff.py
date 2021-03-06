#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import abc
import csv
import functools
import logging
import os
import sys
import timeit
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


# ----------------------------------------------------------------------------------------------------------------------
#  Decorators
# ----------------------------------------------------------------------------------------------------------------------

def show_execution_time():

    def _execution_time(func):

        def wrapper(*args, **kwargs):

            start = timeit.default_timer()

            func(*args, **kwargs)

            elapsed_time = timeit.default_timer() - start
            print
            print("elapsed_time={0}".format(elapsed_time) + "[sec]")
            print

        return wrapper

    return _execution_time


def spacing_before(number_of_lines):

    number_of_lines = number_of_lines or 1

    def _spacing_before(func):

        def wrapper(*args, **kwargs):

            for i in range(number_of_lines):
                print('')

            func(*args, **kwargs)

        return wrapper

    return _spacing_before


# ----------------------------------------------------------------------------------------------------------------------
#  Entrance
# ----------------------------------------------------------------------------------------------------------------------

# @show_execution_time()
def main():

    configure()

    context = context_from_arguments()
    show_context_for_debugging(context)

    try:
        run_in(context)
    except IndexError as e:
        logger.error('It is possible that the number of columns in the row is not aligned. Please check the csv data. If not, please file an issue. [{}, description={}]'.format(type(e), e))
        sys.exit(1)


class App(type):

    VERSION = '1.0.0'


class LoggingConfig(type):

    # If you want to debug, play with the CONSOLE_LEVEL or FILE_LEVEL.

    BASE_LEVEL = logging.DEBUG

    CONSOLE_LEVEL = logging.ERROR
    CONSOLE_FORMAT = '%(levelname)s: %(message)s'

    FILE_LEVEL = logging.WARNING
    FILE_FORMAT = '%(asctime)s: %(levelname)s: %(message)s'
    FILE_PATH = 'csvdiff.log'


logger = logging.getLogger(__name__)


def configure():

    logging.basicConfig(level=LoggingConfig.BASE_LEVEL)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(LoggingConfig.CONSOLE_LEVEL)
    stream_handler.setFormatter(logging.Formatter(LoggingConfig.CONSOLE_FORMAT))

    file_handler = logging.FileHandler(filename=LoggingConfig.FILE_PATH, mode='w')
    file_handler.setLevel(LoggingConfig.FILE_LEVEL)
    file_handler.setFormatter(logging.Formatter(LoggingConfig.FILE_FORMAT))

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    logger.propagate = False


# ----------------------------------------------------------------------------------------------------------------------
#  Context Preparation
# ----------------------------------------------------------------------------------------------------------------------

def context_from_arguments():

    def arg_type_matching_key_in_csv(x):
        return map(MatchingKeyInfo, x.split(','))

    def arg_type_int_in_csv(x):
        return map(int, x.split(','))

    parser = ArgumentParser(prog='csv-diff-python2@blue-monk', formatter_class=ArgumentDefaultsHelpFormatter)

    # Program name & Version -------------------------------------------------------------------------------------------
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(App.VERSION))

    # Input CSV file paths ---------------------------------------------------------------------------------------------
    parser.add_argument('lhs_file_name', type=str, help='Absolute/Relative path to left-hand side file.')
    parser.add_argument('rhs_file_name', type=str, help='Absolute/Relative path to right-hand side file.')

    # Matching conditions ----------------------------------------------------------------------------------------------
    parser.add_argument('-k', '--matching-keys', type=arg_type_matching_key_in_csv, default='0',
                        help='Matching key indices(from 0) for Input CSV in CSV format. For non-fixed length numbers, specify the number of digits after ":". e.g.: 0:8,3')
    parser.add_argument('-u', '--unique-key', default=False, action='store_true',
                        help="Specify if the matching key is unique. Then, if it detects that the matching key is not unique, an error will occur.")
    parser.add_argument('-i', '--ignore-columns', type=arg_type_int_in_csv, default=[],
                        help='Specify the index of the column to be ignored in CSV format. e.g.: 3,7')

    # Report styles ----------------------------------------------------------------------------------------------------
    parser.add_argument('-v', '--vertical-style', default=False, action='store_true',
                        help='Report in vertical style. If not specified, report in horizontal(two facing) style.')

    parser.add_argument('-c', '--show-count', default=False, action='store_true',
                        help='Report the number of differences. Treat this as True if neither -d nor -a is specified.')

    display_group = parser.add_mutually_exclusive_group()
    display_group.add_argument('-d', '--show-difference-only', default=False, action='store_true',
                               help='Report the lines with the difference. Can be used with option -c. Cannot be used with option -a.')
    display_group.add_argument('-a', '--show-all-lines', action='store_true',
                               help='Report on all lines. Can be used with option -c. Cannot be used with option -d.')

    parser.add_argument('-x', '--show-context-from-arguments', default=False, action='store_true',
                        help='Report the context generated from the arguments and CSV sniffing.')

    # CSV analysis conditions ------------------------------------------------------------------------------------------
    parser.add_argument('-H', '--header', type=str, default=None, choices=['n', 'y'],
                        help='If specified, this specification will be enforced.')

    parser.add_argument('-S', '--sniffing-size', type=str, default=4096,
                        help="If csv sniffing fails, try specifying a size larger than 4096. Or Explicitly specify CSV file conditions like '--column-separator-for-lhs TAB'. Check help with -h option.")

    parser.add_argument('-F', '--force-individual-specs', action='store_true',
                        help="If you don't want to rely on csv sniffing, specify it, and then specify --column-separator and so on separately.")

    parser.add_argument('--column-separator', type=str, default=None, choices=['COMMA', 'TAB', 'SEMICOLON'],
                        help='Process both sides CSV file using the specified column delimiter.')

    parser.add_argument('--line-separator', type=str, default=None, choices=['LF', 'CRLF'],
                        help='Process both sides CSV file using the specified line separator.')

    parser.add_argument('--quote-char', type=str, default=None, choices=['"', "'"],
                        help='Process both sides CSV file using the specified quote character.')

    parser.add_argument('--no-skip-space-after-column-separator', action='store_true',
                        help='Specify when you want to treat the space immediately after the separator as data for the both sides CSV file.')

    # CSV analysis conditions by left and right ------------------------------------------------------------------------
    parser.add_argument('--column-separator-for-lhs', type=str, default="COMMA", choices=['COMMA', 'TAB', 'SEMICOLON'],
                        help='Process left-hand side CSV file using the specified column delimiter.')

    parser.add_argument('--column-separator-for-rhs', type=str, default="COMMA", choices=['COMMA', 'TAB', 'SEMICOLON'],
                        help='Process right-hand side CSV file using the specified column delimiter.')

    parser.add_argument('--line-separator-for-lhs', type=str, default="LF", choices=['LF', 'CRLF'],
                        help='Process left-hand side CSV file using the specified line separator.')

    parser.add_argument('--line-separator-for-rhs', type=str, default="LF", choices=['LF', 'CRLF'],
                        help='Process right-hand side CSV file using the specified line separator.')

    parser.add_argument('--quote-char-for-lhs', type=str, default='"', choices=['"', "'"],
                        help='Process left-hand side CSV file using the specified quote character.')

    parser.add_argument('--quote-char-for-rhs', type=str, default='"', choices=['"', "'"],
                        help='Process right-hand side CSV file using the specified quote character.')

    parser.add_argument('--no-skip-space-after-column-separator-for-lhs', default=False, action='store_true',
                        help='Specify when you want to treat the space immediately after the separator as data for the CSV file on the left side.')

    parser.add_argument('--no-skip-space-after-column-separator-for-rhs', default=False, action='store_true',
                        help='Specify when you want to treat the space immediately after the separator as data for the CSV file on the right side.')

    # ------------------------------------------------------------------------------------------------------------------

    return Context(parser.parse_args())


class Context:

    LINE_SEPARATOR_s = {
        "CR": '\r',
        "LF": '\n',
        "CRLF": '\r\n',
        None: '<None>',
    }

    COLUMN_SEPARATOR_s = {
        "COMMA": ',',
        "TAB": '\t',
        "SEMICOLON": ';',
        None: '<None>',
    }

    def __init__(self, args):

        # Input CSV file paths ---------------------------------------------------------------------------------------------
        self.lhs_file_name = args.lhs_file_name
        self.rhs_file_name = args.rhs_file_name
        self.lhs_file_path = os.path.abspath(args.lhs_file_name)
        self.rhs_file_path = os.path.abspath(args.rhs_file_name)

        # Matching conditions ----------------------------------------------------------------------------------------------
        self.matching_key_codec = MatchingKeyCodec(args.matching_keys)
        self.key_should_be_unique = args.unique_key
        self.column_indices_to_ignore = args.ignore_columns

        # Report styles ----------------------------------------------------------------------------------------------------
        self.reports_in_vertical_style = args.vertical_style
        self.reports_in_horizontal_style = not args.vertical_style

        self.shows_count = args.show_count
        self.shows_difference_only = args.show_difference_only
        self.shows_all_lines = args.show_all_lines
        self.shows_details = True if self.shows_difference_only or self.shows_all_lines else False
        self.shows_context_from_arguments = args.show_context_from_arguments

        self.needs_size_info_for_padding = self.shows_details and self.reports_in_horizontal_style

        # CSV analysis conditions ------------------------------------------------------------------------------------------
        self.header = args.header
        self.first_row_is_header = None

        self.sniffing_size = args.sniffing_size

        self.forces_individual_specs = args.force_individual_specs

        if self.forces_individual_specs and args.column_separator:
            self.column_separator_for_lhs = self.COLUMN_SEPARATOR_s[args.column_separator]
            self.column_separator_for_rhs = self.COLUMN_SEPARATOR_s[args.column_separator]
        else:
            self.column_separator_for_lhs = self.COLUMN_SEPARATOR_s[args.column_separator_for_lhs]
            self.column_separator_for_rhs = self.COLUMN_SEPARATOR_s[args.column_separator_for_rhs]

        if self.forces_individual_specs and args.line_separator:
            self.line_separator_for_lhs = self.LINE_SEPARATOR_s[args.line_separator]
            self.line_separator_for_rhs = self.LINE_SEPARATOR_s[args.line_separator]
        else:
            self.line_separator_for_lhs = self.LINE_SEPARATOR_s[args.line_separator_for_lhs]
            self.line_separator_for_rhs = self.LINE_SEPARATOR_s[args.line_separator_for_rhs]

        if self.forces_individual_specs and args.quote_char:
            self.quote_char_for_lhs = args.quote_char
            self.quote_char_for_rhs = args.quote_char
        else:
            self.quote_char_for_lhs = args.quote_char_for_lhs
            self.quote_char_for_rhs = args.quote_char_for_rhs

        if self.forces_individual_specs and args.no_skip_space_after_column_separator:
            self.skips_space_after_column_separator_for_lhs = not args.no_skip_space_after_column_separator
            self.skips_space_after_column_separator_for_rhs = not args.no_skip_space_after_column_separator
        else:
            self.skips_space_after_column_separator_for_lhs = True
            self.skips_space_after_column_separator_for_rhs = True

        self._validate()
        self._normalize()

    def _validate(self):

        if not os.path.exists(self.lhs_file_path):
            logger.error('lhs_file_path not exists. [lhs_file_path={}]'.format(self.lhs_file_path))
            sys.exit(1)
        if not os.path.exists(self.rhs_file_path):
            logger.error('rhs_file_path not exists. [rhs_file_path={}]'.format(self.rhs_file_path))
            sys.exit(1)

        if not os.path.isfile(self.lhs_file_path):
            logger.error('lhs_file_path is not a file. [lhs_file_path={}]'.format(self.lhs_file_path))
            sys.exit(1)
        if not os.path.isfile(self.rhs_file_path):
            logger.error('rhs_file_path is not a file. [rhs_file_path={}]'.format(self.rhs_file_path))
            sys.exit(1)

    def _normalize(self):

        if not any([self.shows_count, self.shows_difference_only, self.shows_all_lines]):
            self.shows_count = True

    def display_string_for_column_separator(self, value):

        candidates = [k for k, v in self.COLUMN_SEPARATOR_s.items() if v == value]
        if candidates:
            return candidates[0]
        else:
            'undefined({})'.format(value)


def show_context_for_debugging(cxt):

    logger.debug('lhs_file_name={}'.format(cxt.lhs_file_name))
    logger.debug('rhs_file_name={}'.format(cxt.rhs_file_name))
    logger.debug('lhs_file_path={}'.format(cxt.lhs_file_path))
    logger.debug('rhs_file_path={}'.format(cxt.rhs_file_path))

    logger.debug('matching_key_codec={}'.format(cxt.matching_key_codec))
    logger.debug('key_should_be_unique={}'.format(cxt.key_should_be_unique))
    logger.debug('column_indices_to_ignore={}'.format(cxt.column_indices_to_ignore))

    logger.debug('reports_in_vertical_style={}'.format(cxt.reports_in_vertical_style))
    logger.debug('reports_in_horizontal_style={}'.format(cxt.reports_in_horizontal_style))
    logger.debug('shows_count={}'.format(cxt.shows_count))
    logger.debug('shows_difference_only={}'.format(cxt.shows_difference_only))
    logger.debug('shows_all_lines={}'.format(cxt.shows_all_lines))
    logger.debug('shows_context_from_arguments={}'.format(cxt.shows_context_from_arguments))
    logger.debug('needs_size_info_for_padding={}'.format(cxt.needs_size_info_for_padding))

    logger.debug('first_row_is_header={}'.format(cxt.first_row_is_header))
    logger.debug('sniffing_size={}'.format(cxt.sniffing_size))
    logger.debug('force_individual_specs={}'.format(cxt.forces_individual_specs))

    logger.debug('column_separator_for_lhs={}'.format(cxt.display_string_for_column_separator(cxt.column_separator_for_lhs)))
    logger.debug('column_separator_for_rhs={}'.format(cxt.display_string_for_column_separator(cxt.column_separator_for_rhs)))
    logger.debug('line_separator_for_lhs={}'.format(cxt.line_separator_for_lhs.encode('hex')))
    logger.debug('line_separator_for_rhs={}'.format(cxt.line_separator_for_rhs.encode('hex')))
    logger.debug('quote_char_for_lhs={}'.format(cxt.quote_char_for_lhs))
    logger.debug('quote_char_for_rhs={}'.format(cxt.quote_char_for_rhs))
    logger.debug('skips_space_after_column_separator_for_lhs={}'.format(cxt.skips_space_after_column_separator_for_lhs))
    logger.debug('skips_space_after_column_separator_for_rhs={}'.format(cxt.skips_space_after_column_separator_for_rhs))

    logger.debug('MatchingKeyCodec#END_of_KEY={}'.format(MatchingKeyCodec.END_of_KEY))


# ----------------------------------------------------------------------------------------------------------------------
#  Matching Key Treatment
# ----------------------------------------------------------------------------------------------------------------------

class MatchingKeyInfo:

    def __init__(self, specified_string):

        elements = filter(lambda x: x != '', specified_string.split(':'))

        index = elements.pop(0)
        self.index = self._transform_into_numeric(index, 'index')

        max_length = elements.pop(0) if elements else '0'
        self.max_length = self._transform_into_numeric(max_length, 'max_length')

    def __repr__(self):
        return '{}({!r}, {!r})'.format(self.__class__.__name__, self.index, self.max_length if self.max_length > 0 else '<not specified>')

    @classmethod
    def _transform_into_numeric(cls, value, name):

        if not value.isdigit():
            logger.error('MATCHING_KEY_INDICES should be a number. See also help. [specified {}={}]'.format(name, value))
            exit(1)

        return int(value)

    def key_for(self, row):
        return row[self.index].rjust(self.max_length, '0')


class MatchingKeyCodec:

    END_of_KEY = 'ZZZ'
    SEPARATOR = '..'

    def __init__(self, matching_key_info_list):
        self.matching_key_info_list = matching_key_info_list

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.matching_key_info_list)

    def managed_key_for(self, row):

        try:
            return functools.reduce(lambda making, matching_key: making + matching_key.key_for(row) + self.SEPARATOR,
                                    self.matching_key_info_list, self.SEPARATOR)
        except IndexError:
            logger.error('one of the indices specified for MATCHING_KEY_INDICES is out of range [MATCHING_KEY_INDICES={}, number of columns = {}, row={}]'.format(self.matching_key_info_list, len(row), row))
            exit(1)

    @property
    def matching_key_indices(self):
        return map(lambda matching_key_info: matching_key_info.index, self.matching_key_info_list)

    @classmethod
    def decode_key(cls, key):
        """ Leave the padding as it is. """
        return key.strip(cls.SEPARATOR).split(cls.SEPARATOR)


# ----------------------------------------------------------------------------------------------------------------------
#  Control and Determine if it exists only on the left, only on the right, or both
# ----------------------------------------------------------------------------------------------------------------------

def run_in(context):

    with open(context.lhs_file_path, mode='r') as lhs_csv,\
         open(context.rhs_file_path, mode='r') as rhs_csv:

        lhs_dialect, adjusted_context = CsvDialectFixer.fixed_dialect(context, lhs_csv, FileArrangement.LHS)
        rhs_dialect, adjusted_context = CsvDialectFixer.fixed_dialect(adjusted_context, rhs_csv, FileArrangement.RHS)

        csv_reader = CsvReader(lhs_csv, rhs_csv, lhs_dialect, rhs_dialect, adjusted_context)
        pre_scan_result = PreScanner.scan(adjusted_context, csv_reader)
        csv_reader.reset()

        detect_diff(adjusted_context, csv_reader, pre_scan_result)


def detect_diff(context, csv_reader, pre_scan_result):

    value_difference_detector = ValueDifferenceDetector(pre_scan_result.number_of_columns,
                                                        context.matching_key_codec.matching_key_indices,
                                                        context.column_indices_to_ignore)

    heading_reporter = HeadingReporter(context)
    detail_reporter = DetailReporter.Factory.reporter_for(context, pre_scan_result)
    count_reporter = CountReporter(context.shows_count)
    counter = count_reporter.counter

    heading_reporter.report_heading()
    detail_reporter.report_detail_heading()


    def existed_only_on_lhs(lhs_fact):
        counter.count_for_case_of_existed_only_on_lhs(lhs_fact.lhs_row_number)
        detail_reporter.report_case_of_existed_only_on_lhs(lhs_fact)

    def existed_on_both_sides(lhs_fact, rhs_fact):
        value_difference_result = value_difference_detector.detect_difference_between(lhs_fact.lhs_row, rhs_fact.rhs_row)
        counter.count_for_case_of_existed_on_both_sides(lhs_fact, rhs_fact, value_difference_result)
        detail_reporter.report_case_of_existed_on_both_sides(lhs_fact, rhs_fact, value_difference_result)

    def existed_only_on_rhs(rhs_fact):
        counter.count_for_case_of_existed_only_on_rhs(rhs_fact.rhs_row_number)
        detail_reporter.report_case_of_existed_only_on_rhs(rhs_fact)

    perform_key_matching(csv_reader, existed_only_on_lhs, existed_on_both_sides, existed_only_on_rhs)


    count_reporter.report_count()


def perform_key_matching(csv_reader, callback_for_lhs_only, callback_for_both_sides, callback_for_rhs_only):

    lhs_fact = csv_reader.read_lhs()
    rhs_fact = csv_reader.read_rhs()

    while lhs_fact.lhs_key != MatchingKeyCodec.END_of_KEY or rhs_fact.rhs_key != MatchingKeyCodec.END_of_KEY:

        if lhs_fact.lhs_key < rhs_fact.rhs_key:
            callback_for_lhs_only(lhs_fact)
            lhs_fact = csv_reader.read_lhs()

        elif lhs_fact.lhs_key == rhs_fact.rhs_key:
            callback_for_both_sides(lhs_fact, rhs_fact)
            lhs_fact = csv_reader.read_lhs()
            rhs_fact = csv_reader.read_rhs()

        elif lhs_fact.lhs_key > rhs_fact.rhs_key:
            callback_for_rhs_only(rhs_fact)
            rhs_fact = csv_reader.read_rhs()


# ----------------------------------------------------------------------------------------------------------------------
#  Value-Difference Detection
# ----------------------------------------------------------------------------------------------------------------------

class ValueDifferenceDetector:

    class ValueDifferenceResult:

        def __init__(self, different_column_indices):

            self.different_column_indices = different_column_indices

        @property
        def has_difference(self):
            return True if self.different_column_indices else False


    def __init__(self, number_of_columns, matching_key_indices, ignore_column_indices):

        self.column_indices = range(0, number_of_columns)
        logger.debug('column_indices={}'.format(self.column_indices))

        self.target_column_indices = set(self.column_indices) - set(matching_key_indices) - set(ignore_column_indices)
        logger.debug('target_column_indices={}'.format(self.target_column_indices))

    def detect_difference_between(self, lhs_row, rhs_row):

        different_column_indices = [index for index in self.target_column_indices if lhs_row[index] != rhs_row[index]]
        logger.debug('different_column_indices={}'.format(different_column_indices))
        return self.ValueDifferenceResult(different_column_indices)


# ----------------------------------------------------------------------------------------------------------------------
#  Reporting
# ----------------------------------------------------------------------------------------------------------------------

class PreScanner:

    class ScanResult:

        def __init__(self, number_of_columns, size_info_for_padding):
            self.number_of_columns = number_of_columns
            self.size_info_for_padding = size_info_for_padding

        @classmethod
        def for_lightly(cls, number_of_columns):
            return PreScanner.ScanResult(number_of_columns, None)

        @classmethod
        def for_deeply(cls, number_of_columns, lhs_max_row_number, lhs_max_row_length, rhs_max_row_number, rhs_max_row_length):
            size_info_for_padding = cls.SizeInfoForPadding(lhs_max_row_number, lhs_max_row_length, rhs_max_row_number, rhs_max_row_length)
            return PreScanner.ScanResult(number_of_columns, size_info_for_padding)


        class SizeInfoForPadding:

            def __init__(self, lhs_max_row_number, lhs_max_row_length, rhs_max_row_number, rhs_max_row_length):
                self.lhs_max_row_number = lhs_max_row_number
                self.lhs_max_row_length = lhs_max_row_length
                self.rhs_max_row_number = rhs_max_row_number
                self.rhs_max_row_length = rhs_max_row_length


    def __init__(self):
        pass

    @classmethod
    def scan(cls, context, csv_reader):

        if context.needs_size_info_for_padding:
            return PreScanner._scan_deeply(csv_reader)
        else:
            return PreScanner._scan_lightly(csv_reader)


    @classmethod
    def _scan_deeply(cls, csv_reader):
        """
        Notes
        -----
        Purpose of deep pre-scanning
            * Determine the number of columns for value difference detection
            * Get size information to format the horizontal report
        """
        start_ = timeit.default_timer()

        lhs_max_row_length, rhs_max_row_length = 0, 0

        lhs_fact = csv_reader.read_lhs()
        rhs_fact = csv_reader.read_rhs()

        number_of_columns = cls._determine_number_of_columns_from(lhs_fact, rhs_fact)

        while lhs_fact.lhs_key != MatchingKeyCodec.END_of_KEY:
            lhs_max_row_length = max(lhs_max_row_length, len(str(lhs_fact.lhs_row)))
            lhs_fact = csv_reader.read_lhs()

        while rhs_fact.rhs_key != MatchingKeyCodec.END_of_KEY:
            rhs_max_row_length = max(rhs_max_row_length, len(str(rhs_fact.rhs_row)))
            rhs_fact = csv_reader.read_rhs()

        lhs_max_row_number = csv_reader.lhs_csv_state.row_number
        rhs_max_row_number = csv_reader.rhs_csv_state.row_number
        logger.debug('lhs_max_row_number={}'.format(lhs_max_row_number))
        logger.debug('rhs_max_row_number={}'.format(rhs_max_row_number))

        elapsed_time_ = timeit.default_timer() - start_
        logger.debug("PreScanner#scan() elapsed_time:{0}".format(elapsed_time_) + "[sec]")
        return PreScanner.ScanResult.for_deeply(number_of_columns,
                                                lhs_max_row_number, lhs_max_row_length, rhs_max_row_number, rhs_max_row_length)

    @classmethod
    def _scan_lightly(cls, csv_reader):
        """
        Notes
        -----
        Purpose of light pre-scanning
            * Determine the number of columns for value difference detection

        Vertical reports do not require size information for formatting.
        """

        lhs_fact = csv_reader.read_lhs()
        rhs_fact = csv_reader.read_rhs()

        return PreScanner.ScanResult.for_lightly(cls._determine_number_of_columns_from(lhs_fact, rhs_fact))

    @classmethod
    def _determine_number_of_columns_from(cls, lhs_fact, rhs_fact):

        number_of_columns = 0
        if lhs_fact.lhs_row:
            number_of_columns = len(lhs_fact.lhs_row)
        elif rhs_fact.rhs_row:
            number_of_columns = len(rhs_fact.rhs_row)

        return number_of_columns


class Mark(type):

    LHS_ONLY = '<'
    RHS_ONLY = '>'
    HAS_DIFF = '!'
    NON_DIFF = ' '
    NON_DIFF_EXPRESSLY = '='


class HeadingReporter:

    def __init__(self, context):
        self.cxt = context


    def report_heading(self):

        self._report_title()

        if self.cxt.shows_context_from_arguments:
            self._report_context()

    @classmethod
    @spacing_before(1)
    def _report_title(cls):
        print('============ Report ============')

    @spacing_before(1)
    def _report_context(self):

        print('* Context')
        print('File Path on the Left-Hand Side: {}'.format(self.cxt.lhs_file_path))
        print('File Path on the Right-Hand Side : {}'.format(self.cxt.rhs_file_path))
        print('Matching Key Indices: {}'.format(self.cxt.matching_key_codec.matching_key_info_list))
        print('Matching Key Is Unique?: {}'.format(self.cxt.key_should_be_unique))
        print('Column Indices to Ignore: {}'.format(self.cxt.column_indices_to_ignore))
        print('with Header?: {}'.format(self.cxt.first_row_is_header))
        print('Report Style: {}'.format('Vertical' if self.cxt.reports_in_vertical_style else 'Two facing (Horizontal)'))
        print('Show Count?: {}'.format(self.cxt.shows_count))
        print('Show Difference Only?: {}'.format(self.cxt.shows_difference_only))
        print('Show All?: {}'.format(self.cxt.shows_all_lines))
        print('Show Context?: {}'.format(self.cxt.shows_context_from_arguments))
        print('CSV Sniffing Size: {}'.format(self.cxt.sniffing_size))
        print('--- csv analysis conditions ---')
        print('Forces Individual Specified Conditions?: {}'.format(self.cxt.forces_individual_specs))
        print('column_separator_for_lhs: {}'.format(self.cxt.display_string_for_column_separator(self.cxt.column_separator_for_lhs)))   # DONE: ????????????????????????
        print('column_separator_for_rhs: {}'.format(self.cxt.display_string_for_column_separator(self.cxt.column_separator_for_rhs)))   # DONE: ????????????????????????
        print('line_separator_for_lhs: {}'.format(self.cxt.line_separator_for_lhs.encode('hex')))
        print('line_separator_for_rhs: {}'.format(self.cxt.line_separator_for_rhs.encode('hex')))
        print('quote_char_for_lhs: {}'.format(self.cxt.quote_char_for_lhs))
        print('quote_char_for_rhs: {}'.format(self.cxt.quote_char_for_rhs))
        print('skips_space_after_column_separator_for_lhs: {}'.format(self.cxt.skips_space_after_column_separator_for_lhs))
        print('skips_space_after_column_separator_for_rhs: {}'.format(self.cxt.skips_space_after_column_separator_for_rhs))


class DetailReporter:

    __metaclass__ = abc.ABCMeta

    def __init__(self, context):
        self.cxt = context


    def report_detail_heading(self):

        if not self.cxt.shows_details:
            return

        self._report_content_heading()
        self._report_file_name()

    @spacing_before(1)
    def _report_content_heading(self):

        if self.cxt.shows_difference_only:
            print('* Differences')
        elif self.cxt.shows_all_lines:
            print('* All')
        else:
            pass

    @abc.abstractmethod
    def _report_file_name(self):
        raise NotImplementedError()


    @abc.abstractmethod
    def report_case_of_existed_only_on_lhs(self, lhs_fact):
        raise NotImplementedError()

    @abc.abstractmethod
    def report_case_of_existed_on_both_sides(self, lhs_fact, rhs_fact, value_difference_result):
        raise NotImplementedError()

    @abc.abstractmethod
    def report_case_of_existed_only_on_rhs(self, rhs_fact):
        raise NotImplementedError()


    class Factory:

        def __init__(self):
            pass

        @staticmethod
        def reporter_for(context, scan_result):

            if context.reports_in_vertical_style:
                return VerticalReporter(context, scan_result)
            else:
                return HorizontalReporter(context, scan_result)


class HorizontalReporter(DetailReporter):

    class Template:

        DIFFERENT_COLUMN_GUIDE = 'Column indices with difference'
        PREFIX_of_DIFF_COLUMNS = '  @ '

        def __init__(self, lhs_max_row_number_length, lhs_max_row_length, rhs_max_row_number_length, rhs_max_row_length):

            self.lhs_max_row_number_length = lhs_max_row_number_length
            self.lhs_filler_length = 1
            self.lhs_max_row_length = lhs_max_row_length
            self.diff_mark_filler_length_in_front = 2
            self.diff_mark_length = 1
            self.diff_mark_filler_length_in_rear = 2
            self.rhs_max_row_number_length = rhs_max_row_number_length
            self.rhs_filler_length = 1
            self.rhs_max_row_length = rhs_max_row_length
            self.prefix_length_for_diff_columns_displays = len(self.PREFIX_of_DIFF_COLUMNS)

            self.lhs_length = self.lhs_max_row_number_length + self.lhs_filler_length + self.lhs_max_row_length
            self.diff_mark_length = self.diff_mark_filler_length_in_front + self.diff_mark_length + self.diff_mark_filler_length_in_rear
            self.rhs_length = self.rhs_max_row_number_length + self.rhs_filler_length + self.rhs_max_row_length


        # --- heading-related description ---

        def division_string(self):
            return '-' * (self.lhs_length + self.diff_mark_length + self.rhs_length + self.prefix_length_for_diff_columns_displays + len(self.DIFFERENT_COLUMN_GUIDE))

        def file_name_description(self, lhs_file_name, rhs_file_name):

            lhs_file_name = lhs_file_name.ljust(self.lhs_length)
            diff_mark_spacing = ' ' * self.diff_mark_length
            rhs_file_name = rhs_file_name.ljust(self.rhs_length)
            prefix_length_spacing = ' ' * self.prefix_length_for_diff_columns_displays
            different_column_guide = self.DIFFERENT_COLUMN_GUIDE
            return '%(lhs_file_name)s%(diff_mark_spacing)s%(rhs_file_name)s%(prefix_length_spacing)s%(different_column_guide)s' % locals()


        # --- left-hand side related description ---

        def lhs_only_description(self, lhs_fact):

            lhs = self._lhs_description(lhs_fact)
            diff_mark_area = (' ' * self.diff_mark_filler_length_in_front) + Mark.LHS_ONLY + (' ' * self.diff_mark_filler_length_in_rear)
            return '%(lhs)s%(diff_mark_area)s' % locals()

        def _lhs_description(self, lhs_fact):

            lhs_row_number = str(lhs_fact.lhs_row_number).rjust(self.lhs_max_row_number_length)
            spacing = ' ' * self.lhs_filler_length
            lhs_row = str(lhs_fact.lhs_row).ljust(self.lhs_max_row_length)
            return '%(lhs_row_number)s%(spacing)s%(lhs_row)s' % locals()

        def _lhs_empty_description(self):
            return ' ' * (self.lhs_max_row_number_length + self.lhs_filler_length + self.lhs_max_row_length)


        # --- right-hand side related description ---

        def rhs_only_description(self, rhs_fact):

            empty_lhs = self._lhs_empty_description()
            diff_mark_area = (' ' * self.diff_mark_filler_length_in_front) + Mark.RHS_ONLY + (' ' * self.diff_mark_filler_length_in_rear)
            rhs = self._rhs_description(rhs_fact)
            return '%(empty_lhs)s%(diff_mark_area)s%(rhs)s' % locals()

        def _rhs_description(self, rhs_fact):

            rhs_row_number = str(rhs_fact.rhs_row_number).rjust(self.rhs_max_row_number_length)
            spacing = ' ' * self.rhs_filler_length
            rhs_row = str(rhs_fact.rhs_row).ljust(self.rhs_max_row_length)
            return '%(rhs_row_number)s%(spacing)s%(rhs_row)s' % locals()


        # --- both sides related description ---

        def both_description(self, lhs_fact, rhs_fact, value_difference_result):

            lhs = self._lhs_description(lhs_fact)
            diff_mark = Mark.HAS_DIFF if value_difference_result.has_difference else Mark.NON_DIFF
            diff_mark_area = (' ' * self.diff_mark_filler_length_in_front) + diff_mark + (' ' * self.diff_mark_filler_length_in_rear)
            rhs = self._rhs_description(rhs_fact)
            prefix_of_diff_columns = self.PREFIX_of_DIFF_COLUMNS if value_difference_result.has_difference else ''
            different_columns = str(value_difference_result.different_column_indices) if value_difference_result.has_difference else ''
            return '%(lhs)s%(diff_mark_area)s%(rhs)s%(prefix_of_diff_columns)s%(different_columns)s' % locals()


    def __init__(self, context, scan_result):

        super(HorizontalReporter, self).__init__(context)
        self.cxt = context

        if context.needs_size_info_for_padding:
            size_info = scan_result.size_info_for_padding
            self.template = HorizontalReporter.Template(len(str(size_info.lhs_max_row_number)),
                                                        size_info.lhs_max_row_length,
                                                        len(str(size_info.rhs_max_row_number)),
                                                        size_info.rhs_max_row_length)
        else:
            self.template = None


    # --- report heading related ---

    def _report_file_name(self):

        print(self.template.division_string())
        print(self.template.file_name_description(os.path.basename(self.cxt.lhs_file_name), os.path.basename(self.cxt.rhs_file_name)))
        print(self.template.division_string())


    # --- report each cases ---

    def report_case_of_existed_only_on_lhs(self, lhs_fact):

        if self.cxt.shows_details:
            print(self.template.lhs_only_description(lhs_fact))

    def report_case_of_existed_on_both_sides(self, lhs_fact, rhs_fact, value_difference_result):

        if (self.cxt.shows_difference_only and value_difference_result.has_difference) or self.cxt.shows_all_lines:
            print(self.template.both_description(lhs_fact, rhs_fact, value_difference_result))

    def report_case_of_existed_only_on_rhs(self, rhs_fact):

        if self.cxt.shows_details:
            print(self.template.rhs_only_description(rhs_fact))


class VerticalReporter(DetailReporter):

    class Template:

        LHS_MARK = 'L'
        RHS_MARK = 'R'
        PREFIX_of_DIFF_COLUMNS = '@'

        def __init__(self):
            pass


        # --- heading-related description ---

        @classmethod
        def division_string(cls):
            return '-' * 80

        @classmethod
        def file_name_description(cls, mark, file_name):
            return mark + ' ' + file_name


        # --- left-hand side related description ---

        @classmethod
        def lhs_only_description(cls, lhs_fact):
            return Mark.LHS_ONLY + ' ' + cls.LHS_MARK + ' ' + str(lhs_fact.lhs_row_number) + ' ' + str(lhs_fact.lhs_row)


        # --- right-hand side related description ---

        @classmethod
        def rhs_only_description(cls, rhs_fact):
            return Mark.RHS_ONLY + ' ' + cls.RHS_MARK + ' ' + str(rhs_fact.rhs_row_number) + ' ' + str(rhs_fact.rhs_row)


        # --- both sides related description ---

        @classmethod
        def both_description_heading(cls, value_difference_result):

            if value_difference_result.has_difference:
                return Mark.HAS_DIFF + ' ' + cls.PREFIX_of_DIFF_COLUMNS + ' ' + str(value_difference_result.different_column_indices)
            else:
                return Mark.NON_DIFF_EXPRESSLY

        @classmethod
        def both_description_lhs(cls, lhs_fact, row_number_length):
            return '  ' + cls.LHS_MARK + ' ' + str(lhs_fact.lhs_row_number).rjust(row_number_length) + ' ' + str(lhs_fact.lhs_row)

        @classmethod
        def both_description_rhs(cls, rhs_fact, row_number_length):
            return '  ' + cls.RHS_MARK + ' ' + str(rhs_fact.rhs_row_number).rjust(row_number_length) + ' ' + str(rhs_fact.rhs_row)



    def __init__(self, context, _):

        super(VerticalReporter, self).__init__(context)
        self.cxt = context
        self.template = VerticalReporter.Template()


    # --- report heading related ---

    def _report_file_name(self):

        print(self.template.division_string())
        print(self.template.file_name_description(self.template.LHS_MARK, os.path.basename(self.cxt.lhs_file_name)))
        print(self.template.file_name_description(self.template.RHS_MARK, os.path.basename(self.cxt.rhs_file_name)))
        print(self.template.division_string())


    # --- report each cases ---

    def report_case_of_existed_only_on_lhs(self, lhs_fact):

        if self.cxt.shows_details:
            print(self.template.lhs_only_description(lhs_fact))

    def report_case_of_existed_on_both_sides(self, lhs_fact, rhs_fact, value_difference_result):

        if (self.cxt.shows_difference_only and value_difference_result.has_difference) or self.cxt.shows_all_lines:

            row_number_length = max(len(str(lhs_fact.lhs_row_number)), len(str(rhs_fact.rhs_row_number)))

            print(self.template.both_description_heading(value_difference_result))
            print(self.template.both_description_lhs(lhs_fact, row_number_length))
            print(self.template.both_description_rhs(rhs_fact, row_number_length))

    def report_case_of_existed_only_on_rhs(self, rhs_fact):

        if self.cxt.shows_details:
            print(self.template.rhs_only_description(rhs_fact))


class CountReporter:

    class Counter:

        def __init__(self):

            self.number_of_same_lines = 0
            self.number_of_lhs_only = 0
            self.number_of_rhs_only = 0
            self.number_of_differences = 0

            self.row_numbers_for_lhs_only = []
            self.row_numbers_for_rhs_only = []
            self.row_numbers_for_differences = {}

            self._max_digit = None

        def _increment_same_lines(self):
            self.number_of_same_lines += 1

        def _increment_lhs_only(self):
            self.number_of_lhs_only += 1

        def _increment_rhs_only(self):
            self.number_of_rhs_only += 1

        def _increment_differences(self):
            self.number_of_differences += 1

        def _add_row_number_for_lhs_only(self, row_number):
            self.row_numbers_for_lhs_only.append(row_number)

        def _add_row_number_for_rhs_only(self, row_number):
            self.row_numbers_for_rhs_only.append(row_number)

        def _add_row_number_for_differences(self, lhs_row_number, rhs_row_number):
            self.row_numbers_for_differences[lhs_row_number] = rhs_row_number


        def count_for_case_of_existed_only_on_lhs(self, row_number):
            self._increment_lhs_only()
            self._add_row_number_for_lhs_only(row_number)

        def count_for_case_of_existed_on_both_sides(self, lhs_fact, rhs_fact, value_difference_result):

            if value_difference_result.has_difference:
                self._increment_differences()
                self._add_row_number_for_differences(lhs_fact.lhs_row_number, rhs_fact.rhs_row_number)
            else:
                self._increment_same_lines()

        def count_for_case_of_existed_only_on_rhs(self, row_number):
            self._increment_rhs_only()
            self._add_row_number_for_rhs_only(row_number)

        @property
        def sorted_row_numbers_for_differences(self):
            return sorted(self.row_numbers_for_differences.items(), key=lambda x: x[0])


        @property
        def max_digit(self):

            if self._max_digit is not None:
                return self._max_digit

            self._max_digit = max(
                len(str(self.number_of_same_lines)),
                len(str(self.number_of_lhs_only)),
                len(str(self.number_of_rhs_only)),
                len(str(self.number_of_differences)),
            )
            return self._max_digit


    def __init__(self, shows_count):
        self.shows_count = shows_count
        self.counter = self.Counter()


    def _func_of_right_justified_number(self):
        return lambda number: str(number).rjust(self.counter.max_digit)

    @spacing_before(1)
    def report_count(self):

        if not self.shows_count:
            return

        print('* Count & Row number')

        rjust = self._func_of_right_justified_number()
        print('same lines           : {}'.format(rjust(self.counter.number_of_same_lines)))
        print('left side only    ({}): {} :-- Row Numbers      -->: {}'.format(Mark.LHS_ONLY, rjust(self.counter.number_of_lhs_only), self.counter.row_numbers_for_lhs_only))
        print('right side only   ({}): {} :-- Row Numbers      -->: {}'.format(Mark.RHS_ONLY, rjust(self.counter.number_of_rhs_only), self.counter.row_numbers_for_rhs_only))
        print('with differences  ({}): {} :-- Row Number Pairs -->: {}'.format(Mark.HAS_DIFF, rjust(self.counter.number_of_differences), self.counter.sorted_row_numbers_for_differences))


# ----------------------------------------------------------------------------------------------------------------------
#  CSV Reading
# ----------------------------------------------------------------------------------------------------------------------

class FileArrangement(type):

    LHS = '_for_lhs'
    RHS = '_for_rhs'


class CsvDialectFixer:

    def __init__(self):
        pass

    @classmethod
    def fixed_dialect(cls, context, csv_file, file_arrangement):

        if context.forces_individual_specs:
            return cls._dialect_from_context(context, file_arrangement)
        else:
            return cls._try_sniffing(context, csv_file, file_arrangement)


    @classmethod
    def _dialect_from_context(cls, context, file_arrangement):

        dialect = csv.excel()
        dialect.delimiter = getattr(context, "column_separator" + file_arrangement)
        dialect.lineterminator = getattr(context, "line_separator" + file_arrangement)
        dialect.quotechar = getattr(context, "quote_char" + file_arrangement)
        dialect.skipinitialspace = getattr(context, "skips_space_after_column_separator" + file_arrangement)

        return dialect, context

    @classmethod
    def _try_sniffing(cls, context, csv_file, file_arrangement):

        try:
            return cls._sniff(context, csv_file, file_arrangement)

        except csv.Error as e:

            logger.warning('Sniffing failed. Generated a dialect from context instead. [type={}, args={}, message={}]'.format(type(e), str(e.args), e.message))
            return cls._dialect_from_context(context, file_arrangement)

        finally:
            csv_file.seek(0)

    @classmethod
    def _sniff(cls, context, csv_file, file_arrangement):

        sample = csv_file.read(context.sniffing_size)
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample)
        has_header = sniffer.has_header(sample)

        adjusted_context = cls._adjust_context_with(dialect, has_header, context, file_arrangement)

        return dialect, adjusted_context

    @classmethod
    def _adjust_context_with(cls, dialect, has_header, context, file_arrangement):

        setattr(context, "column_separator" + file_arrangement, dialect.delimiter)
        setattr(context, "line_separator" + file_arrangement, dialect.lineterminator)
        setattr(context, "quote_char" + file_arrangement, dialect.quotechar)
        setattr(context, "skips_space_after_column_separator" + file_arrangement, dialect.skipinitialspace)
        context.first_row_is_header = has_header if context.header is None else (True if context.header == 'y' else False)

        return context


def debug_log_dialect(dialect, context, message):

    logger.debug('---{}---'.format(message))
    logger.debug('sniffing dialect={}'.format(dialect))
    logger.debug('sniffing dialect csv.excel={}'.format(isinstance(dialect, csv.excel)))
    logger.debug('sniffing dialect csv.excel_tab={}'.format(isinstance(dialect, csv.excel_tab)))
    logger.debug('sniffing dialect.delimiter={}'.format(dialect.delimiter.encode('hex')))
    logger.debug('sniffing dialect.doublequote={}'.format(dialect.doublequote))
    logger.debug('sniffing dialect.escapechar={}'.format(dialect.escapechar))
    logger.debug('sniffing dialect.lineterminator={}'.format(dialect.lineterminator.encode('hex')))
    logger.debug('sniffing dialect.quotechar={}'.format(dialect.quotechar))
    logger.debug('sniffing dialect.quoting={}'.format(dialect.quoting))
    logger.debug('sniffing dialect.skipinitialspace={}'.format(dialect.skipinitialspace))


class LhsFact:

    def __init__(self, lhs_row_number, lhs_row, lhs_key):

        logger.debug('LhsFact ?????? lhs_row_number={}, lhs_row={}, lhs_key={}'.format(lhs_row_number, lhs_row, lhs_key))

        self.lhs_row_number = lhs_row_number
        self.lhs_row = lhs_row
        self.lhs_key = lhs_key


class RhsFact:

    def __init__(self, rhs_row_number, rhs_row, rhs_key):

        logger.debug('RhsFact ?????? rhs_row_number={}, rhs_row={}, rhs_key={}'.format(rhs_row_number, rhs_row, rhs_key))

        self.rhs_row_number = rhs_row_number
        self.rhs_row = rhs_row
        self.rhs_key = rhs_key


class CsvReader:

    class State:

        def __init__(self, csv_file, dialect, file_name, first_row_is_header):

            self._csv_file = csv_file
            self._dialect = dialect
            self._file_name = file_name
            self._first_row_is_header = first_row_is_header

            self._csv_reader = csv.reader(csv_file, dialect)
            self._row_number = 0
            self._previous_key = ""

        def reset(self):

            self._csv_file.seek(0)
            self._csv_reader = csv.reader(self._csv_file, self._dialect)
            self._row_number = 0
            self._previous_key = ""

        def increment_row_number(self):

            if self._previous_key == MatchingKeyCodec.END_of_KEY:
                return

            self._row_number += 1

        def key_changed(self, new_key):

            if self._is_header():
                return

            self._previous_key = new_key

        def _is_header(self):
            return self.row_number == 0 and self._first_row_is_header

        @property
        def csv_reader(self):
            return self._csv_reader

        @property
        def file_name(self):
            return self._file_name

        @property
        def row_number(self):
            return self._row_number

        @property
        def previous_key(self):
            return self._previous_key


    def __init__(self, lhs_csv, rhs_csv, lhs_dialect, rhs_dialect, context):

        debug_log_dialect(lhs_dialect, context, '???CSV')
        debug_log_dialect(rhs_dialect, context, '???CSV')

        self.lhs_csv_state = CsvReader.State(lhs_csv, lhs_dialect, context.lhs_file_name, context.first_row_is_header)
        self.rhs_csv_state = CsvReader.State(rhs_csv, rhs_dialect, context.rhs_file_name, context.first_row_is_header)
        self.cxt = context

        self.skip_header()

    def skip_header(self):

        if self.cxt.first_row_is_header:
            _ = self.read_lhs()
            _ = self.read_rhs()

    def reset(self):

        self.lhs_csv_state.reset()
        self.rhs_csv_state.reset()
        self.skip_header()

    def read_lhs(self):

        lhs_row, lhs_key = self._read_csv(self.lhs_csv_state)
        self.lhs_csv_state.increment_row_number()
        return LhsFact(self.lhs_csv_state.row_number, lhs_row, lhs_key)

    def read_rhs(self):

        rhs_row, rhs_key = self._read_csv(self.rhs_csv_state)
        self.rhs_csv_state.increment_row_number()
        return RhsFact(self.rhs_csv_state.row_number, rhs_row, rhs_key)

    def _read_csv(self, csv_state):

        try:
            row = next(csv_state.csv_reader)
        except StopIteration:
            csv_state.key_changed(MatchingKeyCodec.END_of_KEY)
            return [], MatchingKeyCodec.END_of_KEY

        new_key = self.cxt.matching_key_codec.managed_key_for(row)
        self._detect_key_violation(new_key, csv_state)

        csv_state.key_changed(new_key)

        return row, new_key

    def _detect_key_violation(self, new_key, csv_state):

        if csv_state.previous_key == '':
            return

        if new_key < csv_state.previous_key:
            logger.error('matching keys in {} are not sorted.'
                         ' [current_key={}, previous_key={}, matching-key-indices={}]  If the key is a number without zero padding, specify the max size of the key after colon like -k0:8.'.format(
                         csv_state.file_name, MatchingKeyCodec.decode_key(new_key), MatchingKeyCodec.decode_key(csv_state.previous_key), self.cxt.matching_key_codec.matching_key_info_list))
            exit(1)

        if self.cxt.key_should_be_unique and new_key == csv_state.previous_key:
            logger.error('matching keys in {} are not unique.'
                         ' [current_key={}, previous_key={}, matching-key-indices={}]'.format(
                         csv_state.file_name, MatchingKeyCodec.decode_key(new_key), MatchingKeyCodec.decode_key(csv_state.previous_key), self.cxt.matching_key_codec.matching_key_info_list))
            exit(1)


if __name__ == '__main__':

    main()


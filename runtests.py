#!/usr/bin/env python3
import os
import sys
import difflib
from io import StringIO
from traceback import print_exc
from itertools import chain

from subprocess import STDOUT
from subprocess import check_output
from subprocess import CalledProcessError

from pythonium.main import main
from pythonium.veloce.veloce import Veloce
from pythonium.compliant.compliant import Compliant
from pythonium.utils import pythonium_generate_js


ROOT = os.path.abspath(os.path.dirname(__file__))
TESTS_ROOT = os.path.join(ROOT, 'tests')
COMPLIANT_TESTS_ROOT = os.path.join(TESTS_ROOT, 'compliant')
PYTHON_TESTS_ROOT = os.path.join(TESTS_ROOT, 'python')

# generate pythonium compliant library
stdout = sys.stdout
sys.stdout = StringIO()
main(['--generate'])
COMPLIANTJS = sys.stdout.getvalue()
sys.stdout = stdout


# init counts
ok_ctr = test_ctr = 0


def compare_output(expected, result):
    if isinstance(expected, bytes):
        expected = expected.decode(errors='replace')
    if isinstance(result, bytes):
        result = result.decode(errors='replace')
    expected = expected.strip().splitlines()
    result = result.strip().splitlines()
    diffs = difflib.unified_diff(expected, result, n=1, lineterm='',
                                 fromfile='expected', tofile='result')
    return list(diffs)


def run(test, filepath, mode):
    global ok_ctr, test_ctr
    print('> Running {} in {} mode.'.format(test, mode))
    test_ctr += 1
    ext = 'exec-{}.js'.format(mode)
    exec_script = os.path.join(TMPDIR, test + ext)
    with open(exec_script, 'w') as f:
        if mode =='veloce':
            translator=Veloce
        else:
            f.write(COMPLIANTJS)
            translator=Compliant
        try:
            pythonium_generate_js(filepath, translator, output=f)
        except Exception as exc:
            print_exc()
            print('< Translation failed with the above exception.')
            return

    try:
        result = check_output(['node', '--harmony', exec_script], stderr=STDOUT)
    except CalledProcessError as err:
        print(err.output.decode(errors='replace'))
        print('< ERROR :(')
        return

    expected_file = os.path.join(os.path.dirname(filepath), test+'.expected')
    if os.path.exists(expected_file):
        with open(expected_file, 'br') as f:
            expected = f.read()
    else:
        try:
            expected = check_output(['python3', filepath], stderr=STDOUT)
        except CalledProcessError as err:
            print(err.output.decode(errors='replace'))
            print('< PYTHON ERROR :(')
            return

    diffs = compare_output(expected, result)
    if diffs:
        for line in diffs:
            print(line)
        print('< FAILED :(')
    else:
        ok_ctr += 1
        print('< PASS :)')


def run_python(test, filepath):
    global ok_ctr, test_ctr
    test_ctr +=1
    print('> Running python test {}.'.format(test))
    try:
        expected = check_output(['python3', filepath], stderr=STDOUT)
    except CalledProcessError as err:
        print(err.output.decode(errors='replace'))
        print('< PYTHON ERROR :(')
        return
    else:
        print('> PASS :)')
        ok_ctr += 1

if __name__ == '__main__':

    TMPDIR = os.path.join(TESTS_ROOT, 'tmp')
    try:
        os.mkdir(TMPDIR)
    except OSError:
        pass

    # solo mode
    if len(sys.argv) > 1:
        for path in sys.argv[1:]:
            if 'python' in path:
                run_python(path, path)
            else:
                if 'compliant' in path:
                    modes = ('compliant',)
                else:
                    modes = ('veloce', 'compliant')
                name = os.path.basename(path)
                for mode in modes:
                    run(name, path, mode)
    else:
        for mode in ('veloce', 'compliant'):
            print('* Running tests for {} mode'.format(mode))
            for test in os.listdir(TESTS_ROOT):
                if test.endswith('.py'):
                    filepath = os.path.join(TESTS_ROOT, test)
                    run(test, filepath, mode)
        for test in os.listdir(COMPLIANT_TESTS_ROOT):
            if test.endswith('.py'):
                filepath = os.path.join(COMPLIANT_TESTS_ROOT, test)
                run(test, filepath, mode)
        print('* Running python tests')
        for test in os.listdir(PYTHON_TESTS_ROOT):
            if test.endswith('.py'):
                run_python(test, os.path.join(PYTHON_TESTS_ROOT, test))
    print("= Passed {}/{} tests".format(ok_ctr, test_ctr))
    if (ok_ctr - test_ctr) != 0:
        sys.exit(1)

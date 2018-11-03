import subprocess
import os
import sys

class SatSolver(object):
    """ A helper class that manages SAT solver invocation. """

    def __init__(self, solverPath = None):
        """ Creates a new SAT solver.

            Use *solverPath* to specify an optional location where to look
            for SAT solver binary (it will be looked for in a set of default
            locations).
        """

        self.paths = []
        if solverPath:
            self.paths.append(solverPath)

        if sys.platform.startswith('linux'):
            self.paths += [
                    'minisat', 'MiniSat_v1.14_linux',
                    './minisat', './MiniSat_v1.14_linux',
                    '../tools/lin/minisat'
                ]
        elif sys.platform.startswith('win'):
            self.paths += [
                    'minisat.exe', 'MiniSat_v1.14.exe',
                    '../minisat/minisat.exe',
                ]
        else:
            pass # empty solver paths will fall back to try 'minisat'

        # default fall for all
        self.paths.append('minisat')

    def getSolverPath(self):
        # return './minisat/minisat.exe'
        """ Returns the path to solver binary. """
        for fn in self.paths:
            try:
                subprocess.check_output([fn, '--help'], stderr = subprocess.STDOUT)
                sys.stderr.write('using sat solver:  "%s"\n' % fn)
                return fn
            except OSError:
                pass
        raise IOError('Solver executable not found!')

    def solve(self, theory_file, output_file):
        """ Use SAT solver to solve a theory, which is either the name
            of a file (in DIMACS format) or an instance of DimacsWriter.

            Writes the SAT solvers output to a file named *output*.

            Returns a tuple (sat, solution), where sat is True or False
            and solution is a list of positive or negative integers
            (an empty list if sat is False).
        """
        # if isinstance(theory, DimacsWriter):
        #     if not theory.closed():
        #         theory.close()
        #     theory = theory.filename()

        try:
            self.output = subprocess.check_output(
                    [self.getSolverPath(), theory_file, output_file],
                    stderr = subprocess.STDOUT,

                    )
            print(self.output)
        except subprocess.CalledProcessError:
            # minisat has weird return codes
            # print('error: minisat has weird return codes')
            pass

        with open(output_file) as f:
            sat = f.readline()
            if sat.strip() == 'SAT':
                sol = f.readline()
                return (
                        True,
                        [int(x) for x in sol.split()][:-1]
                )
            else:
                return (False, [])


# vim: set sw=4 ts=4 sts=4 et :
